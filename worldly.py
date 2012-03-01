#!/usr/bin/env python

import sys

import gflags

from zombie import new_world
from zombie import shared


FLAGS = gflags.FLAGS
gflags.DEFINE_string('bind_address', 'ipc:///tmp/foo', 'bind address')


location_db = {'default': 'ipc:///tmp/default'}

default_location = {'id': 'default',
                    'address': 'ipc:///tmp/default',
                    'description': 'default location'}


if __name__ == '__main__':
  args = FLAGS(sys.argv)
  world = new_world.World(location_db)
  shared.pool.spawn(new_world.serve, FLAGS.bind_address, world)

  default_location = new_world.Location(default_location)
  shared.pool.spawn(new_world.serve, location_db['default'], default_location)
  shared.pool.waitall()
