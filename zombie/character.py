from zombie import crypt
from zombie import hooks
from zombie import objects
from zombie import util


class Character(object):
  def __init__(self, name, rsa_priv=None, rsa_pub=None, dsa_priv=None,
               dsa_pub=None):
    self.name = name
    self.rsa_priv = rsa_priv
    self.rsa_pub = rsa_pub
    self.dsa_priv = dsa_priv
    self.dsa_pub = dsa_pub
  
  @classmethod
  def generate(cls, name):
    rsa_priv = crypt.PrivateCrypterKey.generate(name)
    dsa_priv = crypt.PrivateSignerKey.generate(name)
    return cls.load(name)

  @classmethod
  def load(cls, name):
    rsa_priv = crypt.PrivateCrypterKey.load(name)
    rsa_pub = crypt.PublicEncrypterKey.load(name)
    dsa_priv = crypt.PrivateSignerKey.load(name)
    dsa_pub = crypt.PublicVerifierKey.load(name)
  
    return cls(name=name, rsa_priv=rsa_priv, rsa_pub=rsa_pub,
               dsa_priv=dsa_priv, dsa_pub=dsa_pub)

  def init(self):
    init_hooks = self._get_init_hooks()
    for f in init_hooks:
      f()

  def _get_init_hooks(self):
    return [self._init_hooks,
            self._init_spawn,
            #self._init_inventory,
            #self._init_contacts,
            #self._init_triggers,
            #self._init_aliases,
            #self._init_externals,
            ]

  def _init_hooks(self):
    pass

  def _init_spawn(self):
    hooks.add('session_start', self.spawn)

  def handle(self, client, message):
    hooks.run('message', client, message)

  def spawn(self, client):
    client.send({'method': 'spawn'})

  def to_dict(self):
    return {'name': self.name,
            'dsa_pub': str(self.dsa_pub),
            'rsa_pub': str(self.rsa_pub)}

  def __str__(self):
    return util.serialize(self.to_dict())

class CharacterObject(objects.ActiveObject):
  def __init__(self, ctx, dsa_pub):
    pass

  def located(self, location):
    # on the new located event the following should occur:
    # - acquire location session key
    # - subscribe to location's PUB feed
    ctx.event('located', str(location))
