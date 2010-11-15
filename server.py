import eventlet
eventlet.monkey_patch()

from zombie import net
from zombie import shared
from zombie import world


# TODO(termie): allow requesting pubkey via http


if __name__ == '__main__':
  bind = 'ipc:///tmp/foo'
  pool = shared.pool

  foo = world.World.load('foo')
  print 'initializing world'
  foo.init()

  print 'starting worldloop'
  worldloop = pool.spawn(foo.worldloop)
  
  server = net.Server(foo)
  print 'listening for connections'
  pool.spawn(server.listen, bind)
  
  worldloop.wait()
  print 'done'
