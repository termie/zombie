from zombie import crypt
from zombie import exception
from zombie import session
from zombie import util

def session_required(f):
  def _wrapper(self, ctx, *args, **kw):
    if not getattr(ctx, 'session_key'):
      raise exception.Error('session key required')
    return f(self, ctx, *args, **kw)
  _wrapper.func_name = f.func_name
  return _wrapper

class Router(object):
  def __init__(self):
    self._session = session.Manager()
    self._crypt = crypt.Manager()

  def route(self, ctx, msg):
    print ctx
    handler = self._get_handler(ctx, msg)
    if handler:
      rv = handler(ctx, msg)
      if rv:
        ctx.reply(rv)
  
  def _get_handler(self, ctx, msg):
    # special case to request pubkey, everything else will be encrypted
    if msg == 'pubkey':
      return self.on_pubkey, msg

    # if we have a session first try to decrypt the message using that key
    session_key = self._session.get(ctx.ident)
    decrypted = None
    if session_key:
      try:
        decrypted = session_key.decrypt(msg)
        ctx.session_key = session_key
        parsed = util.deserialize(decrypted)
      except exception.Error:
        pass
    
    # if we didn't have a session or we couldn't decrypt it this is probably
    # a session initiation request
    if not decrypted:
      try:
        decrypted = self._crypt.decrypt_session_init(msg)
        parsed = util.deserialize(decrypted)
        if not parsed.get('method', '').startswith('session'):
          raise exception.Error('invalid method')
      except exception.Error:
        return None, None
    
    if parsed:
      handler = getattr(self, 'on_%s' % parsed.get('method', ''), self.on_nop)
      return handler, parsed

    return None, None

  def on_pubkey(self, ctx):
    return self._crypt.session_init_pubkey()

  
  def on_session_init(self, ctx, msg):
    """The client sent us its pubkey, send it an encrypted session key."""
    encrypter = this._crypt.temporary_pubkey_encrypter(msg)
    self._session.new(
