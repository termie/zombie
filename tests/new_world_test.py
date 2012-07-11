#from zombie import character
#from zombie import net
from zombie import shared
from zombie import test
#from zombie import world
from zombie import new_world
import time
import logging
import functools


location_db = {'default': 'inproc://default_location'}

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
    return new_world.Stream(EchoHandler())

  def _get_client(self):
    return new_world.Stream(TestHandler())

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


class WorldTestCase(BaseTestCase):
  def _get_server(self):
    return new_world.Stream(new_world.World(location_db=location_db))

  def test_world_default_location(self):
    def cb(context):
      r = context.send_cmd('default_location')
      for result in r:
        self.assertEqual(result['data']['default'], location_db['default'])

    self.call(cb)

  def test_world_lookup_location(self):
    def cb(context):
      r = context.send_cmd('lookup_location', {'location_id': 'default'})
      for result in r:
        self.assertEqual(result['data']['default'], location_db['default'])

    self.call(cb)


class LocationTestCase(BaseTestCase):
  def test_basic(self):
    # User connects to world
    # User is unknown so gets default location
    # User connects to default location
    # User joins the default location
    # User looks and sees the location
    # User disconnects
    # User reconnects to world is known so gets last location as default
    # User connects to a different location
    # User attempts to join the different location
    # New location rejects join
    # User connects to the default location
    # User joins the default location
    pass


class StreamTestCase(test.TestCase):
  def test_serve(self):
    callback_called = [False]

    s = new_world.Stream(EchoHandler())
    self.spawn(s.serve, WORLD_ADDR)

    def cb(context):
      callback_called[0] = True
      r = context.send_cmd('echo_and_die', {'message': 'foo'})
      for result in r:
        self.assertEqual(result['data']['message'], 'foo')
      context['stream'].close()

    c = new_world.Stream(TestHandler())
    self.spawn(c.connect, WORLD_ADDR, cb)
    shared.pool.waitall()
    self.assert_(callback_called[0])

  def test_multiple_responses(self):
    callback_called = [False]

    s = new_world.Stream(EchoHandler())
    self.spawn(s.serve, WORLD_ADDR)

    def cb(context):
      callback_called[0] = True
      r = context.send_cmd('echo_three_and_die', {'message': 'foo'})
      i = 0
      for result in r:
        self.assertEqual(result['data']['message'], 'foo')
        i += 1
      self.assertEqual(i, 3)
      context['stream'].close()

    c = new_world.Stream(TestHandler())
    self.spawn(c.connect, WORLD_ADDR, cb)
    shared.pool.waitall()
    self.assert_(callback_called[0])
