import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from zombie.mod import location

if __name__ == '__main__':
  location.load_from_file(sys.argv[1])
