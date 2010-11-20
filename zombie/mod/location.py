import json

import eventlet
from eventlet.green import zmq

from zombie import crypt
from zombie import event
from zombie import kvs
from zombie import log as logging
from zombie import shared
from zombie import util
from zombie.mod import accounts

r = kvs.Storage('locations_')

@accounts.auth_required
def last_seen(ctx, parsed):
  ctx['last_seen'] = r.get('last_seen_' + ctx['who'])


@accounts.auth_required
def default_location(ctx, parsed):
  loc = util.deserialize(r.get('default'))
  loc_ref = Location(**loc)

  ctx.reply(parsed, location=str(loc_ref))
  return True

# Locations get a topic, objects in that location are
# expected to subscribe to it, events there are published to subscribers
# each location should act as a singleton

LOCATIONS = {}

def list_all():
  return util.deserialize(r.get('all'))



class Location(event.EventEmitter):
  def __init__(self, id, caddress=None, paddress=None, dsa_priv=None,
               dsa_pub=None, session_key=None, name=None, exits=None, **kw):
    super(Location, self).__init__()
    self.id = id
    self.caddress = str(caddress)
    self.paddress = str(paddress)
    self.dsa_pub = crypt.PublicVerifierKey.from_key('dsa_pub', dsa_pub)
    self.dsa_priv = crypt.PrivateSignerKey.from_key('dsa_priv', dsa_priv)
    self.session_key = session_key
    self.name = name
    self.exits = exits
    self._sock = None
    self.pulses_per_second = 40

  def init(self):
    pass

  @classmethod
  def load(cls, location_id):
    if location_id not in LOCATIONS:
      info = util.deserialize(r.get(location_id))
      session_key = kvs.get('session_key_' + location_id)
      info['session_key'] = session_key
      location = cls(**info)
      LOCATIONS[location_id] = location
    return LOCATIONS[location_id]

  def to_dict(self):
    return {'id': self.id, 'control_address': self.caddress}
  
  def __str__(self):
    return util.serialize(self.to_dict())
  
  def location_loop(self):
    while True:
      eventlet.sleep(1 / self.pulses_per_second)


def load_from_file(filename):
  """Helper function to create location databases."""
  fp = open(filename)
  locations = json.load(fp)
  fp.close()

  # sanity checks
  by_id = dict((x['id'], x) for x in locations)
  for loc in locations:
    for exit in loc['exits']:
      if exit['location'] not in by_id:
        logging.warning('location<%s> has hanging exit: %s',
                        loc['id'], exit['location'])
      else:
        recip = [x['location'] for x in by_id[exit['location']]['exits']]

        if loc['id'] not in recip:
          logging.warning('location<%s> has one-way exit to: %s',
                          loc['id'], exit['location'])


    dsa_priv = crypt.PrivateSignerKey.generate('location_' + loc['id'])
    dsa_pub = crypt.PublicVerifierKey.load('location_' + loc['id'])
    
    loc['dsa_priv'] = str(dsa_priv)
    loc['dsa_pub'] = str(dsa_pub)
    loc['caddress'] = 'ipc:///tmp/' + loc['id']
    loc['paddress'] = 'ipc:///tmp/' + loc['id'] + 'pub'
    if loc.get('default', 0):
      logging.info('setting default location: %s', loc['id'])
      r.set('default', util.serialize(loc))
    r.set(loc['id'], util.serialize(loc))

  r.set('all', util.serialize(by_id.keys()))
