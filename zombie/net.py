import eventlet
from eventlet import greenpool
from eventlet import greenthread
from eventlet.green import zmq
from eventlet.hubs import use_hub

use_hub('zeromq')

from zombie import context
from zombie import crypt
from zombie import util


_ZMQ_CONTEXT = None
def zmq_context():
  global _ZMQ_CONTEXT
  if not _ZMQ_CONTEXT:
    _ZMQ_CONTEXT = zmq.Context()
  return _ZMQ_CONTEXT

_GREEN_POOL = None
def green_pool():
  global _GREEN_POOL
  if not _GREEN_POOL:
    _GREEN_POOL = greenpool.GreenPool()
  return _GREEN_POOL



class ServerInfo(object):
  def __init__(self, address, dsa_pub):
    self.address = address
    self.dsa_pub = dsa_pub


class Server(object):
  def __init__(self, world):
    self.world = world

  def listen(self, address):
    ctx = zmq_context()
    sock = ctx.socket(zmq.XREP)
    sock.bind(address)
    pool = green_pool()

    self._sock = sock

    while True:
      msg_parts = sock.recv_multipart()
      ident = msg_parts.pop(0)
      c = context.Context(ident=ident, sock=sock, pool=pool)
      pool.spawn_n(self._route, c, msg_parts[0])

  def _route(self, ctx, msg):
    print 'routing'
    # special case to request pubkey, everything else will be encrypted
    if msg == 'dsa_pub':
      self._on_dsa_pub(ctx, msg)

    # if we have a session first try to decrypt the message using that key
    try:
      session_key = crypt.SessionKey.load(ctx.ident_b64)
    except Exception:
      session_key = None

    if session_key:
      try:
        decrypted = session_key.decrypt(msg)
        ctx.session_key = session_key
        parsed = util.deserialize(decrypted)
        return self.world.handle(ctx, parsed)
      except exception.Error:
        pass
    
    # if we didn't have a session or we couldn't decrypt it this is probably
    # a session initiation request
    try:
      parsed = util.deserialize(msg)
      if parsed.get('method') == 'session_start':
        self._on_session_start(ctx, msg)
    except Exception:
      pass

  def _on_dsa_pub(self, ctx, msg):
    ctx.send(str(self.world.dsa_pub))

  def on_session_start(self, ctx, msg):
    """The client sent us its pubkey, send it an encrypted session key."""
    session_key = crypt.SessionKey.generate(ctx.ident)
    encrypter = crypt.PublicEncrypterKey.from_key(ctx.ident, msg.get('rsa_pub'))
    msg = util.serialize({'session_key': str(session_key)})
    ctx.send(encrypter.encrypt(msg))


class Client(object):
  def __init__(self, character):
    self.character = character
    self._sock = None
    self._connected = False
    self.serverinfo = None
    self.session_key = None

  def connect(self, address):
    self.address = address

    ctx = zmq_context()

    sock = ctx.socket(zmq.XREQ)
    self._sock = sock

    sock.connect(self.address)
    
    # Get the server's signing key
    sock.send('dsa_pub')
    dsa_pub = sock.recv()

    dsa_pub_key = crypt.PublicVerifierKey.from_key(address, dsa_pub)
    self.serverinfo = ServerInfo(address, dsa_pub_key)
    
    self.session_key = self._session_start()
    self._connected = True

  def _session_start(self):
    msg = util.serialize({'method': 'session_start',
                          'rsa_pub': str(self.character.rsa_pub)})
    self._sock.send(msg)
    rv = self.character.rsa_priv.decrypt(self._sock.recv())
    rv = util.deserialize(rv)
    return crypt.SessionKey.from_key('session', rv['session_key'])
    
  def send(self, msg):
    msg = util.serialize(msg)
    msg = self.session_key.encrypt(msg)
    return self._sock.send(msg)

  def recv(self):
    msg = self._sock.recv()
    msg = self.session_key.decrypt(msg)
    msg = util.deserialize(msg)
    return msg



