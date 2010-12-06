from zombie import character
from zombie import crypt
from zombie import exception
from zombie import hooks
from zombie import kvs
from zombie import log as logging
from zombie import util

r = kvs.Storage('accounts_')

def auth_required(f):
  def _wrapped(ctx, parsed):
    if not ctx.get('authenticated'):
      return
    return f(ctx, parsed)
  _wrapped.func_name = f.func_name
  return _wrapped

def verify_key_for(who):
  verify_key = crypt.PublicVerifierKey.load('dsa_pub_' + who)
  return verify_key


def authenticate(ctx, parsed, msg, sig):
  who = parsed.get('self')
  if not who:
    raise exception.Error('no who')

  who_key = crypt.PublicVerifierKey.load('dsa_pub_' + who)
  if not who_key.verify(msg, sig):
    raise exception.Error('sig failed')
  
  logging.debug('authenticated')
  ctx['authenticated'] = True
  ctx['who'] = who
  ctx['character'] = character.CharacterObject(ctx, dsa_pub=who_key)


def register(ctx, parsed):
  who = parsed.get('self')
  if not who:
    return

  existing_dsa_pub = kvs.get('dsa_pub_' + who)
  if existing_dsa_pub:
    raise exception.Error('already registered')
  
  dsa_pub = parsed.get('args')
  dsa_pub_key = crypt.PublicVerifierKey.from_key('dsa_pub_' + who, dsa_pub)
  dsa_pub_key.save()
  ctx.reply(parsed, response='ok')
