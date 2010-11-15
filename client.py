import sys

import zmq
from zmq.eventloop import ioloop
from zmq.eventloop import zmqstream

# allow requesting pubkey via http


if __name__ == '__main__':
  bind = 'ipc:///tmp/foo'

  loop = ioloop.IOLoop.instance()
  
  ctx = zmq.Context()
  s = ctx.socket(zmq.XREQ)
  s.connect(bind)

  stream = zmqstream.ZMQStream(s, loop)

  def echo(msg):
    print msg

  stream.on_recv(echo)

  def spew():
    stream.send('pubkey')

  tim = ioloop.PeriodicCallback(spew, 1000, loop)
  tim.start()
  
  loop.start()
