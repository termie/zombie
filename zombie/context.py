from zombie import log as logging
from zombie import util

class Context(dict):
  def __init__(self, *args, **kw):
    dict.__init__(self, *args, **kw)

  def send(self, msg, sig):
    self['sock'].send_multipart([self['ident'], msg, sig])

  def reply(self, parsed, **kw):
    response = {}
    response.update(kw)
    if 'uuid' in parsed:
      response['uuid'] = parsed['uuid']
    encrypted = self['session_key'].encrypt(util.serialize(response))
    if self['world']:
      signer = self['world'].dsa_priv
    elif self['location']:
      signer = self['location'].dsa_priv

    sig = signer.sign(encrypted)
    self.send(encrypted, sig)

  def error(self, msg):
    if not self['world']:
      pass
    pass

  def __str__(self):
    return repr(self)
