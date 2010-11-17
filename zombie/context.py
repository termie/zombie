from zombie import log as logging
from zombie import util

class Context(object):
  def __init__(self, ident, sock, pool, **kw):
    self.ident = ident
    self.sock = sock
    self.pool = pool
    self.session_key = None
    for k, v in kw.iteritems():
      setattr(self, k, v)

  @property
  def ident_b64(self):
    return util.b64_encode(self.ident)

  def send(self, msg, sig):
    self.sock.send_multipart([self.ident, msg, sig])

  def error(self, msg):
    if not self.world:
      pass
    pass

  def __str__(self):
    return repr(self.__dict__)
