import eventlet
from eventlet import greenpool
from eventlet import greenthread
from eventlet.green import zmq
from eventlet.hubs import use_hub

use_hub('zeromq')

import zmq

from zombie import crypt
from zombie import util


_ZMQ_CONTEXT = None
def zmq_context():
  global _ZMQ_CONTEXT
  if not _ZMQ_CONTEXT:
    _ZMQ_CONTEXT = zmq.Context()
  return _ZMQ_CONTEXT


class ServerInfo(object):
  def __init__(self, address, dsa_pub):
    self.address = address
    self.dsa_pub = dsa_pub


class Client(object):
  def __init__(self, character):
    self.character = character

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



