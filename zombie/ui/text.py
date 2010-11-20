import atexit
import pprint
import readline

import eventlet

from zombie import character
from zombie import log as logging
from zombie import net
from zombie import shared

class TextUi(object):
  def __init__(self, character, address):
    self.character = character
    self.wclient = None
    self.lclient = None
    self.waddress = address
    self._cmds = {}

  def _setup_readline(self):
    try:
      readline.read_init_file('.readlinerc')
    except IOError:
      pass

    try:
      readline.read_history_file('.zombiehist')
    except IOError:
      pass

    atexit.register(readline.write_history_file, '.zombiehist')

  def _init_cmds(self):
    self._cmds['whoami'] = self._cmd_whoami
    self._cmds['join'] = self._cmd_join

  def _cmd_whoami(self, cmd, args):
    pprint.pprint(self.character.to_dict())

  def _cmd_join(self, cmd, args):
    if self.lclient:
      self.lclient.rpc('leave')
      self.lclient.close()
      self.lclient = None

    self.lclient = net.Client(self.character)
    self.lclient.connect_control(args)
    self.lclient.connect_pubsub()

    shared.pool.spawn_n(self.lclient.control_loop)
    shared.pool.spawn_n(self.lclient.pubsub_loop)

  def _cmd_nop(self):
    return None

  def run(self):
    self._setup_readline()
    self._init_cmds()
    
    self.wclient = net.Client(self.character)
    self.wclient.connect_control(self.waddress)
    self.wclient.connect_pubsub()

    shared.pool.spawn_n(self.wclient.control_loop)
    shared.pool.spawn_n(self.wclient.pubsub_loop)
    shared.pool.spawn(self.input_loop)

  def input_loop(self):
      while True:
        data = raw_input()
        rv = self.handle_input(data)
        result = rv.wait()
        if result:
          pprint.pprint(result)
        eventlet.sleep(0.1)

  def handle_input(self, data):
    cmd, sep, rest = data.partition(' ')
    if not cmd.strip():
      return shared.pool.spawn(self._cmd_nop)
    if cmd in self._cmds:
      return shared.pool.spawn(self._cmds[cmd], cmd, rest)
    if self.lclient:
      return shared.pool.spawn(self.lclient.rpc, cmd, args=rest)
    else:
      return shared.pool.spawn(self.wclient.rpc, cmd, args=rest)
