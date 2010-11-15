import json

class Context(object):
  def __init__(self, ident, sock, pool, **kw):
    self.ident = ident
    self.sock = sock
    self.pool = pool
    self.session_key = None
    for k, v in kw.iteritems():
      setattr(self, k, v)


  def reply(self, msg):
    self.sock.send_multipart([self.ident, msg])


  def __str__(self):
    return repr(self.__dict__)
