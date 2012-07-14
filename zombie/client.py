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
    ctx.reply({self.id: {'description': self.description}})

class Client(object):
  """Holds on to a user object and uses it to interact with the game.

  This represents the high level interface to interacting with the game
  while the User is what holds on to state.

  """
  def __init__(self, user):
    self.user = user
    self.world = None
    self.location = None

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

  def cmd_look(self, ctx):
    return self.user.cmd_look(ctx)


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

  def look_at_other(self, other_id):
    rv = self.ctx.send_cmd('look_at_other', {'other_id': other_id})
    return rv.next()



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

