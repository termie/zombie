import base64
import json


def deserialize(msg):
  return json.loads(msg)


def serialize(msg):
  return json.dumps(msg)


def b64_encode(s):
  return base64.urlsafe_b64encode(s)
