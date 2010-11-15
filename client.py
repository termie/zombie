import eventlet
eventlet.monkey_patch()

from zombie import character
from zombie import net


if __name__ == '__main__':
  bind = 'ipc:///tmp/foo'

  termie = character.Character.load('termie')
  termie.init()
  client = net.Client(termie)
  client.connect(bind)

  client.clientloop()
