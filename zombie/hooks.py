from zombie import log as logging

HOOKS = {}

def add(key, f, insert=None):
  h = HOOKS.get(key, [])
  if insert is not None:
    h.insert(insert, f)
  else:
    h.append(f)
  HOOKS[key] = h


def get(key):
  return HOOKS.get(key, [])


def run(key, *args, **kw):
  for h in get(key):
    logging.debug('running hook (%s) -> %s', key, h.func_name)
    try:
      rv = h(*args, **kw)
      if rv:
        break
    except Exception:
      logging.exception('while running hooks')
