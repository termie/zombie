import json
import logging

import gflags
from eventlet import event

from zombie import model
from zombie import net
from zombie import shared


class User(object):
  description = 'A user.'

  def __init__(self, id):
    self.id = id

  def cmd_look(self, ctx):
    """Somebody is looking at you, what do you tell them."""
    ctx.reply({'description': self.description})

  def cmd_tell(self, ctx, message):
    pass

  def on_event(self, ctx, topic, data):
    pass


class Shell(object):
  """Provide a nice interface to the client."""
  def __init__(self, client):
    self.client = client
    self._exits = {}
    self.ls = 'Uhhh, you just typed ls, try look() instead.'

  def _out(self, s):
    print s

  def debug(self, value=True):
    if value:
      logging.getLogger().setLevel(logging.DEBUG)
    else:
      logging.getLogger().setLevel(logging.WARNING)

  def exits(self):
    self._out('Exits: %s' % ', '.join(self._exits.keys()))
    return self._exits

  def look(self, other_id=None):
    if not other_id:
      rv = self.client._look()
      self._exits = rv['exits']
      self._out('%s\nExits: %s' % (rv['description'],
                                   ', '.join(rv['exits'].keys())))
      return self.client.location

    rv = self.client._look_at_other(other_id)
    if 'description' in rv:
      self._out(rv['description'])
    rv = self.client._interact(other_id, 'look')
    if 'description' in rv:
      self._out(rv['description'])

  def move(self, name):
    if name in self._exits:
      exit_id = self._exits[name]
    else:
      exit_id = name
    self.client._move_location(exit_id)
    return self.look()


class Client(object):
  """Holds on to a user object and uses it to interact with the game.

  This represents the high level interface to interacting with the game
  while the User is what holds on to state.

  """
  def __init__(self, user):
    self.user = user
    self.world = None
    self.location = None
    self.id = self.user.id

  def verify(self, msg_parts):
    data, caller_id, sig = msg_parts
    assert sig == 'signature'

  def _connect_to_world(self, address):
    """Establish a connection to the main world.

    After that you'll most likely reconnect to the User's last location.
    """
    self.world_handler = self
    world_ev = event.Event()
    self.world_stream = net.Stream(self.world_handler)
    shared.pool.spawn(self.world_stream.connect, address, world_ev.send)
    logging.debug('WAITING')
    world_context = world_ev.wait()
    logging.debug('FINSIHED')
    self.world = WorldClient(self.user, world_context)
    return self.world

  def _connect_to_location(self, address):
    """Establish a connection to a given location.

    After that you'll most likely try to join the location.
    """
    self.location_handler = self
    loc_ev = event.Event()

    self.location_stream = net.Stream(self.location_handler)
    shared.pool.spawn(self.location_stream.connect, address, loc_ev.send)
    loc_context = loc_ev.wait()
    self.location = LocationClient(self.user, loc_context)
    return self.location

  def _rejoin_game(self, address):
    """Go through all the steps to get back into game.

    - Connect to the world.
    - Request last location.
    - Connect to last location
    - Join last location with reconnect token.
    """
    world = self._connect_to_world(address)
    last_loc = world.last_location()
    logging.debug('LAST LOC %s', last_loc)
    loc_address = last_loc['address']
    join_token = last_loc['join_token']

    location = self._connect_to_location(loc_address)
    location.join(join_token)

  def _move_location(self, new_location):
    """Send the move command to the current location using the new location.

    The location will send back a move token for the new location (after
    getting it signed by the world.)

    After that it will send a disconnect to this client and the client
    will connect to the new location and attempt to join.
    """
    move_rv = self.location.move(new_location)
    address = move_rv['address']
    join_token = move_rv['join_token']
    self.location.disconnect()

    location = self._connect_to_location(address)
    location.join(join_token)

  def _look_at_other(self, other_id):
    look_rv = self.location.look_at_other(other_id)
    return look_rv

  def _interact(self, other_name, verb, data=None):
    data = data or {}
    rv = self.location.interact(other_name, verb, data)
    return rv

  def _look(self):
    return self.location.look()

  def _say(self, s):
    return self.location.say(s)

  def cmd_look(self, ctx):
    return self.user.cmd_look(ctx)

  def cmd_route(self, ctx, other_id, package):
    if self.id != other_id:
      # ignore these for now
      return
    msg_parts = json.loads(package)
    self.verify(msg_parts)
    new_ctx = ctx.repack(msg_parts)
    new_ctx.stream.handle_cmd(new_ctx)

  def __getattr__(self, key):
    if key.startswith('on_') or key.startswith('cmd_'):
      return getattr(self.user, key)
    raise AttributeError(key)


class ObjectProxy(object):
  """Represent a remote object locally.

  The goal here is for methods called on the local objects to result in
  calls to the remote objects, providing an nicer UI in the shell.
  """
  def __init__(self, location_client, object_name):
    self.location = location_client
    self.object_name = object_name

  def __getattr__(self, key):
    def _proxy(data=None):
      return self.location.interact(self.object_name, key, data)

    _proxy.func_name = '_proxy_%s' % key
    setattr(self, key, _proxy)
    return _proxy


class LocationClient(object):
  """Interface to the various commands we might send to a location."""

  def __init__(self, user, ctx):
    self.ctx = ctx
    self.user = user

  def disconnect(self):
    self.ctx.stream.close()

  def join(self, join_token):
    """Attempt the join the location."""
    rv = self.ctx.send_cmd('join', data={'join_token': join_token})
    success = rv.next()
    return success

  def move(self, new_location_id):
    """Send the move command.

    Returns:
      {'address': <new_location_address>
       'join_token': {'user': <username>,
                      'location_id': <new location_id>,
                      'from_id': <last_location_id>}
        }
    """
    rv = self.ctx.send_cmd('move', data={'user_id': self.user.id,
                                         'new_location_id': new_location_id})
    move_rv = rv.next()
    return move_rv

  def look(self):
    rv = self.ctx.send_cmd('look')
    return rv.next()

  def interact(self, other_name, verb, data=None):
    data = data or {}
    rv = self.ctx.interact_cmd(other_name, verb, data)
    # TODO(termie): this should probably return the iterator, but right now
    #               everything expects the return values to be congealed
    #               results
    return rv.next()

  def look_at_other(self, other_id):
    rv = self.ctx.route_cmd(other_id, 'look', {})
    return rv.next()

  def say(self, s):
    rv = self.ctx.send_cmd('say', {'message': s})
    return rv.next()

  def send_cmd(self, *args, **kwargs):
    return self.ctx.send_cmd(*args, **kwargs)


class WorldClient(object):
  """Interface to the various commands we might send to a world."""

  def __init__(self, user, ctx):
    self.ctx = ctx
    self.user = user

  def last_location(self):
    """Request the current user's last location."""
    rv = self.ctx.send_cmd('last_location', data={'user_id': self.user.id})
    last_loc = rv.next()
    return last_loc

  def send_cmd(self, *args, **kwargs):
    return self.ctx.send_cmd(*args, **kwargs)
