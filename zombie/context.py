import logging

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

    response_s = util.dumps(response)
    if 'session_key' in self:
      response_s = self['session_key'].encrypt(response_s)

    signer = self['node'].dsa_priv

    sig = signer.sign(response_s)
    self.send(response_s, sig)

  def error(self, msg):
    if not self['world']:
      pass
    pass

  def __str__(self):
    return repr(self)
