import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from zombie import character

if __name__ = '__name__':
  char_id = sys.argv[1]
  c = character.CharacterNode.Generate(char_id, char_id)
  c.save()
