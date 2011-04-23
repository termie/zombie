#!/usr/bin/env python

import logging
import sys

import gflags
import nose

from zombie import test


if __name__ == '__main__':
  logging.getLogger().setLevel(logging.DEBUG)
  test.main()
