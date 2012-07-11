import micromodels as mm


class UuidField(mm.CharField):
  pass


class AddressField(mm.CharField):
  pass


class User(mm.Model):
  key_name = '%(id)s'

  id = UuidField()
  last_location = UuidField()


class Location(mm.Model):
  id = UuidField()
  address = AddressField()
