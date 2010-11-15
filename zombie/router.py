from zombie import crypt
from zombie import exception
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
    self._crypt = crypt.Manager()

  def route(self, ctx, msg):
    print ctx, msg
    handler, parsed = self._get_handler(ctx, msg)
    if handler:
      rv = handler(ctx, parsed)
      if rv:
        ctx.reply(rv)
  
  def _get_handler(self, ctx, msg):
    # special case to request pubkey, everything else will be encrypted
    if msg == 'dsa_pub':
      return self.on_dsa_pub, msg

    # if we have a session first try to decrypt the message using that key
    session_key = self._crypt.get_session_key(ctx.ident)
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
        parsed = util.deserialize(msg)
        if not parsed.get('method', '').startswith('session'):
          raise exception.Error('invalid method')
      except exception.Error:
        return None, None
    
    if parsed:
      handler = getattr(self, 'on_%s' % parsed.get('method', ''), self.on_nop)
      return handler, parsed

    return None, None

  def on_dsa_pub(self, ctx, msg):
    return str(self._crypt.signing_pubkey())

  def on_nop(self, ctx, msg):
    return

  def on_session_start(self, ctx, msg):
    """The client sent us its pubkey, send it an encrypted session key."""
    encrypter = self._crypt.temporary_pubkey_encrypter(msg.get('rsa_pub'))
    session_key = self._crypt.generate_session_key(ctx.ident)
    msg = util.serialize({'session_key': str(session_key)})
    return encrypter.encrypt(msg)

  @session_required
  def on_echo(self, ctx, msg):
    return ctx.session_key.encrypt(util.serialize(msg))
