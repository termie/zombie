import unittest

from zombie import character
from zombie import net
from zombie import test
from zombie import world

class NetTestCase(unittest.TestCase):
  def test_basic(self):
    world_address = 'inproc://foo'
    world_id = 'foo'
    char_id = 'bar'
    the_world = world.WorldNode.Load('the_world')
    the_char = character.CharacterNode.Load('the_char')

    server = net.NodeServer(the_world)
