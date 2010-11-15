HOOKS = {}

def add(key, f):
  h = HOOKS.get(key, [])
  h.append(f)


def get(key):
  return HOOKS.get(key, [])


def run(key, *args, **kw):
  for h in get(key):
    h(*args, **kw)
