import eventlet
eventlet.monkey_patch()

from zombie import log as logging
from zombie import net
from zombie import shared
from zombie import world


if __name__ == '__main__':
  cbind = 'ipc:///tmp/foo'
  pbind = 'ipc:///tmp/foopub'


  logging.info('loading world')
  foo = world.World.load('foo')
  foo.init()

  server = net.Server(foo)

  logging.info('listening on control address')
  server.init_control(cbind)

  logging.info('listening on pubsub address')
  server.init_pubsub(pbind)
  
  # push the loops
  logging.info('starting control loop')
  shared.pool.spawn(server.control_loop)

  logging.info('starting world loop')
  shared.pool.spawn(foo.world_loop)

  shared.pool.waitall()