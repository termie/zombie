"""Scriptable NPC / items.

Premise is that there are a few types of triggers:
  - Time: do something every so often
  - Local event: something happened nearby that we care about
  - Direct player interaction: user tried to interact with us

Responses are also governed by a few kinds of state:
  - Location state: something fundamental in this location has changed
                    (similar to a local event, but static)
  - World state: something fundamental has changed
  - Local state: some other trigger has already caused our state to change
"""

from zombie import client
from zombie import shared


class EventMatcher(object):
  def match(self, event):
    return False


class RegexEventMatcher(object):
  """Match based on the string message content."""

  regex = None

  def match(self, event):
    msg = event['msg']
    if regex.match(msg):
      return True
    return False


class Npc(object):
  description = 'An NPC.'

  def __init__(self, npc_id, description=None):
    self.id = npc_id
    if description:
      self.description = description

  def react_time(self, time_desc, callback):
    """Do something based on some time check."""
    # TODO(termie): probably requires some mini-description language to define
    #               when to do stuff, punting for now.
    pass

  def react_event(self, matcher, callback):
    self._event_matchers.append((matcher, callback))

  def on_event(self, ctx, evt):
    for matcher, callback in self._event_matchers:
      if matcher.match(evt):
        shared.pool.spawn(callback, ctx, evt)

  def cmd_look(self, ctx):
    ctx.reply({'description': self.description})


class ObjectNpc(Npc):
  def __init__(self, obj_id, description=None):
    super(ObjectNpc, self).__init__(obj_id, description=description)


def spawn_object(obj, address):
  cl = client.Client(obj)
  cl._connect_to_location(address)
  rv = cl.location.send_cmd('join_as_object')
  rv.next()
  return cl



