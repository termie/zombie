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
    self._cmds['whoami'] = self._whoami
    self._cmds['join'] = self._join

  def _whoami(self, cmd, args):
    pprint.pprint(self.character.to_dict())

  def _join(self, cmd, args):
    if self.lclient:
      self.lclient.rpc('leave')
      self.lclient.close()
      self.lclient = None

    self.lclient = net.Client(self.character)
    self.lclient.connect(args)
    self.lclient.subscribe()

    shared.pool.spawn_n(self.lclient.controlloop)
    shared.pool.spawn_n(self.lclient.subscribeloop)
    logging.debug('after join bits')


  def run(self):
    self._setup_readline()
    self._init_cmds()
    
    self.wclient = net.Client(self.character)
    self.wclient.connect(self.waddress)
    self.wclient.subscribe()

    shared.pool.spawn_n(self.wclient.controlloop)


    shared.pool.spawn_n(self.wclient.subscribeloop)
    
    def _input():
      while True:
        print 'raw?'
        data = raw_input()
        rv = self.handle_input(data)
        #shared.pool.spawn(lambda: pprint.pprint(rv.wait()))
        pprint.pprint(rv.wait())
        eventlet.sleep(0.1)

    return shared.pool.spawn(_input)

  def handle_input(self, data):
    cmd, sep, rest = data.partition(' ')
    if not cmd.strip():
      return
    if cmd in self._cmds:
      return shared.pool.spawn(self._cmds[cmd], cmd, rest)
    if self.lclient:
      return shared.pool.spawn(self.lclient.rpc, cmd, args=rest)
    else:
      return shared.pool.spawn(self.wclient.rpc, cmd, args=rest)
