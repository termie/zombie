import redis


class Storage(object):
  def __init__(self, prefix=''):
    self.r = redis.Redis()
    self.prefix = prefix

  def set(self, key, value):
    self.r.set(prefix + key, value)

  def get(self, key):
    return self.r.get(prefix + key, value)


default = Storage()


def get(key):
  return default.get(key)


def set(key, value)
  return default.set(key, value)
