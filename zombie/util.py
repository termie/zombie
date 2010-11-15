import json


def deserialize(msg):
  return json.loads(msg)


def serialize(msg):
  return json.dumps(msg)
