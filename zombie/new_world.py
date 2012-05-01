"""Don't you dare close your eyes."""

import functools
import json
import logging
import time
import uuid

import eventlet
from eventlet import queue
import zmq

from zombie import shared


SLEEP_TIME = 0.0001


class ServeContext(dict):
  # ident
  # sock
  def __init__(self, stream, ident, data):
    super(ServeContext, self).__init__(**json.loads(data))
    self['ident'] = ident
    self['stream'] = stream

  def reply(self, msg, done=True):
    envelope = {'msg_id': self['msg_id'],
                'cmd': 'reply',
                'data': msg}
    msg_data = json.dumps(envelope)
    self['stream'].sock.send_multipart([self['ident'], msg_data])
    if done:
      self.end_reply()

  def end_reply(self):
    msg = {'msg_id': self['msg_id'],
           'cmd': 'end_reply'}
    msg_data = json.dumps(msg)
    self['stream'].sock.send_multipart([self['ident'], msg_data])

  def send(self, msg, *args):
    self['stream'].sock.send_multipart([msg % args])


class ConnectContext(dict):
  # ident
  # sock
  def __init__(self, stream, data):
    super(ConnectContext, self).__init__(**json.loads(data))
    self['stream'] = stream

  def reply(self, msg, done=True):
    envelope = {'msg_id': self['msg_id'],
                'cmd': 'reply',
                'data': msg}
    msg_data = json.dumps(envelope)
    self['stream'].sock.send_multipart([msg_data])
    if done:
      self.end_reply()

  def end_reply(self):
    msg = {'msg_id': self['msg_id'],
           'cmd': 'end_reply'}
    msg_data = json.dumps(msg)
    self['stream'].sock.send_multipart([msg_data])

  def send_cmd(self, cmd, data=None):
    msg = {'msg_id': uuid.uuid4().hex,
           'cmd': cmd,
           'args': data or {},
           }
    msg_data = json.dumps(msg)

    q = self['stream'].register_channel(msg['msg_id'])

    self['stream'].sock.send_multipart([msg_data])
    try:
      while True:
        eventlet.sleep(SLEEP_TIME)
        if not q.empty():
          rv = q.get(timeout=5)
          if rv == StopIteration:
            break
          yield rv
    except queue.Empty:
      pass

    self['stream'].deregister_channel(msg['msg_id'])

  def send(self, msg, *args):
    self['stream'].sock.send_multipart([msg % args])


class Stream(object):
  def __init__(self, handler):
    self.handler = handler
    self._reply_waiters = {}

  def serve(self, address):
    """Listen on an XREP socket."""
    self.sock = shared.zctx.socket(zmq.XREP)
    self.sock.bind(address)
    while not self.sock.closed:
      eventlet.sleep(SLEEP_TIME)
      try:
        parts = self.sock.recv_multipart(flags=zmq.NOBLOCK)
        ident = parts.pop(0)
        msg = ServeContext(stream=self, ident=ident, data=parts[0])

        # special case replies
        if msg['cmd'] == 'reply':
          shared.pool.spawn(self.handle_reply, msg)
        elif msg['cmd'] == 'end_reply':
          shared.pool.spawn(self.handle_end_reply, msg)
        else:
          shared.pool.spawn(self.handle_cmd, msg)

      except zmq.ZMQError as e:
        if e.errno == zmq.EAGAIN:
          pass

  def connect(self, address, callback):
    """Connect with an XREQ socket."""
    self.sock = shared.zctx.socket(zmq.XREQ)
    self.sock.connect(address)

    shared.pool.spawn(callback, ConnectContext(stream=self, data='{}'))
    while not self.sock.closed:
      eventlet.sleep(SLEEP_TIME)
      try:
        parts = self.sock.recv_multipart(flags=zmq.NOBLOCK)
        msg = ConnectContext(stream=self, data=parts[0])

        # special case replies
        if msg['cmd'] == 'reply':
          shared.pool.spawn(self.handle_reply, msg)
        elif msg['cmd'] == 'end_reply':
          shared.pool.spawn(self.handle_end_reply, msg)
        else:
          shared.pool.spawn(self.handle_cmd, msg)

      except zmq.ZMQError as e:
        if e.errno == zmq.EAGAIN:
          pass

  def close(self):
    self.sock.close()

  def register_channel(self, msg_id):
    q = queue.LightQueue()
    self._reply_waiters[msg_id] = q
    return q

  def deregister_channel(self, msg_id):
    del self._reply_waiters[msg_id]

  def get_channel(self, msg_id):
    return self._reply_waiters[msg_id]

  def handle_reply(self, msg):
    """Put responses to a message on our queue."""
    if msg['msg_id'] not in self._reply_waiters:
      raise Exception('no such reply waiter: %s' % msg['msg_id'])
    reply_waiter = self._reply_waiters[msg['msg_id']]
    reply_waiter.put(msg)

  def handle_end_reply(self, msg):
    """End responses to a message on our queue."""
    if msg['msg_id'] not in self._reply_waiters:
      raise Exception('no such reply waiter: %s' % msg['msg_id'])
    reply_waiter = self._reply_waiters[msg['msg_id']]
    reply_waiter.put(StopIteration)

  def handle_cmd(self, msg):
    """Attempt to call a method on the handler."""
    f = getattr(self.handler, 'cmd_%s' % msg['cmd'])
    f(msg, **dict((str(k), v) for k, v in msg['args'].iteritems()))


