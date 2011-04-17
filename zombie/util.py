import base64
import logging
import json
import sys

import gflags

from zombie import exception


FLAGS = gflags.FLAGS



def loads(s):
  try:
    rv = json.loads(s)
    try:
      return dict((str(k), v) for k, v in rv.iteritems())
    except Exception:
      return rv
  except Exception as e:
    raise exception.wrap(e)


def dumps(obj):
  return json.dumps(obj)


def b64_encode(s):
  return base64.urlsafe_b64encode(s)


def import_class(import_str):
    """Returns a class from a string including module and class."""
    mod_str, _sep, class_str = import_str.rpartition('.')
    try:
        __import__(mod_str)
        return getattr(sys.modules[mod_str], class_str)
    except (ImportError, ValueError, AttributeError), exc:
        logging.debug('Inner Exception: %s', exc)
        raise exception.Error('Class %s cannot be found: %s' % (class_str,
                                                                import_str))


class LazyPluggable(object):
  """A pluggable backend loaded lazily based on some value."""

  def __init__(self, pivot):
    self.__pivot = pivot
    self.__backend = None

  def __get_backend(self):
    if not self.__backend:
      backend_name = getattr(FLAGS, self.__pivot)
      self.__backend = import_class(backend_name)
    return self.__backend

  def __call__(self, *args, **kw):
    return self.__get_backend()(*args, **kw)

  def __getattr__(self, key):
    backend = self.__get_backend()
    return getattr(backend, key)
