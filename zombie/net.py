import uuid

import eventlet
from eventlet import event as e_event
from eventlet.green import zmq

from zombie import context
from zombie import crypt
from zombie import hooks
from zombie import log as logging
from zombie import shared
from zombie import util


class Server(object):
  """Servers handle normal connections and publishing connections."""

  def __init__(self, proxy):
    self.proxy = proxy
    self._psock = None
    self._paddress = None
    self._lsock = None
    self._laddress = None

  def listen(self, address):
    zctx = shared.zmq_context
    pool = shared.pool
    sock = zctx.socket(zmq.XREP)
    sock.bind(address)

    self._laddress = address
    self._lsock = sock

    while True:
      msg_parts = sock.recv_multipart()
      ident = msg_parts.pop(0)
      ident_b64 = util.b64_encode(ident)
      c = context.Context(ident=ident,
                          ident_b64=ident_b64,
                          sock=sock,
                          pool=pool)
      rv = pool.spawn(self._route, c, msg_parts)
      eventlet.sleep(0.1)

  def publish(self, address):
    zctx = shared.zmq_context
    pool = shared.pool
    sock = zctx.socket(zmq.PUB)
    sock.bind(address)

    self._paddress = address
    self._psock = sock
    
    self._pkey = crypt.SessionKey.generate('publish_' + uuid.uuid4().hex)
    self.proxy.on('notify', self._notify)
    
  def _notify(self, msg):
    self._psock.send_multipart([msg, self._sign(msg)])

  def _route(self, ctx, msg_parts):
    logging.info('routing: %s, %s', *msg_parts)

    # special case to request pubkey, everything else will be encrypted
    if msg_parts[0] == 'dsa_pub':
      self._on_dsa_pub(ctx)

    msg, sig = msg_parts

    # if we have a session first try to decrypt the message using that key
    try:
      session_key = crypt.SessionKey.load(self.proxy.name + ctx['ident_b64'])
    except Exception:
      session_key = None
    
    if session_key:
      logging.info('session key found')
      try:
        decrypted = session_key.decrypt(msg)
        ctx['session_key'] = session_key
        parsed = util.deserialize(decrypted)
        logging.debug('parsed: %s', parsed)
        if parsed.get('method') == 'subscribe_start':
          return self._on_subscribe_start(ctx, parsed)
        return self.proxy.handle(ctx, parsed, msg, sig)
      except Exception:
        pass
    
    # if we didn't have a session or we couldn't decrypt it this is probably
    # a session initiation request
    try:
      parsed = util.deserialize(msg)
      logging.debug('parsed (unencrypted): %s', parsed)
      if parsed.get('method') == 'session_start':
        self._on_session_start(ctx, parsed)
    except Exception:
      pass

  def _on_dsa_pub(self, ctx):
    logging.debug('DSA_PUB')
    msg = str(self.proxy.dsa_pub)
    ctx.send(msg, self._sign(msg))

  def _on_subscribe_start(self, ctx, parsed):
    logging.debug('new subscriber')
    msg = util.serialize({'subscribe_key': str(self._pkey),
                          'subscribe_address': str(self._paddress),
                          'uuid': parsed['uuid'],
                          })
    msg = ctx['session_key'].encrypt(msg)
    sig = self._sign(msg)
    ctx.send(msg, sig)

  def _on_session_start(self, ctx, parsed):
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


class Client(object):
  def __init__(self, proxy):
    self._clooping = False
    self._csock = None
    self._caddress = None
    self._slooping = False
    self._ssock = None
    self._saddress = None
    self._waiters = {}
    self._connected = False
    self._session_key = None
    self.proxy = proxy

  def connect(self, address):
    zctx = shared.zmq_context
    sock = zctx.socket(zmq.XREQ)
    sock.connect(address)

    self._csock = sock
    self._caddress = address

    # Get the server's signing key to verify everything else
    # TODO(termie): obviously we would expect to have this on file already
    #               if we trusted the server
    sock.send_multipart(['dsa_pub', self._sign('dsa_pub')])
    dsa_pub, sig = sock.recv_multipart()
    dsa_pub_key = crypt.PublicVerifierKey.from_key(address, dsa_pub)
    self._server_key = dsa_pub_key

    # Start our session
    self._session_key = self._session_start()

  def subscribe(self):
    # We get the subscription address via the main connection
    rv = self.rpc('subscribe_start')
    self._skey = crypt.SessionKey.from_key('subscribe', rv['subscribe_key'])
    self._saddress = str(rv['subscribe_address'])

    zctx = shared.zmq_context
    sock = zctx.socket(zmq.SUB)
    sock.setsockopt(zmq.SUBSCRIBE, '')
    sock.connect(self._saddress)
    self._ssock = sock
    logging.debug('subscribed to %s', self._saddress)
  
  def rpc(self, method, **kw):
    logging.debug('rpc: %s', method)
    msg = {'method': method}
    msg['uuid'] = uuid.uuid4().hex
    msg.update(kw)
    ev = e_event.Event()
    self._add_rpc_waiter(msg['uuid'], ev)
    self._sign_and_send(msg)
    
    # for the clientloop to run while we are waiting
    def _runloop():
      while not ev.ready():
        self.controlloop(once=True)

    shared.pool.spawn_n(_runloop)
    rv = ev.wait()
    logging.debug('got response for %s', method)
    return rv

  def _session_start(self):
    rv = self.rpc('session_start', rsa_pub=str(self.proxy.rsa_pub), uuid=0)
    return crypt.SessionKey.from_key('session', rv['session_key'])
  
  def _add_rpc_waiter(self, key, ev):
    self._waiters[key] = ev
  
  def _crecv(self):
    logging.debug('_crecv(%s)', self._caddress)
    if not self._csock:
      return
    msg, sig = self._csock.recv_multipart()
    logging.debug('ctrl_msg %s', msg)
    valid = self._server_key.verify(msg, sig)
    if not valid:
      return

    if self._session_key:
      msg = self._session_key.decrypt(msg)
    else:
      msg = self.proxy.rsa_priv.decrypt(msg)
      
    msg = util.deserialize(msg)
    if msg['uuid'] in self._waiters:
      self._waiters[msg['uuid']].send(msg)
      del self._waiters[msg['uuid']]

    return msg

  def _srecv(self):
    logging.debug('_srecv(%s)', self._saddress)
    if not self._ssock:
      return
    
    msg, sig = self._ssock.recv_multipart()
    logging.debug('sub_msg %s', msg)
    valid = self._server_key.verify(msg, sig)
    if not valid:
      return
    
    msg = self._subscribe_key.decrypt(msg)
    msg = util.deserialize(msg)
    return msg

  def _sign_and_send(self, msg):
    msg['self'] = self.proxy.name
    msg = util.serialize(msg)
    logging.debug('sending: %s', msg)
    if self._session_key:
      msg = self._session_key.encrypt(msg)
    sig = self._sign(msg)
    return self._csock.send_multipart([msg, sig])

  def _sign(self, s):
    return self.proxy.dsa_priv.sign(s)

  def _verify(self, s, sig):
    return self.serverinfo.dsa_pub.verify(s, sig)

  def controlloop(self, once=False):
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

  def subscribeloop(self, once=False):
    while True:
      if self._slooping:
        eventlet.sleep(0.1)
        return
      self._slooping = True
      if self._ssock:
        msg = self._srecv()
        if msg:
          self.proxy.handle(self, msg)
      self._slooping = False
      if once:
        return
      eventlet.sleep(0.1)
