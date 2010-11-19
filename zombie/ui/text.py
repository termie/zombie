import atexit
import readline

from zombie import character
from zombie import net
from zombie import shared

class TextUi(object):
  def __init__(self, character, address):
    self.character = character
    self.wclient = None
    self.lclient = None
    self.waddress = address

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

  def run(self):
    self._setup_readline()
    
    self.wclient = net.Client(self.character)
    self.wclient.connect(self.waddress)
    self.wclient.subscribe()

    shared.pool.spawn_n(self.wclient.clientloop)

    while True:
      data = raw_input()
      self.handle_input(data)

  def handle_input(self, data):
    cmd, sep, rest = data.partition(' ')
    if self.lclient:
      self.lclient.rpc({'method': cmd, 'args': rest})
    else:
      self.wclient.rpc({'method': cmd, 'args': rest})
