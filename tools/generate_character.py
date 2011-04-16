#!/usr/bin/env python
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from zombie import character
from zombie import world


if __name__ == '__main__':
  char_id = sys.argv[1]
  world_id = sys.argv[2]
  w = world.WorldNode.Load(world_id)
  c = character.CharacterNode.Generate(char_id, char_id)
  c.save()
  w.sign_node(c)
  c.save()
  c.trust_key(world_id, w.dsa_pub)
  c.save()
  w.save()
