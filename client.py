import eventlet
eventlet.monkey_patch()

from zombie import character
from zombie import net
from zombie import shared
from zombie import util
from zombie.ui import text
from zombie.ui import websocket


if __name__ == '__main__':
  bind = 'ipc:///tmp/foo'
  
  termie = character.Character.load('termie')
  termie.init()

  #ui = websocket.WebSocketUi(termie, bind)
  ui = text.TextUi(termie, bind)
  ui.init()
  
  ui.handle_input('connect %s' % bind).wait()
  rv = ui.handle_input('default_location').wait()
  default_location = util.deserialize(rv['location'])
  ui.handle_input('join %s' % str(default_location['control_address'])).wait()
  
  shared.pool.spawn(ui.input_loop)
  shared.pool.waitall()
