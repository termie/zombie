import eventlet
eventlet.monkey_patch()

from zombie import log as logging
from zombie import net
from zombie import shared
from zombie.mod import location


if __name__ == '__main__':
  import sys

  logging.info('loading location')
  foo = location.Location.load(sys.argv[1])
  foo.init()

  server = net.Server(foo)

  print foo
  logging.info('listening on control address')
  server.init_control(foo.caddress)

  logging.info('listening on pubsub address')
  server.init_pubsub(foo.paddress)

  # push the loops
  logging.info('starting control loop')
  shared.pool.spawn(server.control_loop)

  logging.info('starting location loop')
  shared.pool.spawn(foo.location_loop)

  shared.pool.waitall() 
