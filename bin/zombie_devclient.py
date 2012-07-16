#!/usr/bin/env python

"""Run a basic client that connects to a game."""

import eventlet
eventlet.monkey_patch()

import code
import logging
import os
import pprint
import sys

# If ../zombie/__init__.py exists, add ../ to Python search path, so that
# it will override what happens to be installed in /usr/(local/)lib/python...
possible_topdir = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]),
                                   os.pardir,
                                   os.pardir))
if os.path.exists(os.path.join(possible_topdir, 'zombie', '__init__.py')):
    sys.path.insert(0, possible_topdir)


import gflags
import zmq

from zombie import client
from zombie import shared


FLAGS = gflags.FLAGS
gflags.DEFINE_string('world', 'tcp://127.0.0.1:2222',
                     'world address')
gflags.DEFINE_string('user', 'darkthorn',
                     'id of default user')


try:
    import readline
    import rlcompleter
    import os
    import atexit

    historyPath = os.path.expanduser("~/.py_history")

    def save_history(historyPath=historyPath):
        import readline
        readline.write_history_file(historyPath)

    if os.path.exists(historyPath):
        readline.read_history_file(historyPath)

    atexit.register(save_history)
    del os, atexit, readline, rlcompleter, save_history, historyPath
    print '''Using readline'''
except ImportError:
    print '''You should install readline... try: python `python -c "import pimp; print pimp.__file__"` -i readline'''

def main():
  logging.getLogger().setLevel(logging.DEBUG)

  user_ref = client.User(id=FLAGS.user)
  cl = client.Client(user_ref)
  cl._rejoin_game(FLAGS.world)

  #shared.pool.waitall()
  banner = """
  You are now in an interactive python shell.

  You've got couple variables already floating around in here:

    cl: the client object
      - _move_location($location_id)

  """
  vars = globals().copy()
  vars.update(locals())
  shell = code.InteractiveConsole(vars)
  shell.interact(banner)


if __name__ == '__main__':
  FLAGS(sys.argv)
  main()
