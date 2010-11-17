import eventlet
eventlet.monkey_patch()

from zombie import character
from zombie import net
from zombie.ui import text


if __name__ == '__main__':
  bind = 'ipc:///tmp/foo'
  

  termie = character.Character.load('termie')
  termie.init()

  
  ui = text.TextUi(termie, bind)
  ui.run()
  

  #client = net.Client(termie)
  #client.connect(bind)

  #client.clientloop()
