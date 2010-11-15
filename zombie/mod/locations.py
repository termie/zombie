import json

from eventlet.green import zmq

from zombie import crypt
from zombie import kvs
from zombie import log as logging
from zombie import shared
from zombie import util

r = kvs.Storage('locations_')

def last_seen(ctx, parsed):
  ctx.last_seen = kvs.get('last_seen_' + ctx.who)

# Locations get a topic, objects in that location are
# expected to subscribe to it, events there are published to subscribers
# each location should act as a singleton

LOCATIONS = {}

def list_all():
  return util.deserialize(kvs.get('all'))

class Location(object):
  def __init__(self, id, address, dsa_priv=None, dsa_pub=None,
               session_key=None):
    self.id = id
    self.address = address
    self._sock = None

  def init(self):
    ctx = shared.zmq_context
    sock = ctx.socket(zmq.PUB)
    sock.bind(self.address)
    self._sock = sock

  @classmethod
  def load(cls, location_id):
    if location_id not in LOCATIONS:
      info = kvs.get(location_id)
      session_key = kvs.get('session_key_' + location_id)
      info['session_key'] = session_key
      location = cls(**info)
      location.init()
      LOCATIONS[location_id] = location
    return LOCATIONS[location_id]

  def add_object(self, obj, referer=None):
    self.objects.append(obj)
    obj.located(location)
    hooks.run('add_object', location, obj, referer)


def load_from_file(filename):
  """Helper function to create location databases."""
  fp = open(filename)
  locations = json.load(fp)
  fp.close()

  # sanity checks
  by_id = dict((x.id, x) for x in locations)
  for loc in locations:
    for exit in loc.exits:
      if exit.location not in by_id:
        logging.warning('location<%s> has hanging exit: %s',
                        loc.id, exit.location)
      else:
        recip = [x.location for x in by_id[exit.location].exits]

        if loc.id not in recip:
          logging.warning('location<%s> has one-way exit to: %s',
                          loc.id, exit.location)


    dsa_priv = crypt.PrivateSignerKey.generate('location_' + loc.id)
    dsa_pub = crypt.PublicVerifierKey.load('location_' + loc.id)
    
    loc['dsa_priv'] = str(dsa_priv)
    loc['dsa_pub'] = str(dsa_pub)
    r.set(loc.id, util.serialize(loc))

  r.set('all', util.serialize(by_id.keys())

if __name__ == '__main__':
  import sys
  load_from_file(sys.argv[1])
