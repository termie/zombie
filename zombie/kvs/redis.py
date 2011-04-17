from __future__ import absolute_import

import logging

import gflags
import redis


FLAGS = gflags.FLAGS


class Store(object):
  def __init__(self, prefix=''):
    self.r = redis.Redis()
    self.prefix = prefix

  def set(self, key, value):
    self.r.set(FLAGS.kvs_prefix + self.prefix + key, value)

  def get(self, key):
    return self.r.get(FLAGS.kvs_prefix + self.prefix + key)
