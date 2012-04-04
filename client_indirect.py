#!/usr/bin/env python

"""A client that prints results from the server and listens for new commands.

Basically, I got tired of dealing with curses and the like, so this acts as an
intermediate that will print stuff from the server as it comes in, letting you
use a command-line client to send new commands for it to forward to the server.
"""

import eventlet
eventlet.monkey_patch()

import sys

import gflags
import zmq

from zombie import shared


FLAGS = gflags.FLAGS


gflags.DEFINE_string('connect_address', 'ipc:///tmp/foo', 'connect address')
gflags.DEFINE_string('listen_address', 'ipc:///tmp/bar', 'listen address')


def forward(listen_sock, connect_sock):
  while True:
    parts = listen_sock.recv_multipart()
    print '>>> ', parts[1:]
    connect_sock.send_multipart(parts[1:])


def display(connect_sock):
  while True:
    parts = connect_sock.recv_multipart()
    print parts
    print


if __name__ == '__main__':
  args = FLAGS(sys.argv)

  print 'listening on %s' % FLAGS.listen_address
  listen_sock = shared.zctx.socket(zmq.XREP)
  listen_sock.bind(FLAGS.listen_address)

  print 'connecting to %s' % FLAGS.connect_address
  connect_sock = shared.zctx.socket(zmq.XREQ)
  connect_sock.connect(FLAGS.connect_address)

  shared.pool.spawn(forward, listen_sock, connect_sock)
  shared.pool.spawn(display, connect_sock)

  shared.pool.waitall()
