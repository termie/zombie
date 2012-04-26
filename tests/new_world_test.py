#from zombie import character
#from zombie import net
from zombie import shared
from zombie import test
#from zombie import world
from zombie import new_world
import time
import logging


location_db = {'default': 'inproc://default_location'}

default_location = {'id': 'default',
                    'address': 'inproc://default_location',
                    'description': 'default location'}

WORLD_ADDR = 'inproc://world'


class TestHandler(object):
  def cmd_connection_started(self, context):
    print 'connecty'
    context.send('default_location')
    #raise StopIteration()

class EchoHandler(object):
  def cmd_echo_and_die(self, context, message):
    context.reply({'message': message})
    context.end_reply()
    context['stream'].sock.close()



class WorldTestCase(test.TestCase):
  #def test_world_serve(self):
  #  w = new_world.World(location_db=location_db)
  #  k = self.spawn(new_world.serve, WORLD_ADDR, w)
  #  c = TestHandler()
  #  self.spawn(new_world.connect, WORLD_ADDR, c)
  #  shared.pool.waitall()
  pass

class StreamTestCase(test.TestCase):
  def test_serve(self):
    s = new_world.Stream(EchoHandler())
    self.spawn(s.serve, WORLD_ADDR)

    def cb(context):
      r = context.send_cmd('echo_and_die', {'message': 'foo'})
      print "asdasd"
      for result in r:
        print "LALLSDLAS"
        print result
      context['stream'].sock.close()


    c = new_world.Stream(TestHandler())
    self.spawn(c.connect, WORLD_ADDR, cb)

    shared.pool.waitall()
