
class BaseObject(object):
  def located(self, location):
    pass

class ActiveObject(BaseObject):
  pass


class ControlHandle(object):
  def __init__(self, ident, session_key):
    pass

class ProxyObject(BaseObject):
  def __init__(self, control_handle):
    pass
  def handle(self, ctx, parsed):

    pass
  pass
