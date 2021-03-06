import eventlet
eventlet.monkey_patch()

import time
import logging
import functools

from eventlet import debug
from eventlet import queue

from zombie import client
from zombie import location
from zombie import net
from zombie import npc
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


class EventQueue(object):
  def __init__(self):
    self.queues = {}

  def __getitem__(self, key):
    if key in self.queues:
      return self.queues[key]
    self.queues[key] = queue.LightQueue()
    return self.queues[key]


class TestUser(client.User):
  def __init__(self, *args, **kw):
    super(TestUser, self).__init__(*args, **kw)
    self.events = EventQueue()

  def on_event(self, ctx, topic, data):
    self.events[topic].put(data)


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
                              #'broadcast': 'ipc:///tmp/loc_a_bcast',
                              'address': 'ipc:///tmp/loc_a'},
                    'loc_b': {'id': 'loc_b',
                              #'broadcast': 'ipc:///tmp/loc_b_bcast',
                              'address': 'ipc:///tmp/loc_b'},
                    },
      }


  fixture_loc_a = {
      'id': 'loc_a',
      'address': 'ipc:///tmp/loc_a',
      #'broadcast': 'ipc:///tmp/loc_a_bcast',
      'users': {},
      'exits': {'east': 'loc_b'},
      'objects': {'the rock': 'obj_z'},
      }

  fixture_loc_b = {
      'id': 'loc_b',
      'address': 'ipc:///tmp/loc_b',
      #'broadcast': 'ipc:///tmp/loc_b_bcast',
      'users': {},
      'exits': {'east': 'loc_a'},
      'objects': {'the rock': 'obj_z'},
      }

  fixture_bot_1 = {
      'id': 'bot_1',
      }

  fixture_bot_2 = {
      'id': 'bot_2',
      }

  fixture_obj_z = {
      'id': 'obj_z',
      'description': 'the only rock in the universe',
      }

  def setUp(self):
    super(BasicTestCase, self).setUp()
    self.load_world(self.fixture_world)
    self.load_loc_a(self.fixture_loc_a)
    self.load_loc_b(self.fixture_loc_b)
    self.load_obj_z(self.fixture_obj_z)
    self.load_bot_1(self.fixture_bot_1)
    self.load_bot_2(self.fixture_bot_2)

  def load_world(self, fixture):
    self.world = world.World(
          location_db=world.WorldLocationDatabase(**fixture['locations']),
          user_db=world.WorldUserDatabase(**fixture['users']),
          world_id='foo')

  def load_loc_a(self, fixture):
    self.loc_a = location.Location(
        user_db=location.LocationUserDatabase(**fixture['users']),
        location_id=fixture['id'],
        address=fixture['address'],
        #broadcast=fixture['broadcast'],
        exits=fixture['exits'],
        objects=fixture['objects'])

  def load_loc_b(self, fixture):
    self.loc_b = location.Location(
        user_db=location.LocationUserDatabase(**fixture['users']),
        location_id=fixture['id'],
        address=fixture['address'],
        #broadcast=fixture['broadcast'],
        exits=fixture['exits'],
        objects=fixture['objects'])

  def load_bot_1(self, fixture):
    self.bot_1 = TestUser(**fixture)

  def load_bot_2(self, fixture):
    self.bot_2 = TestUser(**fixture)

  def load_obj_z(self, fixture):
    self.obj_z = npc.ObjectNpc(obj_id=fixture['id'],
                               description=fixture['description'])

  def spawn_world(self):
    world_stream = net.Stream(self.world)
    self.spawn(world_stream.serve, self.fixture_world['address'])
    return world_stream

  def spawn_loc_a(self):
    loc_a_stream = net.Stream(self.loc_a)
    self.spawn(loc_a_stream.serve,
               self.fixture_world['locations']['loc_a']['address'])
    #self.spawn(loc_a_stream.serve_broadcast,
    #           self.fixture_world['locations']['loc_a']['broadcast'])
    self.loc_a._connect_to_world(self.fixture_world['address'])
    return loc_a_stream

  def spawn_loc_b(self):
    loc_b_stream = net.Stream(self.loc_b)
    self.spawn(loc_b_stream.serve,
               self.fixture_world['locations']['loc_b']['address'])
    #self.spawn(loc_b_stream.serve_broadcast,
    #           self.fixture_world['locations']['loc_b']['broadcast'])
    self.loc_b._connect_to_world(self.fixture_world['address'])
    return loc_b_stream

  def spawn_obj_z(self):
    for loc in self.fixture_world['locations'].values():
      cl = client.Client(self.obj_z)
      cl._connect_to_location(loc['address'])
      rv = cl.location.send_cmd('join_as_object')
      rv.next()

  def test_it(self):
    world = self.spawn_world()
    loc_a = self.spawn_loc_a()
    loc_b = self.spawn_loc_b()
    obj_z = self.spawn_obj_z()
    #bot_1 = self.spawn_bot_1()
    #bot_2 = self.spawn_bot_2()

    cl_1 = client.Client(self.bot_1)
    cl_2 = client.Client(self.bot_2)

    # join the game with bot 1
    cl_1._rejoin_game(self.fixture_world['address'])
    self.assert_(self.loc_a.user_db.get(self.bot_1.id))

    joined_event = self.bot_1.events['joined'].get(timeout=2)
    self.assertEquals(joined_event['user_id'], self.bot_1.id)

    # look at loc_a and make sure things line up
    rv = cl_1._look()
    self.assert_(self.loc_b.id in rv['exits'].values())
    self.assert_(self.bot_1.id in rv['users'])

    rv = cl_1._interact('the rock', 'look')
    self.assertEquals(rv['description'], self.obj_z.description)

    # move to a new location
    cl_1._move_location(self.loc_b.id)
    self.assert_(not self.loc_a.user_db.get(self.bot_1.id))
    self.assert_(self.loc_b.user_db.get(self.bot_1.id))

    joined_event = self.bot_1.events['joined'].get(timeout=2)
    self.assertEquals(joined_event['user_id'], self.bot_1.id)


    # check out the new location
    rv = cl_1._look()
    self.assert_(self.loc_a.id in rv['exits'].values())
    self.assert_(self.bot_1.id in rv['users'])
    self.assert_(self.bot_2.id not in rv['users'])

    # bring bot 2 into the game
    cl_2._rejoin_game(self.fixture_world['address'])
    self.assert_(self.loc_b.user_db.get(self.bot_2.id))

    joined_event = self.bot_1.events['joined'].get(timeout=2)
    self.assertEquals(joined_event['user_id'], self.bot_2.id)

    raw_message = 'hello bot_1'
    cl_2._say(raw_message)
    said_event = self.bot_1.events['said'].get(timeout=2)
    self.assertEquals(said_event['user_id'], self.bot_2.id)
    self.assertEquals(said_event['raw_message'], raw_message)

    # look again and verify that bot 2 shows up
    rv = cl_1._look()
    self.assert_(self.bot_2.id in rv['users'])

    # look at bot 2
    rv = cl_1._look_at_other(self.bot_2.id)
    self.assertEquals(rv['description'], self.bot_2.description)

