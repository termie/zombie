#!/usr/bin/env python

"""Run a whole world in a single process.

Requires location fixtures to load.
"""

import eventlet
eventlet.monkey_patch()

import logging
import os
import pprint
import sys

# If ../zombie/__init__.py exists, add ../ to Python search path, so that
# it will override what happens to be installed in /usr/(local/)lib/python...
possible_topdir = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]),
                                   os.pardir,
                                   os.pardir))
if os.path.exists(os.path.join(possible_topdir, 'zombie', '__init__.py')):
    sys.path.insert(0, possible_topdir)


import gflags
import zmq

from zombie import location
from zombie import model
from zombie import net
from zombie import shared
from zombie import world


FLAGS = gflags.FLAGS
gflags.DEFINE_string('locations', 'fixtures/locations.txt',
                     'where to look for location fixtures')
gflags.DEFINE_string('user', 'darkthorn',
                     'id of default user')
gflags.DEFINE_string('last_location', 'awakening',
                     'id of starting location for default user')
gflags.DEFINE_string('bind', 'tcp://127.0.0.1',
                     'bind host for world and locations')
gflags.DEFINE_integer('port', '2222',
                      'port for the world')

def load_locations(path):
  """Quick naive parser for our silly location definition language."""
  o = []
  current = {}
  for line in open(path):
    line = line.strip()
    if 'id' not in current and line:
      current['id'] = line
    elif line.startswith('EXITS'):
      current['exits'] = {}
    elif 'id' in current and 'exits' not in current:
      desc = current.get('description', [])
      desc.append(line)
      current['description'] = desc
    elif 'exits' in current:
      if line:
        name, location = line.split(': ', 1)
        current['exits'][name] = location
      else:
        current['description'] = '\n'.join(current['description'])
        o.append(current)
        current = {}
  return o


def main():
  logging.basicConfig()
  logging.getLogger().setLevel(logging.DEBUG)
  world_address = '%s:%s' % (FLAGS.bind, FLAGS.port)
  locations = load_locations(FLAGS.locations)
  pprint.pprint(locations)

  # squat some random ports so we can add the addresses to our locations
  ports = []
  for i in range(len(locations)):
    sock = shared.zctx.socket(zmq.XREQ)
    ports.append(sock.bind_to_random_port(FLAGS.bind))
    sock.close()

  pprint.pprint(ports)
  for loc in locations:
    port = ports.pop(0)
    loc['address'] = '%s:%s' % (FLAGS.bind, port)

  # Generate our state objects
  default_user = model.User.from_kwargs(id=FLAGS.user,
                                        last_location=FLAGS.last_location)
  w_user_db = world.WorldUserDatabase(**{FLAGS.user: default_user.to_dict()})
  w_loc_db = world.WorldLocationDatabase(**dict((loc['id'], loc)
                                                 for loc in locations))

  w_ref = world.World(location_db=w_loc_db, user_db=w_user_db, world_id='foo')
  loc_refs = []
  for loc in locations:
    loc_ref = location.Location(user_db=location.LocationUserDatabase(),
                                location_id=loc['id'],
                                exits=loc['exits'],
                                address=loc['address'])
    loc_refs.append(loc_ref)

  # Launch all the servers
  shared.pool.spawn(net.Stream(w_ref).serve, world_address)
  for loc_ref in loc_refs:
    shared.pool.spawn(net.Stream(loc_ref).serve, loc_ref.address)
    loc_ref._connect_to_world(world_address)
  shared.pool.waitall()

if __name__ == '__main__':
  FLAGS(sys.argv)
  main()
