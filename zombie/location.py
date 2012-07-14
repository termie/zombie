import logging

from eventlet import event

from zombie import db
from zombie import model
from zombie import net
from zombie import shared


class Location(object):
  """Handle the tasks a location must handle. That which never ends.

  A location is in charge of a few things:
    - Broadcasting events to everybody in the location
    - Checking whether a user is allowed to enter (join)
    - Allowing a user to leave (move)
    - Providing information about itself (look)

  """
  description = 'A location.'

  def __init__(self, user_db, location_id, exits):
    self.user_db = user_db
    self.location_id = location_id
    self.id = location_id
    self.exits = exits
    #self.keys = Keystore()

  def verify(self, msg_parts):
    data, caller_id, sig = msg_parts
    assert sig == 'signature'

  def _connect_to_world(self, address):
    """Establish a connection to the main world.

    """
    self.world_handler = self
    world_ev = event.Event()
    self.world_stream = net.Stream(self.world_handler)
    shared.pool.spawn(self.world_stream.connect, address, world_ev.send)
    logging.debug('WAITING')
    world_context = world_ev.wait()
    logging.debug('FINSIHED')
    self.world = LocationWorldClient(self, world_context)
    return self.world

  def cmd_join(self, ctx, join_token):
    """Handle a user trying to join this location.

    If the join_token looks good, get the world to update the last location
    in the db.
    """
    # TODO(termie): verify join token
    join_token_ref = model.JoinToken.from_dict(join_token)
    self.world.update_user_location(join_token)
    ctx.reply({'result': 'ok'})

    # Add the user to our local db
    self.user_db.set(join_token_ref.user_id, ctx)

    # Announce the user's entrance, if applicable.
    #self.broadcast_joined(ctx.username, join_token['from_id'])

  def cmd_move(self, ctx, user_id, new_location_id):
    """Provide the user with a join_token for the new location."""
    logging.debug('LOC MOVE')
    o = self.world.make_join_token(user_id, self.location_id, new_location_id)
    logging.debug('BEFORE LOC_MOVE REPLY')
    ctx.reply(o)
    logging.debug('AFTER LOC_MOVE')
    self.user_db.delete(user_id)

  def cmd_look(self, ctx):
    o = {'description': self.description,
         'exits': self.exits,
         'users': self.user_db.keys()}
    return ctx.reply(o)

  def cmd_route(self, ctx, other_id, package):
    """Route a message to another user in this location.

    This will envelope the package to be routed.

    Results will be sent back to the caller.
    """
    other_ctx = self.user_db.get(other_id)

  def cmd_look_at_other(self, ctx, other_id):
    other_ctx = self.user_db.get(other_id)
    rv = other_ctx.send_cmd('look')
    for x in rv:
      ctx.reply(x)


class LocationWorldClient(object):
  """Interface to the various commands we might send to a world."""

  def __init__(self, location, ctx):
    self.ctx = ctx
    self.location = location

  def update_user_location(self, join_token):
    """Set the user's last location."""
    rv = self.ctx.send_cmd('update_user_location',
                           data={'join_token': join_token})
    return rv.next()

  def make_join_token(self, user_id, from_id, location_id):
    rv = self.ctx.send_cmd('make_join_token',
                           data={'user_id': user_id,
                                 'from_id': from_id,
                                 'location_id': location_id})
    logging.debug('FOO_LOC_WORLD')
    o = rv.next()
    logging.debug('AFTER FOO_LOC_WORLD')
    return o


class LocationUserDatabase(db.Kvs):
  #deserialize = model.User.from_dict
  pass


