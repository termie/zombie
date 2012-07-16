import logging
import time

from eventlet import event

from zombie import db
from zombie import model
from zombie import net
from zombie import shared


LOG = logging.getLogger(__name__)


class Location(object):
  """Handle the tasks a location must handle. That which never ends.

  A location is in charge of a few things:
    - Broadcasting events to everybody in the location
    - Checking whether a user is allowed to enter (join)
    - Allowing a user to leave (move)
    - Providing information about itself (look)

  """
  description = 'A location.'

  def __init__(self, user_db, location_id, exits, address): #, broadcast):
    self.user_db = user_db
    self.location_id = location_id
    self.id = location_id
    self.exits = exits
    self.address = address
    #self.broadcast = broadcast
    #self.keys = Keystore()

  def debug(self, msg, *args, **kw):
    """Quick, naive helper to add some data to log messages."""
    # TODO(termie): refactor this into logging library
    msg = '%s:%s:' + msg
    args = list(args)
    args.insert(0, self.__class__.__name__)
    args.insert(1, self.id)
    LOG.debug(msg, *args, **kw)

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
    world_context = world_ev.wait()
    self.world = LocationWorldClient(self, world_context)
    return self.world

  def broadcast(self, topic, data):
    self.debug('BROADCAST %s: %s', topic, data)
    evt = {'topic': topic,
           'data': data}
    for ctx in self.user_db.values():
      ctx.send_cmd('event', data=evt, noreply=True)


  def _location_to_direction(self, from_id):
    for k, v in self.exits.iteritems():
      if v == from_id:
        return k

  def broadcast_joined(self, user_id, from_id):
    direction = self._location_to_direction(from_id)

    if direction:
      msg = '%s entered from the %s.' % (user_id, direction)
    else:
      msg = '%s rejoined.' % user_id
    self.broadcast('joined', {'user_id': user_id,
                              'from_id': from_id,
                              'message': msg})


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
    # TODO(termie): possibly should provide some original contect
    #               to verify the action causing this broadcast
    self.broadcast_joined(ctx.caller_id, join_token['from_id'])

  def cmd_move(self, ctx, user_id, new_location_id):
    """Provide the user with a join_token for the new location."""
    o = self.world.make_join_token(user_id, self.location_id, new_location_id)
    ctx.reply(o)
    self.user_db.delete(user_id)

  def cmd_look(self, ctx):
    o = {'description': self.description,
         'exits': self.exits,
         'users': self.user_db.keys()}
    return ctx.reply(o)

  def cmd_say(self, ctx, message):
    self.broadcast('said', {'user_id': ctx.caller_id,
                            'message': '%s said "%s"' % (ctx.caller_id,
                                                         message),
                            'raw_message': message})
    ctx.reply({'result': 'ok'})

  def cmd_route(self, ctx, other_id, package):
    """Route a message to another user in this location.

    This will envelope the package to be routed.

    Results will be sent back to the caller.
    """
    self.debug('ROUTE TO %s', other_id)
    other_ctx = self.user_db.get(other_id)
    rv = other_ctx.send_cmd('route', {'other_id': other_id,
                                      'package': package})
    for x in rv:
      ctx.reply(x)

  def cmd_interact(self, ctx, other_name, verb):
    """Interact with the location.

    In most cases these interactions will be with with items that are not
    explicitly visible but are described in the room's description.
    """


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
    o = rv.next()
    return o


class LocationUserDatabase(db.Kvs):
  #deserialize = model.User.from_dict
  pass


