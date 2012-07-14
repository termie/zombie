class Error(Exception):
  pass


def wrap(e):
  return Error(str(e))


class RemoteError(Error):
  pass


