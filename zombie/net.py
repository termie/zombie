import logging
import uuid

import eventlet
from eventlet import event as e_event
from eventlet.green import zmq

from zombie import context
from zombie import crypt
from zombie import hooks
from zombie import shared
from zombie import util


class Server(object):
  """Servers handle normal connections and publishing connections."""

  def __init__(self, proxy):
    self.proxy = proxy
    self._psock = None
    self._paddress = None
    self._csock = None
    self._caddress = None

  def init_control(self, address):
    """Set up the control socket."""
    sock = shared.zctx.socket(zmq.XREP)
    sock.bind(address)
    self._caddress = address
    self._csock = sock

  def init_pubsub(self, address):
    """Set up the pubsub socket."""
    sock = shared.zctx.socket(zmq.PUB)
    sock.bind(address)
    self._paddress = address
    self._psock = sock
    self._pkey = crypt.SessionKey.generate('pubsub_' + uuid.uuid4().hex)
    self.proxy.on('notify', self._handle_notify)

  def control_loop(self):
    while True:
      msg_parts = self._csock.recv_multipart()
      ident = msg_parts.pop(0)
      ident_b64 = util.b64_encode(ident)
      c = context.Context(ident=ident,
                          ident_b64=ident_b64,
                          sock=self._csock,
                          pool=shared.pool)
      rv = shared.pool.spawn(self._handle_control, c, msg_parts)
      eventlet.sleep(0.1)

  def _handle_notify(self, msg):
    self._psock.send_multipart([msg, self._sign(msg)])

  def _handle_control(self, ctx, msg_parts):
    logging.info('routing: %s, %s', *msg_parts)

    # special case to request pubkey, everything else will be encrypted
    if msg_parts[0] == 'dsa_pub':
      self._cmd_dsa_pub(ctx)

    msg, sig = msg_parts

    # if we have a session first try to decrypt the message using that key
    try:
      session_key = crypt.SessionKey.load(self.proxy.name + ctx['ident_b64'])
    except Exception:
      session_key = None

    if not session_key:
      parsed = util.deserialize(msg)
      logging.debug('parsed (unencrypted): %s', parsed)
      if parsed.get('method') != 'session_start':
        raise exception.Error('no session key found')
      return self._cmd_session_start(ctx, parsed)

    logging.info('session key found')
    try:
      decrypted = session_key.decrypt(msg)
    except Exception as e:
      raise exception.Error('invalid session')

    ctx['session_key'] = session_key

    try:
      parsed = util.deserialize(decrypted)
    except Exception as e:
      raise exception.Error('no message found')

    logging.debug('parsed: %s', parsed)
    if parsed.get('method') == 'subscribe_start':
      if self.proxy.authenticate(ctx, parsed, msg, sig):
        return self._cmd_subscribe_start(ctx, parsed)

    try:
      return self.proxy.handle(ctx, parsed, msg, sig)
    except Exception as e:
      logging.exception('in proxy.handle')
      raise exception.Error('unexpected error')

  def _cmd_dsa_pub(self, ctx):
    logging.debug('DSA_PUB')
    msg = str(self.proxy.dsa_pub)
    ctx.send(msg, self._sign(msg))

  def _cmd_subscribe_start(self, ctx, parsed):
    logging.debug('new subscriber')
    msg = util.serialize({'subscribe_key': str(self._pkey),
                          'subscribe_address': str(self._paddress),
                          'uuid': parsed['uuid'],
                          })
    msg = ctx['session_key'].encrypt(msg)
    sig = self._sign(msg)
    ctx.send(msg, sig)

  def _cmd_session_start(self, ctx, parsed):
    """The client sent us its pubkey, send it an encrypted session key."""
    logging.debug('starting new session')
    session_key = crypt.SessionKey.generate(self.proxy.name + ctx['ident_b64'])
    rsa_pub = parsed.get('rsa_pub')
    encrypter = crypt.PublicEncrypterKey.from_key(ctx['ident_b64'],
                                                  parsed.get('rsa_pub'))
    out = {'session_key': str(session_key)}
    out['uuid'] = 0
    msg = util.serialize(out)
    logging.debug('serialized, length: %s', len(msg))
    msg = encrypter.encrypt(msg)
    sig = self._sign(msg)
    ctx.send(msg, sig)
    logging.debug('sent session_start response')

  def _sign(self, s):
    return self.proxy.dsa_priv.sign(s)


