#!/usr/bin/env python

"""Tiny CLI to push commands to client_indirect."""

import eventlet
eventlet.monkey_patch()

import sys

import gflags
import zmq

from zombie import shared


FLAGS = gflags.FLAGS


gflags.DEFINE_string('connect_address', 'ipc:///tmp/bar', 'connect address')


if __name__ == '__main__':
  args = FLAGS(sys.argv)
  connect_sock = shared.zctx.socket(zmq.XREQ)
  connect_sock.connect(FLAGS.connect_address)

  connect_sock.send_multipart(args[1:])
