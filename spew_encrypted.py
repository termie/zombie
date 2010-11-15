
import gen_key
import zmq


if __name__ == '__main__':
  name = 'foo'
  crypter = gen_key.RedisCrypter.Read(name)
  bind = 'ipc:///tmp/foo'


  ctx = zmq.Context()
  s = ctx.socket(zmq.PUB)
  s.bind(bind)
  
  i = 0
  while True:
    out = crypter.Encrypt(str(i))
    s.send_multipart(['foo', out])
    i += 1
