import uuid
import unittest

from zombie import character
from zombie import kvs
from zombie import world

class BaseTestCase(unittest.TestCase):
  def setUp(self):
    pass


def setup_test_fixtures():
  kvs.global_prefix('test' + uuid.uuid4().hex)
  
  world_id = 'the_world'
  char_id = 'the_char'

  the_world = world.WorldNode.Generate(world_id, world_id)
  the_world.save()

  the_char = character.CharacterNode.Generate(char_id, char_id)
  the_world.sign_node(the_char)
  the_char.save()

  the_char.trust_key(world_id, the_world.dsa_pub)
