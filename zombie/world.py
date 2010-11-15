from zombie import crypt


class World(object):
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