class Keystore(object):
  def __init__(self, keys):
    self.keys = {}

  def fetch(self, signature):
    signer = Signature.Load(signature).signer
    if signer in self.keys:
      return self.keys[signer]
    raise Exception('key not found')


class Signature(object):
  def __init__(self, signer, ciphertext):
    self.signer = signer
    self.ciphertext = ciphertext

  @classmethod
  def Load(cls, signature):
    data = json.loads(signature)
    return cls(signer=data['signer'], ciphertext=data['ciphertext'])


class World(object):
  """Handle the tasks a world must handle. So heavy is this burden.

  A world is in charge of a few things:
    - Providing addresses for locations (lookup_location)
    - Providing a default location for new users (default_location)

  """

  def __init__(self, location_db):
    self.location_db = location_db

  def cmd_lookup_location(self, context, location_id):
    return context.reply({location_id: self.location_db.get(location_id)})

  def cmd_default_location(self, context):
    return self.cmd_lookup_location(context, 'default')


class Location(object):
  """Handle the tasks a location must handle. That which never ends.

  A location is in charge of a few things:
    - Broadcasting events to everybody in the location
    - Checking whether a user is allowed to enter (enter)
    - Allowing a user to leave (leave)
    - Providing information about itself (look)

  """

  def __init__(self, data):
    self.data = data
    self.keys = Keystore()

  def sign(self, data):
    return (data, 'i_am_a_signature')

  def verify(self, data, signature):
    """Verify the signature on given data.

    This will result in an attempt to look up the public key of the signer,
    possibly requiring a network call to get the key if it is not already
    cached.
    """
    public_key = self.keys.fetch(signature)
    public_key.verify(data, signature)
    return True

  def cmd_enter(self, context, valid_entry):
    """Decide whether to allow a user to enter. Announce if success.

    In the basic case a user needs to present some sort of validation token,
    usually from an adjoining location, that proves this user left that
    location towards this one. Something like::

      signed(old_location, ('leave', old_location, new_location))

    In plausibly more advanced cases (e.g. teleportation), a teleportation
    credential may be added::

      signed(old_location, ('teleport', old_location, new_location))

    The new location should probably additionally verify this entry token
    with the world to prevent a user from being in multiple spots.
    """
    pass

  def cmd_leave(self, context, new_location):
    """Decide whether to allow a user to leave. Announce if success.

    This is pretty much always successful but possibly some puzzles will want
    to make this more difficult.

    Should provide a valid entry token for the new location.

    In the basic case only allow leaving to adjacent locations.
    """
    context.reply((self.data.get('id'), new_location))

  def cmd_look(self, context):
    return context.reply(self.data)
