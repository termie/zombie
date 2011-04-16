import os

from keyczar import keyczar
from keyczar import keyczart
from keyczar import keydata
from keyczar import keyinfo
from keyczar import keys
from keyczar import readers
from keyczar import util as keyczar_util

from zombie import exception
from zombie import kvs
from zombie import util



def monkey_patch_keyczar_file_functions():
  keyczar_util.WriteFile = WriteFile
  keyczar_util.ReadFile = ReadFile

r = kvs.Storage('keyczar|')

def WriteFile(data, loc):
  print 'kvs >', loc
  r.set(loc, data)

def ReadFile(loc):
  print 'kvs <', loc
  rv = r.get(loc)
  if rv is None:
    raise Exception()
  return rv

monkey_patch_keyczar_file_functions()


class Key(object):
  prefix = ''
  purpose = None
  asymmetric = None
  factory = None
  kind = None

  def __init__(self, name, czar):
    self.name = name
    self.czar = czar

  @classmethod
  def load(cls, name):
    czar = cls.factory.Read(cls.prefix + name)
    return cls(name, czar)

  @classmethod
  def generate(cls, name):
    kmd = keydata.KeyMetadata(name, cls.purpose, cls.kind)
    keyczar_util.WriteFile(str(kmd), cls.prefix + name + '/meta')
    keyczart.AddKey(cls.prefix + name, keyinfo.PRIMARY)

    # if we're asymmetric make a public key also
    if cls.asymmetric:
      keyczart.PubKey(cls.prefix + name, cls.prefix + 'public_' + name)

    return cls.load(name)

  @classmethod
  def from_key(cls, name, key_string):
    reader = StringReader(name, key_string, purpose=cls.purpose, kind=cls.kind)
    return cls(name, cls.factory(reader))

  def save(self):
    reader = StringReader(
        self.name, str(self), purpose=self.purpose, kind=self.kind)
    genczar = keyczar.GenericKeyczar(reader)
    genczar.Write(self.prefix + self.name)
    return self.__class__.load(self.name)

  def sign(self, s):
    return self.czar.Sign(s)

  def verify(self, data, ciphertext):
    return self.czar.Verify(data, ciphertext)

  def encrypt(self, s):
    return self.czar.Encrypt(s)

  def decrypt(self, ciphertext):
    return self.czar.Decrypt(ciphertext)

  def __str__(self):
    return str(self.czar.primary_key)


class SessionKey(Key):
  prefix = 'keys/session_'
  purpose = keyinfo.DECRYPT_AND_ENCRYPT
  asymmetric = None
  factory = keyczar.Crypter
  kind = keyinfo.AES


class PrivateCrypterKey(Key):
  prefix = 'keys/crypter_'
  purpose = keyinfo.DECRYPT_AND_ENCRYPT
  asymmetric = True
  factory = keyczar.Crypter
  kind = keyinfo.RSA_PRIV


class PrivateSignerKey(Key):
  prefix = 'keys/signer_'
  purpose = keyinfo.SIGN_AND_VERIFY
  asymmetric = True
  factory = keyczar.Signer
  kind = keyinfo.DSA_PRIV


class PublicEncrypterKey(Key):
  prefix = 'keys/crypter_public_'
  purpose = keyinfo.ENCRYPT
  asymmetric = True
  factory = keyczar.Encrypter
  kind = keyinfo.RSA_PUB


class PublicVerifierKey(Key):
  prefix = 'keys/signer_public_'
  purpose = keyinfo.VERIFY
  asymmetric = True
  factory = keyczar.Verifier
  kind = keyinfo.DSA_PUB


class StringReader(readers.Reader):
  def __init__(self, name, key_string, purpose, kind):
    self.key_string = key_string
    self.kmd = keydata.KeyMetadata(name, purpose, kind)
    version = keydata.KeyVersion(1, keyinfo.PRIMARY, False)
    self.kmd.AddVersion(version)

  def GetMetadata(self):
    return str(self.kmd)

  def GetKey(self, version_number):
    kmd = keydata.KeyMetadata.Read(self.GetMetadata())
    keys.ReadKey(kmd.type, self.key_string)
    return self.key_string


class Manager(object):
  signing_keyname = 'session_init'

  def signing_pubkey(self):
    try:
      pubkey = PublicVerifierKey.load(self.signing_keyname)
    except:
      privkey = PrivateSignerKey.generate(self.signing_keyname)
      pubkey = PublicVerifierKey.load(self.signing_keyname)
    return pubkey

  def temporary_pubkey_encrypter(self, pubkey):
    return PublicEncrypterKey.from_key('tmp', pubkey)

  def get_session_key(self, ident):
    ident_b64 = util.b64_encode(ident)
    try:
      return SessionKey.load(ident_b64)
    except Exception:
      pass
    return

  def generate_session_key(self, ident):
    ident_b64 = util.b64_encode(ident)
    return SessionKey.generate(ident_b64)

