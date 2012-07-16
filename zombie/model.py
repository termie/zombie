import micromodels as mm


class UuidField(mm.CharField):
  pass


class AddressField(mm.CharField):
  pass


class User(mm.Model):
  key_name = '%(id)s'

  id = mm.CharField()
  last_location = mm.CharField()


class Location(mm.Model):
  id = mm.CharField()
  address = AddressField()


class Object(mm.Model):
  id = mm.CharField()


class JoinToken(mm.Model):
  """General authorization to enter an area.

  If from_id == location_id then this is probably a reconnect.
  """
  user_id = mm.CharField()
  location_id = mm.CharField()
  from_id = mm.CharField()

