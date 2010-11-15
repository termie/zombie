
import gen_key
import zmq


if __name__ == '__main__':
  name = 'bar'
  #signer = gen_key.RedisSigner.Read(name)
  bind = 'ipc:///tmp/foo'


  ctx = zmq.Context()
  s = ctx.socket(zmq.PUB)
  s.bind(bind)
  
  i = 0
  while True:
    #out = signer.Sign(str(i))
    s.send_multipart(['foo', str(i)])
    i += 1
