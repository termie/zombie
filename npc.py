

# - signing objects you create
# - all communications are encrypted
# - p2p file sharing (maybe built in bittorrent client?)

# - join a secret server to get special things, badges or membership privileges


# Roles:
# - server to provide pubkey
#   - pubkey
#   - private communiation (open up new secure connection)
# - accept events from server and update local state
# - send events to server to attempt to update global state

class World(object):
  def on_join(self, obj):
    # update world state
    self.render_object_at_position(obj['position'], obj)

  def on_leave(self, obj):
    self.forget_object(obj)


class You(object):
  def move(self, vector):
    pass

  def say(self, message, loudness):
    pass

  def on_pubkey_request(self, request):
    # provide pubkey
    pass

  def on_hear(self, message):
    # possibly notify
    pass

  def on_chat(self, message):
    # accept if already known

  def join_server(self, server):
    # issue connect request
    # receive world state
    # possibly disconnect from existing server
    pass

  def give_item(self, item, recipient):
    pass
