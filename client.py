#!/usr/bin/env python
import eventlet
eventlet.monkey_patch()

import sys

import gflags

from zombie import character
from zombie import logging
from zombie import net
from zombie import shared
from zombie import util
from zombie.ui import text


FLAGS = gflags.FLAGS


if __name__ == '__main__':
  args = FLAGS(sys.argv)
  logging.setup()

  bind = 'ipc:///tmp/foo'
  world_id = 'foo'

  termie = character.CharacterNode.Load('termie')
  #termie.init()

  #ui = websocket.WebSocketUi(termie, bind)
  ui = text.TextUi(termie, bind)
  ui.init()

  ui.handle_input('connect %s %s' % (bind, world_id)).wait()
  rv = ui.handle_input('default_location').wait()
  default_location = util.deserialize(rv['location'])
  ui.handle_input('join %s' % str(default_location['control_address'])).wait()

  shared.pool.spawn(ui.input_loop)
  shared.pool.waitall()
