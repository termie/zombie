import eventlet
eventlet.monkey_patch()

from zombie import net
from zombie import shared
from zombie import world


# TODO(termie): allow requesting pubkey via http


if __name__ == '__main__':
  #bind = 'tcp://0.0.0.0:4000'
  bind = 'ipc:///tmp/foo'
  pbind = 'ipc:///tmp/foopub'
  pool = shared.pool

  foo = world.World.load('foo')
  print 'initializing world'
  foo.init()

  print 'starting worldloop'
  worldloop = pool.spawn(foo.worldloop)
  
  server = net.Server(foo)
  print 'listening for connections'
  pool.spawn(server.listen, bind)

  print 'publisher active'
  pool.spawn(server.publish, pbind)
  
  worldloop.wait()
  print 'done'
