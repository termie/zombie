import logging

from zombie import character
from zombie import shared
from zombie.ui import curse


if __name__ == '__main__':
  bind = 'ipc:///tmp/foo'
  logging.getLogger().setLevel(logging.DEBUG)


  termie = character.CharacterNode.Load('termie')
  ui = curse.CursesUi(termie, bind)
  ui.init()

  shared.pool.spawn(ui.input_loop)
  shared.pool.waitall()