class NodeServer(object):
  """Servers handle normal connections and publishing connections."""

  def __init__(self, node):
    self.node = node
    self._psock = None
    self._paddress = None
    self._csock = None
    self._caddress = None

  def init_control(self, address):
    """Set up the control socket."""
    sock = shared.zctx.socket(zmq.XREP)
    sock.bind(address)
    self._caddress = address
    self._csock = sock

  def control_loop(self):
    while True:
      msg_parts = self._csock.recv_multipart()
      ident = msg_parts.pop(0)
      ident_b64 = util.b64_encode(ident)
      c = context.Context(ident=ident,
                          client_id=ident_b64,
                          sock=self._csock)
      rv = shared.pool.spawn(self._handle_control, c, msg_parts)
      eventlet.sleep(0.1)

  def _handle_control(self, ctx, msg_parts):
    logging.info('routing: %s, %s', *msg_parts)

    msg, sig = msg_parts

    # parse the message if we can
    try:
      parsed = util.loads(msg)
    except Exception:
      parsed = {}

    try:
      ctx['node'] = self.node
      self.node.handle(ctx, parsed, msg, sig)
    except Exception as e:
      ctx.reply(parsed, error=str(e))


class NodeClient(object):
  def __init__(self, node):
    self._clooping = False
    self._csock = None
    self._caddress = None
    self._plooping = False
    self._psock = None
    self._paddress = None
    self._waiters = {}
    self._connected = False
    self._session_key = None
    self.node = node

  def connect_control(self, address, name):
    sock = shared.zctx.socket(zmq.XREQ)
    sock.connect(address)

    self._csock = sock
    self._caddress = address
    self._cname = name

    # Get the server's signing key to verify everything else
    # TODO(termie): obviously we would expect to have this on file already
    #               if we trusted the server
    #sock.send_multipart(['dsa_pub', self._sign('dsa_pub')])
    #dsa_pub, sig = sock.recv_multipart()
    #dsa_pub_key = crypt.PublicVerifierKey.from_key(address, dsa_pub)
    #self._server_key = dsa_pub_key

    # Start our session
    rv = self.rpc('session_start', rsa_pub=str(self.node.rsa_pub), uuid=0)
    self._session_key = crypt.SessionKey.from_key('session', rv['session_key'])

  def connect_pubsub(self):
    # We get the subscription address via the main connection
    rv = self.rpc('subscribe_start')
    self._skey = crypt.SessionKey.from_key('subscribe', rv['subscribe_key'])
    self._paddress = str(rv['subscribe_address'])

    zctx = shared.zctx
    sock = zctx.socket(zmq.SUB)
    sock.setsockopt(zmq.SUBSCRIBE, '')
    sock.connect(self._paddress)
    self._psock = sock
    logging.debug('subscribed to %s', self._paddress)

  def rpc(self, method, **kw):
    logging.debug('rpc: %s', method)
    msg = {'method': method}
    msg['uuid'] = uuid.uuid4().hex
    msg.update(kw)
    ev = e_event.Event()
    self._wait_for(msg['uuid'], ev)
    self.sign_and_send(msg)

    # for the clientloop to run while we are waiting
    def _forceloop():
      while not ev.ready():
        self.control_loop(once=True)

    shared.pool.spawn_n(_forceloop)
    rv = ev.wait()
    logging.debug('got response for %s', method)
    return rv

  def sign_and_send(self, msg):
    msg['self'] = self.node.name
    msg = util.dumps(msg)
    logging.debug('sending: %s', msg)
    if self._session_key:
      msg = self._session_key.encrypt(msg)
    sig = self._sign(msg)
    return self._csock.send_multipart([msg, sig])

  def control_loop(self, once=False):
    while True:
      if self._clooping:
        eventlet.sleep(0.1)
        return
      self._clooping = True
      if self._csock:
        msg = self._crecv()
        if msg:
          self.node.handle(self, msg)
      self._clooping = False
      if once:
        return
      eventlet.sleep(0.1)

  def pubsub_loop(self, once=False):
    while True:
      if self._plooping:
        eventlet.sleep(0.1)
        return
      self._plooping = True
      if self._psock:
        msg = self._srecv()
        if msg:
          self.node.handle(self, msg)
      self._plooping = False
      if once:
        return
      eventlet.sleep(0.1)

  def verify(self, s, sig):
    return self.node.verify_trusted_sig(s, self._cname, sig)
    #return self._server_key.verify(s, sig)

  def _wait_for(self, key, ev):
    self._waiters[key] = ev

  def _crecv(self):
    logging.debug('_crecv(%s)', self._caddress)
    if not self._csock:
      return
    msg, sig = self._csock.recv_multipart()
    logging.debug('ctrl_msg %s', msg)
    valid = self.verify(msg, sig)
    if not valid:
      return

    if self._session_key:
      msg = self._session_key.decrypt(msg)
    else:
      msg = self.node.rsa_priv.decrypt(msg)

    msg = util.loads(msg)
    logging.debug('ctrl_msg(decrypt): %s', msg)
    if msg['uuid'] in self._waiters:
      self._waiters[msg['uuid']].send(msg)
      del self._waiters[msg['uuid']]

    return msg

  def _srecv(self):
    logging.debug('_srecv(%s)', self._paddress)
    if not self._psock:
      return

    msg, sig = self._psock.recv_multipart()
    logging.debug('sub_msg %s', msg)
    valid = self.verify(msg, sig)
    if not valid:
      return

    msg = self._subscribe_key.decrypt(msg)
    msg = util.loads(msg)
    return msg

  def _sign(self, s):
    return self.node.dsa_priv.sign(s)


