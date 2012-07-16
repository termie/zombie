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


def main():
  logging.getLogger().setLevel(logging.DEBUG)

  user_ref = client.User(id=FLAGS.user)
  cl = client.Client(user_ref)
  cl._rejoin_game(FLAGS.world)

  #shared.pool.waitall()
  vars = globals().copy()
  vars.update(locals())
  shell = code.InteractiveConsole(vars)
  shell.interact()


if __name__ == '__main__':
  FLAGS(sys.argv)
  main()
