import logging
import os
import uuid
import unittest
import sys

import eventlet
import gflags
from nose import config
from nose import result
from nose import core
from nose.plugins import skip

#from zombie import kvs
from zombie import shared
#from zombie import world


FLAGS = gflags.FLAGS
gflags.DEFINE_boolean('fast_tests', True,
                      'only create new keys if they do not exist')
gflags.DEFINE_boolean('pdb', False,
                      'drop into pdb on errors (nose flag)')
gflags.DEFINE_boolean('logcapture', True,
                      'capture logs (nose flag)')
gflags.DEFINE_integer('spawn_timeout', 1,
                      'how long to allow spawned greenthreads')


LOG = logging.getLogger(__name__)


class TestCase(unittest.TestCase):
  def setUp(self):
    self.monkey_patch_spawn()
    self._spawned = []

  def monkey_patch_spawn(self):
    self._real_spawn = shared.pool.spawn
    shared.pool.spawn = self.spawn

  def spawn(self, *args, **kw):
    spawned = self._real_spawn(eventlet.with_timeout,
                               FLAGS.spawn_timeout,
                               *args, **kw)
    LOG.debug('SPAWN %s', args[0])
    self._spawned.append(spawned)
    return spawned

  def tearDown(self):
    shared.pool.spawn = self._real_spawn
    for spawned in self._spawned:
      spawned.kill()


def skip_if_fast(f):
  def _wrapped(*args, **kw):
    if FLAGS.fast_tests:
      raise skip.SkipTest()
    return f(*args, **kw)
  _wrapped.func_name = f.func_name
  return _wrapped


def old_fixtures_stuff():
  return
  db_prefix = 'test' + uuid.uuid4().hex
  world_id = 'the_world'
  char_id = 'the_char'

  # A bit of a hack to copy existing keys around
  if FLAGS.fast_tests:
    FLAGS.kvs_prefix = 'test' + 'fast_tests'
    try:
      the_world = world.WorldNode.Load(world_id)
      the_char = world.WorldNode.Load(char_id)

      FLAGS.kvs_prefix = db_prefix
      the_char.trust_key(world_id, the_world.dsa_pub)
      the_world.trust_key(world_id, the_world.dsa_pub)
      the_world.save()
      the_char.save()
      return
    except Exception:
      pass

  FLAGS.kvs_prefix = db_prefix
  the_world = world.WorldNode.Generate(world_id, world_id)
  the_char = character.CharacterNode.Generate(char_id, char_id)
  the_world.save()

  the_world.sign_node(the_char)
  the_char.trust_key(world_id, the_world.dsa_pub)
  the_world.trust_key(world_id, the_world.dsa_pub)
  the_char.save()
  the_char.save()

  FLAGS.kvs_prefix = 'test' + 'fast_tests'
  the_char.trust_key(world_id, the_world.dsa_pub)
  the_world.trust_key(world_id, the_world.dsa_pub)
  the_world.save()
  the_char.save()
  FLAGS.kvs_prefix = db_prefix


class TestResult(result.TextTestResult):
    def __init__(self, *args, **kw):
        result.TextTestResult.__init__(self, *args, **kw)
        self._last_case = None

    def getDescription(self, test):
        return str(test)

    def startTest(self, test):
        unittest.TestResult.startTest(self, test)
        current_case = test.test.__class__.__name__

        if self.showAll:
            if current_case != self._last_case:
                self.stream.writeln(current_case)
                self._last_case = current_case

            self.stream.write(
                '    %s' % str(test.test._testMethodName).ljust(60))
            self.stream.flush()


class TestRunner(core.TextTestRunner):
    def _makeResult(self):
        return TestResult(self.stream,
                              self.descriptions,
                              self.verbosity,
                              self.config)


def main():
    argv = FLAGS(sys.argv)
    if FLAGS.pdb:
      argv.insert(1, '--pdb')
    if not FLAGS.logcapture:
      argv.insert(1, '--nologcapture')
    argv.insert(1, '--where=tests')
    c = config.Config(stream=sys.stdout,
                      env=os.environ,
                      verbosity=2,
                      plugins=core.DefaultPluginManager())

    runner = TestRunner(stream=c.stream,
                        verbosity=c.verbosity,
                        config=c)

    sys.exit(not core.run(config=c, testRunner=runner, argv=argv))
