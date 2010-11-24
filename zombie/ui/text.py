import atexit
import pprint
import readline

import eventlet

from zombie import character
from zombie import log as logging
from zombie import net
from zombie import shared
from zombie.ui import base

class Output(object):
  def write(self, text):
    print text

class TextUi(base.Ui):
  def __init__(self, character, waddress):
    super(TextUi, self).__init__(character, waddress)
    self.main = Output()

  def init(self):
    super(TextUi, self).init()
    self._setup_readline()

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
    super(TextUi, self)._init_cmds()
    self._cmds['whoami'] = self._cmd_whoami
    self._cmds['look'] = self._cmd_look

  def input_loop(self):
      while True:
        data = raw_input()
        rv = self.handle_input(data)
        result = rv.wait()
        #if result:
        #  self.main.write(pprint.pformat(result))
        eventlet.sleep(0.1)

  def _cmd_whoami(self, cmd, args):
    self.main.write(pprint.pformat(self.character.to_dict()))

  def _cmd_join(self, cmd, args):
    super(TextUi, self)._cmd_join(cmd, args)
    self._cmd_look('look', '')

  def _cmd_look(self, cmd, args):
    rv = self.lclient.rpc(cmd, args=args)
    self.main.write(pprint.pformat(rv))
    #if 'name' in rv:
    #  self.main.write(rv['name'])
    #if 'description' in rv:
    #  self.main.write(rv['description'])
    return rv
