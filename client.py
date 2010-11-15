
from zombie import character
from zombie import net


if __name__ == '__main__':
  bind = 'ipc:///tmp/foo'

  termie = character.Character.load('termie')
  client = net.Client(termie)
  client.connect(bind)


  #loop = ioloop.IOLoop.instance()
  
  #ctx = zmq.Context()
  #s = ctx.socket(zmq.XREQ)
  #s.connect(bind)

  ## Make sure we have our own keys
  #my_keyname = 'foo'
  #try:
  #  my_privkey = crypt.PrivateCrypterKey.load(my_keyname)
  #  my_pubkey = crypt.PublicEncrypterKey.load(my_keyname)
  #except Exception:
  #  my_privkey = crypt.PrivateCrypterKey.generate(my_keyname)
  #  my_pubkey = crypt.PublicEncrypterKey.load(my_keyname)
  
  ## Get the server's pubkey
  #s.send('pubkey')
  #pubkey = s.recv()
  #print pubkey

  #msg = {'method': 'session_init',
  #       'pubkey': str(my_pubkey)}

  #msg = util.serialize(msg)
  #s.send(msg)

  #sesskey = s.recv()
  #print sesskey
  #sesskey = my_privkey.decrypt(sesskey)
  #print sesskey
  #sesskey = util.deserialize(sesskey)

  #my_sesskey = crypt.SessionKey.from_key('session', sesskey['session_key'])
  
  #msg = {'method': 'echo', 'foo': 'bar'}
  #s.send(my_sesskey.encrypt(util.serialize(msg)))

  #rv = s.recv()
  #print rv
  #rv = my_sesskey.decrypt(rv)
  #print rv



  ##stream = zmqstream.ZMQStream(s, loop)

  ##def echo(msg):
  ##  print msg

  ##stream.on_recv(echo)

  ##def spew():
  ##  stream.send('pubkey')

  ##tim = ioloop.PeriodicCallback(spew, 1000, loop)
  ##tim.start()
  
  ##loop.start()
