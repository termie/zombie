import eventlet
eventlet.monkey_patch()


from zombie import net
from zombie import shared
from zombie.mod import locations


# TODO(termie): allow requesting pubkey via http


if __name__ == '__main__':
  import sys
  #bind = 'tcp://0.0.0.0:4000'
  #bind = 'ipc:///tmp/foo'
  #pbind = 'ipc:///tmp/foopub'
  pool = shared.pool

  foo = locations.Location.load(sys.argv[1])
  print 'initializing location'
  foo.init()

  print 'starting locationloop'
  locationloop = pool.spawn(foo.locationloop)
  
  server = net.Server(foo)
  print 'listening for connections'
  pool.spawn(server.listen, foo.laddress)

  print 'publisher active'
  pool.spawn(server.publish, foo.paddress)
  
  locationloop.wait()
  print 'done'
