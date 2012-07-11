"""Don't you dare close your eyes."""

import functools
import json
import logging
import time
import uuid

import eventlet
from eventlet import event
from eventlet import queue
from eventlet import timeout
import zmq

from zombie import shared
from zombie import model


SLEEP_TIME = 0.1

class RemoteError(Exception):
  pass


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

  def reply_exc(self, exc, done=True):
    envelope = {'msg_id': self['msg_id'],
                'cmd': 'reply',
                'exc': str(exc),
                'data': {}}
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
    logging.debug('SSEND> %s', [msg % args])
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
    """Send command to the remote server and feed replies back to the caller.

    This produces a generator to allow for multiple responses to a single
    call. If an exception is returned it will be raised.
    """
    msg = {'msg_id': uuid.uuid4().hex,
           'cmd': cmd,
           'args': data or {},
           }
    msg_data = json.dumps(msg)

    q = self['stream'].register_channel(msg['msg_id'])

    self['stream'].sock.send_multipart([msg_data])
    with timeout.Timeout(3):
      try:
        while True:
          eventlet.sleep(SLEEP_TIME)
          if not q.empty():
            rv = q.get(timeout=5)
            if rv == StopIteration:
              break
            if 'exc' in rv:
              raise RemoteError(rv['exc'])
            yield rv['data']
      except queue.Empty:
        pass

    self['stream'].deregister_channel(msg['msg_id'])

  def send(self, msg, *args):
    logging.debug('CSEND> %s', [msg % args])
    self['stream'].sock.send_multipart([msg % args])


