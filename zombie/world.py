import logging

from zombie import db
from zombie import model


class World(object):
  """Handle the tasks a world must handle. So heavy is this burden.

  A world is in charge of a few things:
    - (x) Providing addresses for locations (lookup_location)
    - (x) Providing a default location for new users (default_location)
    - ( ) Keeping track of the locations of all users (accept_move)
  """

  def __init__(self, location_db, user_db, world_id=None):
    self.location_db = location_db
    self.user_db = user_db
    self.id = world_id

  def verify(self, msg_parts):
    data, caller_id, sig = msg_parts
    assert sig == 'signature'

  def cmd_lookup_location(self, ctx, location_id):
    return ctx.reply({location_id: self.location_db.get(location_id)})

  def cmd_default_location(self, ctx):
    return self.cmd_lookup_location(ctx, 'default')

  def cmd_last_location(self, ctx, user_id):
    """Get the last location for the given user and return a join token."""
    last_location_id = self.user_db.last_location(user_id)
    location_ref = self.location_db.get(last_location_id)
    o = {'address': location_ref.address,
         'join_token': {'user_id': user_id,
                        'location_id': last_location_id,
                        'from_id': last_location_id,
                        }
         }
    return ctx.reply(o)

  def cmd_update_user_location(self, ctx, join_token):
    # verify the token is valid
    # verify the token is for the location that is sending it
    join_token_ref = model.JoinToken.from_dict(join_token)
    user_ref = self.user_db.get(join_token_ref.user_id)
    user_ref.last_location = join_token_ref.location_id
    self.user_db.set(join_token_ref.user_id, user_ref)
    return ctx.reply({'result': 'ok'})

  def cmd_make_join_token(self, ctx, user_id, from_id, location_id):
    # TODO(termie): verify that the locations connect
    location_ref = self.location_db.get(location_id)
    token = model.JoinToken.from_dict({'user_id': user_id,
                                       'from_id': from_id,
                                       'location_id': location_id})
    logging.debug('BEFORE WORLD_JOIN')
    ctx.reply({'address': location_ref.address,
               'join_token': token.to_dict()})
    logging.debug('AFTER WORLD_JOIN')


class WorldUserDatabase(db.Kvs):
  """Interface for accessing user data."""
  deserialize = model.User.from_dict

  def last_location(self, user_id):
    """Return the last location for a given user_id."""
    user_ref = self.get(user_id)
    return user_ref.last_location


class WorldLocationDatabase(db.Kvs):
  """Interface for accessing location data."""
  deserialize = model.Location.from_dict