class Client(object):
  def __init__(self, proxy):
    self._clooping = False
    self._csock = None
    self._caddress = None
    self._plooping = False
    self._psock = None
    self._paddress = None
    self._waiters = {}
    self._connected = False
    self._session_key = None
    self.proxy = proxy

  def connect_control(self, address):
    sock = shared.zctx.socket(zmq.XREQ)
    sock.connect(address)

    self._csock = sock
    self._caddress = address

    # Get the server's signing key to verify everything else
    # TODO(termie): obviously we would expect to have this on file already
    #               if we trusted the server
    #sock.send_multipart(['dsa_pub', self._sign('dsa_pub')])
    #dsa_pub, sig = sock.recv_multipart()
    #dsa_pub_key = crypt.PublicVerifierKey.from_key(address, dsa_pub)
    #self._server_key = dsa_pub_key

    # Start our session
    rv = self.rpc('session_start', rsa_pub=str(self.proxy.rsa_pub), uuid=0)
    self._session_key = crypt.SessionKey.from_key('session', rv['session_key'])

  def connect_pubsub(self):
    # We get the subscription address via the main connection
    rv = self.rpc('subscribe_start')
    self._skey = crypt.SessionKey.from_key('subscribe', rv['subscribe_key'])
    self._paddress = str(rv['subscribe_address'])

    zctx = shared.zctx
    sock = zctx.socket(zmq.SUB)
    sock.setsockopt(zmq.SUBSCRIBE, '')
    sock.connect(self._paddress)
    self._psock = sock
    logging.debug('subscribed to %s', self._paddress)

  def rpc(self, method, **kw):
    logging.debug('rpc: %s', method)
    msg = {'method': method}
    msg['uuid'] = uuid.uuid4().hex
    msg.update(kw)
    ev = e_event.Event()
    self._wait_for(msg['uuid'], ev)
    self.sign_and_send(msg)

    # for the clientloop to run while we are waiting
    def _forceloop():
      while not ev.ready():
        self.control_loop(once=True)

    shared.pool.spawn_n(_forceloop)
    rv = ev.wait()
    logging.debug('got response for %s', method)
    return rv

  def sign_and_send(self, msg):
    msg['self'] = self.proxy.name
    msg = util.dumps(msg)
    logging.debug('sending: %s', msg)
    if self._session_key:
      msg = self._session_key.encrypt(msg)
    sig = self._sign(msg)
    return self._csock.send_multipart([msg, sig])

  def control_loop(self, once=False):
    while True:
      if self._clooping:
        eventlet.sleep(0.1)
        return
      self._clooping = True
      if self._csock:
        msg = self._crecv()
        if msg:
          self.proxy.handle(self, msg)
      self._clooping = False
      if once:
        return
      eventlet.sleep(0.1)

  def pubsub_loop(self, once=False):
    while True:
      if self._plooping:
        eventlet.sleep(0.1)
        return
      self._plooping = True
      if self._psock:
        msg = self._srecv()
        if msg:
          self.proxy.handle(self, msg)
      self._plooping = False
      if once:
        return
      eventlet.sleep(0.1)

  def verify(self, s, sig):
    return self._server_key.verify(s, sig)

  def _wait_for(self, key, ev):
    self._waiters[key] = ev

  def _crecv(self):
    logging.debug('_crecv(%s)', self._caddress)
    if not self._csock:
      return
    msg, sig = self._csock.recv_multipart()
    logging.debug('ctrl_msg %s', msg)
    valid = self.verify(msg, sig)
    if not valid:
      return

    if self._session_key:
      msg = self._session_key.decrypt(msg)
    else:
      msg = self.proxy.rsa_priv.decrypt(msg)

    msg = util.loads(msg)
    logging.debug('ctrl_msg(decrypt): %s', msg)
    if msg['uuid'] in self._waiters:
      self._waiters[msg['uuid']].send(msg)
      del self._waiters[msg['uuid']]

    return msg

  def _srecv(self):
    logging.debug('_srecv(%s)', self._paddress)
    if not self._psock:
      return

    msg, sig = self._psock.recv_multipart()
    logging.debug('sub_msg %s', msg)
    valid = self.verify(msg, sig)
    if not valid:
      return

    msg = self._subscribe_key.decrypt(msg)
    msg = util.loads(msg)
    return msg

  def _sign(self, s):
    return self.proxy.dsa_priv.sign(s)

