import atexit
import readline

from zombie import character
from zombie import net
from zombie import shared

class TextUi(object):
  def __init__(self, character, address):
    self.character = character
    self.address = address

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
    
    self.client = net.Client(self.character)
    self.client.connect(self.address)

    shared.pool.spawn_n(self.client.clientloop)

    while True:
      data = raw_input()
      self.handle_input(data)

  def handle_input(self, data):
    cmd, sep, rest = data.partition(' ')
    self.client.send({'method': cmd, 'args': rest})
