import json
import logging
import time
import uuid

import gflags
import zmq
from eventlet import queue
from eventlet import timeout

from zombie import shared


FLAGS = gflags.FLAGS
gflags.DEFINE_float('sleep_time', 0.001,
                    'how long to wait in event loops')



class ServeContext(dict):
  # ident
  # sock
  def __init__(self, stream, ident, data):
    super(ServeContext, self).__init__(**json.loads(data))
    self['ident'] = ident
    self.stream = stream

  def reply(self, msg, done=True):
    try:
      msg = msg.to_dict()
    except AttributeError:
      pass
    envelope = {'msg_id': self['msg_id'],
                'cmd': 'reply',
                'data': msg}
    msg_data = json.dumps(envelope)
    self.stream.sock.send_multipart([self['ident'], msg_data])
    if done:
      self.end_reply()

  def reply_exc(self, exc, done=True):
    envelope = {'msg_id': self['msg_id'],
                'cmd': 'reply',
                'exc': str(exc),
                'data': {}}
    msg_data = json.dumps(envelope)
    self.stream.sock.send_multipart([self['ident'], msg_data])
    if done:
      self.end_reply()

  def end_reply(self):
    msg = {'msg_id': self['msg_id'],
           'cmd': 'end_reply'}
    msg_data = json.dumps(msg)
    self.stream.sock.send_multipart([self['ident'], msg_data])

  def send(self, msg, *args):
    logging.debug('SSEND> %s', [msg % args])
    self.stream.sock.send_multipart([msg % args])


class ConnectContext(dict):
  # ident
  # sock
  def __init__(self, stream, data):
    super(ConnectContext, self).__init__(**json.loads(data))
    self.stream = stream

  def reply(self, msg, done=True):
    try:
      msg = msg.to_dict()
    except AttributeError:
      pass
    envelope = {'msg_id': self['msg_id'],
                'cmd': 'reply',
                'data': msg}
    msg_data = json.dumps(envelope)
    self.stream.sock.send_multipart([msg_data])
    if done:
      self.end_reply()

  def end_reply(self):
    msg = {'msg_id': self['msg_id'],
           'cmd': 'end_reply'}
    msg_data = json.dumps(msg)
    self.stream.sock.send_multipart([msg_data])

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

    q = self.stream.register_channel(msg['msg_id'])

    self.stream.sock.send_multipart([msg_data])
    with timeout.Timeout(3):
      try:
        while True:
          time.sleep(FLAGS.sleep_time)
          if not q.empty():
            rv = q.get(timeout=5)
            if rv == StopIteration:
              break
            if 'exc' in rv:
              raise RemoteError(rv['exc'])
            yield rv['data']
      except queue.Empty:
        pass

    self.stream.deregister_channel(msg['msg_id'])

  def send(self, msg, *args):
    logging.debug('CSEND> %s', [msg % args])
    self.stream.sock.send_multipart([msg % args])


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
      time.sleep(FLAGS.sleep_time)
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
      time.sleep(FLAGS.sleep_time)
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


