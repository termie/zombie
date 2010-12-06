import base64
import json

from zombie import exception


def loads(s):
  try:
    return json.loads(s)
  except Exception as e:
    raise exception.wrap(e)


def dumps(obj):
  return json.dumps(obj)


def b64_encode(s):
  return base64.urlsafe_b64encode(s)
