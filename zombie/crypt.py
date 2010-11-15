from keyczar import keyczar
from keyczar import keyczart
from keyczar import keydata
from keyczar import keyinfo
from keyczar import keys
from keyczar import readers
from keyczar import util as keyczar_util

import redis

from zombie import exception
from zombie import util

import os

  
def monkey_patch_keyczar_file_functions():
  keyczar_util.WriteFile = WriteFile
  keyczar_util.ReadFile = ReadFile

r = redis.Redis()

def WriteFile(data, loc):
  r.set(loc, data)

def ReadFile(loc):
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

  def __init__(self, name, czar):
    self.name = name
    self.czar = czar

  @classmethod
  def load(cls, name):
    czar = cls.factory.Read(cls.prefix + name)
    return cls(name, czar)

  @classmethod
  def generate(cls, name):
    keyczart.Create(cls.prefix + name, name, cls.purpose, cls.asymmetric)
    keyczart.AddKey(cls.prefix + name, keyinfo.PRIMARY)
    
    # if we're asymmetric make a public key also
    if cls.asymmetric:
      keyczart.PubKey(cls.prefix + name, cls.prefix + 'public_' + name)

    return cls.load(name)

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


class PrivateCrypterKey(Key):
  prefix = 'keys/crypter_'
  purpose = keyinfo.DECRYPT_AND_ENCRYPT
  asymmetric = True
  factory = keyczar.Crypter


class PrivateSignerKey(Key):
  prefix = 'keys/signer_'
  purpose = keyinfo.SIGN_AND_VERIFY
  asymmetric = True
  factory = keyczar.Signer


class PublicKey(Key):
  @classmethod
  def from_key(cls, name, key_string):
    reader = StringReader(name, key_string, purpose=cls.purpose)
    genczar = keyczar.GenericKeyczar(reader)
    genczar.Write(cls.prefix + name)
    return cls.load(name)
    

class PublicEncrypterKey(PublicKey):
  prefix = 'keys/crypter_public_'
  purpose = keyinfo.ENCRYPT
  asymmetric = True
  factory = keyczar.Encrypter


class PublicVerifierKey(PublicKey):
  prefix = 'keys/signer_public_'
  purpose = keyinfo.VERIFY
  asymmetric = True
  factory = keyczar.Verifier


class StringReader(readers.Reader):
  def __init__(self, name, key_string, purpose):
    if purpose == keyinfo.ENCRYPT:
      type_ = keyinfo.RSA_PUB
    else:
      type_ = keyinfo.DSA_PUB

    self.key_string = key_string
    self.kmd = keydata.KeyMetadata(name, purpose, type_)
    version = keydata.KeyVersion(1, keyinfo.PRIMARY, False)
    self.kmd.AddVersion(version)

  def GetMetadata(self):
    return str(self.kmd)

  def GetKey(self, version_number):
    return self.key_string


class TemporaryPublicEncrypterKey(PublicEncrypterKey):
  prefix = 'tmp/'

  def __init__(self, key_string):
    name = 'tmp'
    reader = StringReader(name, key_string, purpose=self.purpose)
    czar = keyczar.Encrypter(reader)
    super(TemporaryPublicEncrypterKey, self).__init__(name, czar)




class Manager(object):
  session_init_keyname = 'session_init'

  def decrypt_session_init(self, msg):
    pass

  def session_init_pubkey(self):
    try:
      pubkey = PublicEncrypterKey.load(self.session_init_keyname)
    except:
      privkey = PrivateCrypterKey.generate(self.session_init_keyname)
      pubkey = PublicEncrypterKey.load(self.session_init_keyname)
    return pubkey

  def temporary_pubkey_encrypter(self, pubkey):
    pass

  def lookup_session_key(self, ident):
    ident_b64 = util.b64_encode(ident)
    try:
      return SessionKey.load(ident_b64)
    except exception.Error:
      pass
    return