class Stream(object):
  """Handles data coming in to a server or from a server.

  The basic operations as a server:
    - Listen on a given port
    - On new messages
      - Create a ServeContext (used by the handler to direct any replies)
      - Decide what to do with the message based on the command.
        - Two special cases of command are 'reply' and 'end_reply' which route
          messages back to the calling function and do what you would expect.


  """

  def __init__(self, handler):
    self.handler = handler
    self._reply_waiters = {}

  def serve(self, address):
    """Listen on an XREP socket."""
    logging.debug('SERVE %s', address)
    self.sock = shared.zctx.socket(zmq.XREP)
    self.sock.bind(address)
    while not self.sock.closed:
      eventlet.sleep(SLEEP_TIME)
      try:
        parts = self.sock.recv_multipart(flags=zmq.NOBLOCK)
        logging.debug('<SRECV %s', parts)
        ident = parts.pop(0)
        ctx = ServeContext(stream=self, ident=ident, data=parts[0])

        # special case replies
        if ctx['cmd'] == 'reply':
          shared.pool.spawn(self.handle_reply, ctx)
        elif ctx['cmd'] == 'end_reply':
          shared.pool.spawn(self.handle_end_reply, ctx)
        else:
          shared.pool.spawn(self.handle_cmd, ctx)

      except zmq.ZMQError as e:
        if e.errno == zmq.EAGAIN:
          pass

  def connect(self, address, callback):
    """Connect with an XREQ socket."""
    logging.debug('CONNECT %s', address)
    self.sock = shared.zctx.socket(zmq.XREQ)
    self.sock.connect(address)

    shared.pool.spawn(callback, ConnectContext(stream=self, data='{}'))
    while not self.sock.closed:
      eventlet.sleep(SLEEP_TIME)
      try:
        parts = self.sock.recv_multipart(flags=zmq.NOBLOCK)
        logging.debug('<CRECV %s', parts)
        ctx = ConnectContext(stream=self, data=parts[0])

        # special case replies
        if ctx['cmd'] == 'reply':
          shared.pool.spawn(self.handle_reply, ctx)
        elif ctx['cmd'] == 'end_reply':
          shared.pool.spawn(self.handle_end_reply, ctx)
        else:
          shared.pool.spawn(self.handle_cmd, ctx)

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

  def handle_reply(self, ctx):
    """Put responses to a message on our queue."""
    if ctx['msg_id'] not in self._reply_waiters:
      raise Exception('no such reply waiter: %s' % ctx['msg_id'])
    reply_waiter = self._reply_waiters[ctx['msg_id']]
    reply_waiter.put(ctx)

  def handle_end_reply(self, ctx):
    """End responses to a message on our queue."""
    if ctx['msg_id'] not in self._reply_waiters:
      raise Exception('no such reply waiter: %s' % ctx['msg_id'])
    reply_waiter = self._reply_waiters[ctx['msg_id']]
    reply_waiter.put(StopIteration)

  def handle_cmd(self, ctx):
    """Attempt to call a method on the handler."""
    try:
      f = getattr(self.handler, 'cmd_%s' % ctx['cmd'])
      f(ctx, **dict((str(k), v) for k, v in ctx['args'].iteritems()))
    except Exception as e:
      logging.exception('EXC in handle_cmd\ncmd_%s(**%s)', ctx['cmd'], ctx['args'])
      ctx.reply_exc(e)


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
    - (x) Providing addresses for locations (lookup_location)
    - (x) Providing a default location for new users (default_location)
    - ( ) Keeping track of the locations of all users (accept_move)
  """

  def __init__(self, location_db, user_db):
    self.location_db = location_db
    self.user_db = user_db

  def cmd_lookup_location(self, ctx, location_id):
    return ctx.reply({location_id: self.location_db.get(location_id)})

  def cmd_default_location(self, ctx):
    return self.cmd_lookup_location(ctx, 'default')

  def cmd_last_location(self, ctx, user_id):
    """Get the last location for the given user and return a join token."""
    last_location_id = self.user_db.last_location(user_id)
    location_ref = self.location_db.get(last_location_id)
    o = {'address': location_ref.address,
         'join_token': {'user_id': user_id,
                        'location_id': last_location_id,
                        'from_id': last_location_id,
                        }
         }
    return ctx.reply(o)


class Kvs(dict):
  deserialize = lambda x: x

  def get(self, key, default=None):
    rv = super(Kvs, self).get(key, default)
    return self.deserialize(rv)



class WorldUserDatabase(Kvs):
  """Interface for accessing user data."""
  deserialize = model.User.from_dict

  def last_location(self, user_id):
    """Return the last location for a given user_id."""
    user_ref = self.get(user_id)
    return user_ref.last_location


class WorldLocationDatabase(Kvs):
  """Interface for accessing location data."""
  deserialize = model.Location.from_dict


class Location(object):
  """Handle the tasks a location must handle. That which never ends.

  A location is in charge of a few things:
    - Broadcasting events to everybody in the location
    - Checking whether a user is allowed to enter (join)
    - Allowing a user to leave (move)
    - Providing information about itself (look)

  """

  def __init__(self, user_db):
    self.user_db = user_db
    #self.keys = Keystore()

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

  def cmd_join(self, ctx, join_token):
    """Handle a user trying to join this location.

    If the join_token looks good, get the world to update the last location
    in the db.
    """
    # TODO(termie): verify join token
    self.world.update_location(join_token)
    ctx.reply({'result': 'ok'})

    # Add the user to our local db
    self.users.add(ctx.username, ctx)

    # Announce the user's entrance, if applicable.
    self.broadcast_joined(ctx.username, join_token['from_id'])

  def cmd_look(self, ctx):
    return ctx.reply(self.data)


class LocationUserDatabase(Kvs):
  pass


class User(object):
  def __init__(self, id):
    self.id = id


class Client(object):
  """Holds on to a user object and uses it to interact with the game.

  This represents the high level interface to interacting with the game
  while the User is what holds on to state.

  """
  def __init__(self, user):
    self.user = user
    self.world = None
    self.location = None

  def _connect_to_world(self, address):
    """Establish a connection to the main world.

    After that you'll most likely reconnect to the User's last location.
    """
    self.world_handler = self
    world_ev = event.Event()
    self.world_stream = Stream(self.world_handler)
    shared.pool.spawn(self.world_stream.connect, address, world_ev.send)
    logging.debug('WAITING')
    world_context = world_ev.wait()
    logging.debug('FINSIHED')
    self.world = WorldClient(self.user, world_context)
    return self.world

  def _connect_to_location(self, address):
    """Establish a connection to a given location.

    After that you'll most likely try to join the location.
    """
    self.location_handler = self
    loc_ev = event.Event()

    self.location_stream = Stream(self.location_handler)
    shared.pool.spawn(self.location_stream.connect, address, loc_ev.send)
    loc_context = loc_ev.wait()
    self.location = LocationClient(self.user, loc_context)
    return self.location

  def _rejoin_game(self, address):
    """Go through all the steps to get back into game.

    - Connect to the world.
    - Request last location.
    - Connect to last location
    - Join last location with reconnect token.
    """
    world = self._connect_to_world(address)
    last_loc = world.last_location()
    logging.debug('LAST LOC %s', last_loc)
    loc_address = last_loc['address']
    join_token = last_loc['join_token']

    location = self._connect_to_location(loc_address)
    location.join(join_token)

  def _move_location(self, new_location):
    """Send the move command to the current location using the new location.

    The location will send back a move token for the new location (after
    getting it signed by the world.)

    After that it will send a disconnect to this client and the client
    will connect to the new location and attempt to join.
    """
    move_rv = self.location.move(new_location)
    address = move_rv['address']
    join_token = move_rv['join_token']
    self.location.disconnect()

    location = self._connect_to_location(address)
    location.join(join_token)


class LocationClient(object):
  """Interface to the various commands we might send to a location."""

  def __init__(self, user, ctx):
    self.ctx = ctx
    self.user = user

  def disconnect(self):
    self.ctx.stream.close()

  def join(self, join_token):
    """Attempt the join the location."""
    rv = self.ctx.send_cmd('join', data={'join_token': join_token})
    success = rv.next()
    return success

  def move(self, new_location_id):
    """Send the move command.

    Returns:
      {'address': <new_location_address>
       'join_token': {'user': <username>,
                      'location_id': <new location_id>,
                      'from_id': <last_location_id>}
        }
    """
    rv = self.ctx.send_cmd('move', data={'new_location': new_location_id})
    move_rv = rv.next()
    return move_rv


class WorldClient(object):
  """Interface to the various commands we might send to a world."""

  def __init__(self, user, ctx):
    self.ctx = ctx
    self.user = user

  def last_location(self):
    """Request the current user's last location."""
    rv = self.ctx.send_cmd('last_location', data={'user_id': self.user.id})
    last_loc = rv.next()
    return last_loc

