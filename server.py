import sys

import eventlet
from eventlet import greenpool
from eventlet import greenthread
from eventlet.green import zmq
from eventlet.hubs import use_hub

use_hub('zeromq')

from zombie import router
from zombie import context


# TODO(termie): allow requesting pubkey via http


if __name__ == '__main__':
  bind = 'ipc:///tmp/foo'

  pool = greenpool.GreenPool()
  
  ctx = zmq.Context()
  sock = ctx.socket(zmq.XREP)
  sock.bind(bind)
  
  router = router.Router()

  def slow_reply(sock, ident, msg):
    sock.send_multipart([ident, msg])

  while True:
    msg_parts = sock.recv_multipart()
    ident = msg_parts.pop(0)
    c = context.Context(ident=ident, sock=sock, pool=pool)
    pool.spawn_n(router.route, c, msg_parts[0])
