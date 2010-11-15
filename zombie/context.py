import json

class Context(object):
  def __init__(self, ident, sock, pool, **kw):
    self.ident = ident
    self.sock = sock
    self.pool = pool
    self.session_key = None
    for k, v in kw.iteritems():
      setattr(self, k, v)


  def reply(self, msg_parts):
    msg_parts.insert(0, self.ident)
    self.sock.send_multipart(msg_parts)


  def __str__(self):
    return repr(self.__dict__)
