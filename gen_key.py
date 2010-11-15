from keyczar import keyczar
from keyczar import keydata
from keyczar import keyinfo
from keyczar import keys
from keyczar import readers

import redis



class KeyValueReader(readers.Reader):
  def __init__(self, location):
    """Location is the name of our keyset"""
    self.location = location
  
  def _Get(self, key):
    raise NotImplemented

  def GetMetadata(self):
    return self._Get('%s/meta' % self.location)
  
  def GetKey(self, id):
    return self._Get('%s/%s' % (self.location, id))


class KeyValueKeyczar(keyczar.GenericKeyczar):
  @classmethod
  def Read(cls, location):
    return cls(cls.reader_factory(location))
  
  def _Set(self, key, value):
    raise NotImplemented

  def Write(self, loc, encrypter=None):
    if encrypter:
      self.metadata.encrypted = True
    self._Set('%s/meta' % loc, str(self.metadata)) # just plain
    for v in self.versions:
      key = str(self.GetKey(v))
      if self.metadata.encrypted:
        key = encrypter.Encrypt(key)  # encrypt key info before outputting
      self._Set('%s/%s' % (loc, str(v.version_number)), key)
  

class KeyValueEncrypter(keyczar.Encrypter):
  reader_factory = None

  @classmethod
  def Read(cls, location):
    return cls(cls.reader_factory(location))


class KeyValueCrypter(keyczar.Crypter):
  reader_factory = None

  @classmethod
  def Read(cls, location):
    return cls(cls.reader_factory(location))


class KeyValueSigner(keyczar.Signer):
  reader_factory = None

  @classmethod
  def Read(cls, location):
    return cls(cls.reader_factory(location))


class RedisReader(KeyValueReader):
  def __init__(self, *args, **kw):
    super(RedisReader, self).__init__(*args, **kw)
    self.r = redis.Redis()

  def _Get(self, key):
    return self.r.get(key)


class RedisKeyczar(KeyValueKeyczar):
  reader_factory = RedisReader

  def __init__(self, *args, **kw):
    super(RedisKeyczar, self).__init__(*args, **kw)
    self.r = redis.Redis()

  def _Set(self, key, value):
    return self.r.set(key, value)


class RedisEncrypter(KeyValueEncrypter):
  reader_factory = RedisReader


class RedisCrypter(KeyValueCrypter):
  reader_factory = RedisReader


class RedisSigner(KeyValueSigner):
  reader_factory = RedisReader



if __name__ == '__main__':
  r = redis.Redis()

  name = 'foo'
  purpose = keyinfo.DECRYPT_AND_ENCRYPT
  #purpose = keyinfo.SIGN_AND_VERIFY

  kmd = keydata.KeyMetadata(name, purpose, keyinfo.AES)
  #kmd = keydata.KeyMetadata(name, purpose, keyinfo.RSA_PRIV)

  # write that to datastore as a keyset
  r.set('%s/meta' % name, str(kmd))
  
  # add key
  reader = RedisReader(name)
  czar = RedisKeyczar(reader)
  czar.AddVersion(keyinfo.PRIMARY, None)
  czar.Write(name, encrypter=None)
