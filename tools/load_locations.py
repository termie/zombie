import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from zombie.mod import locations

if __name__ == '__main__':
  locations.load_from_file(sys.argv[1])
