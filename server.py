import sys

import eventlet
from eventlet import greenpool
from eventlet import greenthread
from eventlet.green import zmq
from eventlet.hubs import use_hub

use_hub('zeromq')

from zombie import context
from zombie import router
from zombie import world
from zombie import net


# TODO(termie): allow requesting pubkey via http


if __name__ == '__main__':
  bind = 'ipc:///tmp/foo'

  foo = world.World.load('foo')
  server = net.Server(foo)
  server.listen(bind)
