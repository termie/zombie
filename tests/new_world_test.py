import time
import logging
import functools

from eventlet import debug

from zombie import client
from zombie import location
from zombie import net
from zombie import shared
from zombie import test
from zombie import world


location_db = {'default': 'inproc://default_location'}
user_db = {'asd': 'asda'}

default_location = {'id': 'default',
                    'address': 'inproc://default_location',
                    'description': 'default location'}

WORLD_ADDR = 'inproc://world'


class TestHandler(object):
  pass


class EchoHandler(object):
  def cmd_echo_and_die(self, context, message):
    context.reply({'message': message})
    context['stream'].close()

  def cmd_echo_three_and_die(self, context, message):
    context.reply({'message': message}, False)
    context.reply({'message': message}, False)
    context.reply({'message': message}, False)
    context.end_reply()
    context['stream'].close()


class BaseTestCase(test.TestCase):
  def _get_server(self):
    return net.Stream(EchoHandler())

  def _get_client(self):
    return net.Stream(TestHandler())

  def call(self, cb):
    callback_called = [False]
    s = self._get_server()
    c = self._get_client()

    @functools.wraps(cb)
    def _cb(*args, **kw):
      callback_called[0] = True
      rv = cb(*args, **kw)
      s.close()
      c.close()
      return rv

    self.spawn(s.serve, WORLD_ADDR)
    self.spawn(c.connect, WORLD_ADDR, _cb)
    shared.pool.waitall()
    self.assert_(callback_called)


#class WorldTestCase(BaseTestCase):
#  def _get_server(self):
#    return net.Stream(world.World(location_db=location_db,
#                                            user_db=user_db))

#  def test_world_default_location(self):
#    def cb(context):
#      r = context.send_cmd('default_location')
#      for result in r:
#        self.assertEqual(result['default'], location_db['default'])

#    self.call(cb)

#  def test_world_lookup_location(self):
#    def cb(context):
#      r = context.send_cmd('lookup_location', {'location_id': 'default'})
#      for result in r:
#        self.assertEqual(result['default'], location_db['default'])

#    self.call(cb)


#class StreamTestCase(test.TestCase):
#  def test_serve(self):
#    callback_called = [False]

#    s = net.Stream(EchoHandler())
#    self.spawn(s.serve, WORLD_ADDR)

#    def cb(context):
#      callback_called[0] = True
#      r = context.send_cmd('echo_and_die', {'message': 'foo'})
#      for result in r:
#        self.assertEqual(result['data']['message'], 'foo')
#      context['stream'].close()

#    c = net.Stream(TestHandler())
#    self.spawn(c.connect, WORLD_ADDR, cb)
#    shared.pool.waitall()
#    self.assert_(callback_called[0])

#  def test_multiple_responses(self):
#    callback_called = [False]

#    s = net.Stream(EchoHandler())
#    self.spawn(s.serve, WORLD_ADDR)

#    def cb(context):
#      callback_called[0] = True
#      r = context.send_cmd('echo_three_and_die', {'message': 'foo'})
#      i = 0
#      for result in r:
#        self.assertEqual(result['message'], 'foo')
#        i += 1
#      self.assertEqual(i, 3)
#      context['stream'].close()

#    c = net.Stream(TestHandler())
#    self.spawn(c.connect, WORLD_ADDR, cb)
#    shared.pool.waitall()
#    self.assert_(callback_called[0])


class BasicTestCase(test.TestCase):
  fixture_world = {
      'address': 'ipc:///tmp/world',
      'users': {'bot_1': {'id': 'bot_1',
                          'last_location': 'loc_a'},
                'bot_2': {'id': 'bot_2',
                          'last_location': 'loc_b'},
                },
      'locations': {'loc_a': {'id': 'loc_a',
                              'address': 'ipc:///tmp/loc_a'},
                    'loc_b': {'id': 'loc_b',
                              'address': 'ipc:///tmp/loc_b'},
                    },
      }


  fixture_loc_a = {
      'users': {},
      }

  fixture_loc_b = {
      'users': {},
      }

  fixture_bot_1 = {
      'id': 'bot_1',
      }

  fixture_bot_2 = {
      'id': 'bot_2',
      }

  def setUp(self):
    super(BasicTestCase, self).setUp()
    self.load_world(self.fixture_world)
    self.load_loc_a(self.fixture_loc_a)
    self.load_loc_b(self.fixture_loc_b)
    self.load_bot_1(self.fixture_bot_1)
    self.load_bot_2(self.fixture_bot_2)

  def load_world(self, fixture):
    self.world = world.World(
          location_db=world.WorldLocationDatabase(**fixture['locations']),
          user_db=world.WorldUserDatabase(**fixture['users']))

  def load_loc_a(self, fixture):
    self.loc_a = location.Location(
        user_db=location.LocationUserDatabase(**fixture['users']),
        location_id='loc_a')

  def load_loc_b(self, fixture):
    self.loc_b = location.Location(
        user_db=location.LocationUserDatabase(**fixture['users']),
        location_id='loc_b')

  def load_bot_1(self, fixture):
    self.bot_1 = client.User(**fixture)

  def load_bot_2(self, fixture):
    self.bot_2 = client.User(**fixture)

  def spawn_world(self):
    world_stream = net.Stream(self.world)
    self.spawn(world_stream.serve, self.fixture_world['address'])
    return world_stream

  def spawn_loc_a(self):
    loc_a_stream = net.Stream(self.loc_a)
    self.spawn(loc_a_stream.serve,
               self.fixture_world['locations']['loc_a']['address'])
    self.loc_a._connect_to_world(self.fixture_world['address'])
    return loc_a_stream

  def spawn_loc_b(self):
    loc_b_stream = net.Stream(self.loc_b)
    self.spawn(loc_b_stream.serve,
               self.fixture_world['locations']['loc_b']['address'])
    self.loc_b._connect_to_world(self.fixture_world['address'])
    return loc_b_stream

  def test_it(self):
    debug.hub_blocking_detection(True, 0.5)
    world = self.spawn_world()
    loc_a = self.spawn_loc_a()
    loc_b = self.spawn_loc_b()
    #bot_1 = self.spawn_bot_1()
    #bot_2 = self.spawn_bot_2()

    cl_1 = client.Client(self.bot_1)
    cl_2 = client.Client(self.bot_2)

    #self.spawn(cl_1._rejoin_game, self.fixture_world['address'])
    cl_1._rejoin_game(self.fixture_world['address'])
    self.assert_(self.loc_a.user_db.get(self.bot_1.id))
    cl_1._move_location('loc_b')
    self.assert_(not self.loc_a.user_db.get(self.bot_1.id))
    self.assert_(self.loc_b.user_db.get(self.bot_1.id))

    cl_2._rejoin_game(self.fixture_world['address'])
    self.assert_(self.loc_b.user_db.get(self.bot_2.id))

    cl_1._look_at_other(self.bot_2.id)
