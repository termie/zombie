#!/usr/bin/env python

import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


from zombie import world


if __name__ == '__main__':
  logging.getLogger().setLevel(logging.DEBUG)
  world_id = sys.argv[1]
  w = world.WorldNode.Generate(world_id, world_id)
  w.save()
  w.trust_key(world_id, w.dsa_pub)
  w.save()
