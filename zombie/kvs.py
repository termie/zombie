import redis


class Storage(object):
  def __init__(self, prefix=''):
    self.r = redis.Redis()
    self.prefix = prefix

  def set(self, key, value):
    self.r.set(PREFIX + self.prefix + key, value)

  def get(self, key):
    return self.r.get(PREFIX + self.prefix + key)


default = Storage()


PREFIX = ''


def global_prefix(prefix):
  global PREFIX
  PREFIX = prefix


def get(key):
  return default.get(key)


def set(key, value):
  return default.set(key, value)
