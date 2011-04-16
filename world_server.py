#!/usr/bin/env python
import eventlet
eventlet.monkey_patch()

import logging

from zombie import net
from zombie import shared
from zombie import world


if __name__ == '__main__':
  cbind = 'ipc:///tmp/foo'
  pbind = 'ipc:///tmp/foopub'

  logging.getLogger().setLevel(logging.DEBUG)
  logging.info('loading world')
  #foo = world.World.load('foo')
  #foo.init()
  foo = world.WorldNode.Load('foo')


  #server = net.Server(foo)
  server = net.NodeServer(foo)

  logging.info('listening on control address')
  server.init_control(cbind)

  #logging.info('listening on pubsub address')
  #server.init_pubsub(pbind)

  # push the loops
  logging.info('starting control loop')
  shared.pool.spawn(server.control_loop)

  #logging.info('starting world loop')
  #shared.pool.spawn(foo.world_loop)

  shared.pool.waitall()
