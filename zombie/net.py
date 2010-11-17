import eventlet
from eventlet.green import zmq

from zombie import context
from zombie import crypt
from zombie import hooks
from zombie import log as logging
from zombie import shared
from zombie import util


class ServerInfo(object):
  def __init__(self, address, dsa_pub):
    self.address = address
    self.dsa_pub = dsa_pub


class Server(object):
  def __init__(self, world):
    self.world = world

  def listen(self, address):
    ctx = shared.zmq_context
    sock = ctx.socket(zmq.XREP)
    sock.bind(address)
    pool = shared.pool

    self._sock = sock

    while True:
      msg_parts = sock.recv_multipart()
      ident = msg_parts.pop(0)
      c = context.Context(ident=ident, sock=sock, pool=pool)
      pool.spawn(self._route, c, msg_parts)
      eventlet.sleep(0.1)

  def _route(self, ctx, msg_parts):
    logging.info('routing')
    # special case to request pubkey, everything else will be encrypted
    if msg_parts[0] == 'dsa_pub':
      self._on_dsa_pub(ctx)

    msg, sig = msg_parts

    # if we have a session first try to decrypt the message using that key
    try:
      session_key = crypt.SessionKey.load(ctx.ident_b64)
    except Exception:
      session_key = None
    
    if session_key:
      logging.info('session key found')
      try:
        decrypted = session_key.decrypt(msg)
        ctx.session_key = session_key
        parsed = util.deserialize(decrypted)
        return self.world.handle(ctx, parsed, msg, sig)
      except Exception:
        pass
    
    # if we didn't have a session or we couldn't decrypt it this is probably
    # a session initiation request
    try:
      parsed = util.deserialize(msg)
      if parsed.get('method') == 'session_start':
        self._on_session_start(ctx, parsed)
    except Exception:
      pass

  def _on_dsa_pub(self, ctx):
    msg = str(self.world.dsa_pub)
    ctx.send(msg, self.sign(msg))

  def sign(self, s):
    return self.world.dsa_priv.sign(s)

  def _on_session_start(self, ctx, parsed):
    """The client sent us its pubkey, send it an encrypted session key."""
    logging.debug('starting new session')
    session_key = crypt.SessionKey.generate(ctx.ident_b64)
    rsa_pub = parsed.get('rsa_pub')
    encrypter = crypt.PublicEncrypterKey.from_key(
        ctx.ident_b64, parsed.get('rsa_pub'))
    msg = util.serialize({'session_key': str(session_key)})
    msg = encrypter.encrypt(msg)
    sig = self.sign(msg)
    ctx.send(msg, sig)


class Client(object):
  def __init__(self, character):
    self.character = character
    self._sock = None
    self._connected = False
    self.serverinfo = None
    self.session_key = None

  def connect(self, address):
    self.address = address

    ctx = shared.zmq_context

    sock = ctx.socket(zmq.XREQ)
    self._sock = sock

    sock.connect(self.address)
    
    # Get the server's signing key
    sock.send_multipart(['dsa_pub', self.sign('dsa_pub')])
    dsa_pub, sig = sock.recv_multipart()

    dsa_pub_key = crypt.PublicVerifierKey.from_key(address, dsa_pub)
    logging.debug('received dsa_pub')

    self.serverinfo = ServerInfo(address, dsa_pub_key)
    
    self.session_key = self._session_start()
    self._connected = True
    logging.debug('session started')
    hooks.run('session_start', self)
    logging.debug('after hooks')

  def _session_start(self):
    msg = util.serialize({'method': 'session_start',
                          'rsa_pub': str(self.character.rsa_pub)})
    self._sock.send_multipart([msg, self.sign(msg)])
    logging.debug('sent session_start')
    session_key, sig = self._sock.recv_multipart()
    logging.debug('received session key')
    valid = self.verify(session_key, sig)
    if not valid:
      return

    rv = self.character.rsa_priv.decrypt(session_key)
    rv = util.deserialize(rv)
    return crypt.SessionKey.from_key('session', rv['session_key'])
    
  def sign(self, s):
    return self.character.dsa_priv.sign(s)

  def verify(self, s, sig):
    return self.serverinfo.dsa_pub.verify(s, sig)

  def send(self, msg):
    if type(msg) != type({}):
      msg = {'method': 'raw', 'raw': msg}
    msg['self'] = self.character.name
    logging.debug('send > %s', msg)
    msg = util.serialize(msg)
    msg = self.session_key.encrypt(msg)
    sig = self.character.dsa_priv.sign(msg)
    return self._sock.send_multipart([msg, sig])

  def recv(self):
    msg, sig = self._sock.recv_multipart()
    valid = self.serverinfo.dsa_pub.verify(msg, sig)
    if not valid:
      return
    msg = self.session_key.decrypt(msg)
    msg = util.deserialize(msg)
    return msg

  def clientloop(self):
    while True:
      msg = self.recv()
      self.character.handle(client, msg)
      eventlet.sleep(0.1)
