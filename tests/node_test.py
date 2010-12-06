import unittest

from zombie import node
from zombie import test

class NodeTestCase(test.BaseTestCase):
  def test_Generate_and_Load(self):
    foo = node.Node.Generate('foo', 'foo')
    foo.save()
    foo_loaded = node.Node.Load('foo')
    self.assertEqual(str(foo.rsa_priv), str(foo_loaded.rsa_priv))
    self.assertEqual(str(foo.rsa_pub), str(foo_loaded.rsa_pub))
    self.assertEqual(str(foo.dsa_priv), str(foo_loaded.dsa_priv))
    self.assertEqual(str(foo.dsa_pub), str(foo_loaded.dsa_pub))

  

  # generate a world
  # generate a character
  # load some locations into the world
  # register that character with the world
  # connect that character to the world
  # get the default location
  # join that location
