from zombie import log as logging


class EventEmitter(object):
  def __init__(self):
    self._event_handlers = {}

  def on(self, event, handler, *args, **kw):
    handlers = self._event_handlers.get(event, [])
    handlers.append([handler, args, kw])

  def emit(self, event, *args, **kw):
    handlers = self._event_handlers.get(event, [])
    for handler, h_args, h_kw in handlers:
      all_args = h_args + args
      all_kw = h_kw.copy()
      all_kw.update(kw)
      try:
        handler(*all_args, **all_kw)
      except Exception:
        logging.exception('exception in event handler')
