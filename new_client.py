

from zombie import shared


class User(object):
  pass


class Client(object):
  """A client manages the connections to remote servers for a user.

  This includes joining and leaving locations.
  """

  def __init__(self, user):
    self.user = user
    self.world_sock = None
    self.location_sock = None

  def connect_world(self, world_address):
    """Connect to a world.

    Get last location, rejoin.
    """

  def join_location(self, location_address, join_from=None):
    """Join a location.

    There are two types of joining:

      a) You are reconnecting, the world provides you a token that says
         you are already in the given location. The location announces
         a "reconnect" style entry.

      b) You are coming from another location, the previous location contacts
         the world and provides you with a token that you hand to the new
         location, the new location either accepts the token and acks with
         the world (setting your location with the world) or rejects and you
         are unable to join.
    """


