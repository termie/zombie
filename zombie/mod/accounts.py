from zombie import character
from zombie import crypt
from zombie import exception
from zombie import hooks
from zombie import kvs

r = kvs.Storage('accounts_')

def authenticate(ctx, parsed, msg, sig):
  who = parsed.get('self')
  if not who:
    return

  dsa_pub = kvs.get('dsa_pub_' + who)
  if not dsa_pub:
    return

  who_key = crypt.PublicVerifierKey.from_key(who, dsa_pub)
  if not who_key.verify(msg, sig):
    raise exception.Error('sig failed')
  
  ctx.authenticated = True
  ctx.who = who
  ctx.character = character.CharacterObject(ctx, dsa_pub=who_key)

