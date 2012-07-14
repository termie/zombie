class Kvs(dict):
  deserialize = staticmethod(lambda x: x)

  def set(self, key, value):
    try:
      value = value.to_dict()
    except AttributeError:
      pass
    self.__setitem__(key, value)

  def get(self, key, default=None):
    rv = super(Kvs, self).get(key, default)
    return self.deserialize(rv)

  def delete(self, key):
    self.__delitem__(key)


