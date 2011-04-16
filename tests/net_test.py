from zombie import character
from zombie import net
from zombie import shared
from zombie import test
from zombie import world


class NetTestCase(test.TestCase):
  def test_basic(self):
    world_address = 'inproc://foo'
    world_id = 'the_world'
    char_id = 'the_char'
    the_world = world.WorldNode.Load('the_world')
    the_char = character.CharacterNode.Load('the_char')

    server = net.NodeServer(the_world)
    server.init_control(world_address)
    wloop = self.spawn(server.control_loop)

    client = net.NodeClient(the_char)
    client.connect_control(world_address, world_id)
    wloop.wait()
