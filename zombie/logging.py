from __future__ import absolute_import

import logging
import sys

import gflags


FLAGS = gflags.FLAGS
gflags.DEFINE_boolean('verbose', True,
                      'verbose logging output')


def setup():
  if FLAGS.verbose:
    level = logging.DEBUG
  else:
    level = logging.WARNING

  stderr_handler = logging.StreamHandler(sys.stderr)
  #log_format = '%(asctime)s %(levelname)s %(message)s'
  log_format = '%(levelname)s (%(module)s) %(message)s'
  stderr_handler.setFormatter(logging.Formatter(log_format))
  root = logging.getLogger()
  root.addHandler(stderr_handler)
  root.setLevel(level)

DEBUG = logging.DEBUG
WARNING = logging.WARNING

log = logging.log
exception = logging.exception
critical = logging.critical
error = logging.error
warning = logging.warning
info = logging.info
debug = logging.debug
getLogger = logging.getLogger
