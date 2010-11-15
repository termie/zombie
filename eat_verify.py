
import gen_key
import zmq


if __name__ == '__main__':
  name = 'bar'
  signer = gen_key.RedisSigner.Read(name)
  bind = 'ipc:///tmp/foo'
  
  ctx = zmq.Context()
  s = ctx.socket(zmq.SUB)
  s.connect(bind)
  
  s.setsockopt(zmq.SUBSCRIBE, 'f')

  try:
    while True:
      topic, msg, sig = s.recv_multipart()
      valid = signer.Verify(msg, sig)
      if valid:
        print msg
      else:
        print 'INVALID'
  except KeyboardInterrupt:
    pass

  print 'Done.'
