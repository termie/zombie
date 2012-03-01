"""Don't you dare close your eyes."""

import functools
import zmq

from zombie import shared


def serve(address, handler):
  sock = shared.zctx.socket(zmq.XREP)
  sock.bind(address)
  print 'listening on %s' % address
  while True:
    parts = sock.recv_multipart()
    shared.pool.spawn(handle_cmd, sock, parts, handler)


def invalid_cmd(context, cmd, *msg_parts):
  context.reply('invalid cmd %s: %s' % (cmd, msg_parts))


def handle_cmd(sock, msg_parts, handler):
  ctx = Context(sock=sock, ident=msg_parts.pop(0))
  cmd = msg_parts.pop(0)
  print '<<< %s %s' % (cmd, msg_parts)
  f = getattr(handler, 'cmd_%s' % cmd, functools.partial(invalid_cmd, cmd))
  f(ctx, *msg_parts)


class Context(dict):
  # ident
  # sock

  def reply(self, msg, *args):
    self['sock'].send_multipart([self['ident'], msg % args])


class World(object):
  """Handle the tasks a world must handle. So heavy is this burden.

  A world is in charge of a few things:
    - Providing addresses for locations (lookup_location)
    - Providing a default location for new users (default_location)

  """

  def __init__(self, location_db):
    self.location_db = location_db

  def cmd_lookup_location(self, context, location_id):
    return context.reply(self.location_db.get(location_id))

  def cmd_default_location(self, context):
    return self.cmd_lookup_location(context, 'default')


class Location(object):
  """Handle the tasks a location must handle. That which never ends.

  A location is in charge of a few things:
    - Broadcasting events to everybody in the location
    - Checking whether a user is allowed to enter (enter)
    - Allowing a user to leave (leave)
    - Providing information about itself (look)

  """

  def __init__(self, data):
    self.data = data

  def cmd_enter(self, context, valid_entry):
    """Decide whether to allow a user to enter. Announce if success.

    In the basic case a user needs to present some sort of validation token,
    usually from an adjoining location, that proves this user left that
    location towards this one. Something like::

      signed(old_location, ('leave', old_location, new_location))

    In plausibly more advanced cases (e.g. teleportation), a teleportation
    credential may be added::

      signed(old_location, ('teleport', old_location, new_location))

    The new location should probably additionally verify this entry token
    with the world to prevent a user from being in multiple spots.
    """
    pass

  def cmd_leave(self, context, new_location):
    """Decide whether to allow a user to leave. Announce if success.

    This is pretty much always successful but possibly some puzzles will want
    to make this more difficult.

    Should provide a valid entry token for the new location.

    In the basic case only allow leaving to adjacent locations.
    """
    context.reply((self.data.get('id'), new_location))

  def cmd_look(self, context):
    return context.reply(self.data)
