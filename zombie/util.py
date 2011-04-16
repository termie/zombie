import base64
import json

from zombie import exception


def loads(s):
  try:
    rv = json.loads(s)
    return dict((str(k), v) for k, v in rv.iteritems())
  except Exception as e:
    raise exception.wrap(e)


def dumps(obj):
  return json.dumps(obj)


def b64_encode(s):
  return base64.urlsafe_b64encode(s)
