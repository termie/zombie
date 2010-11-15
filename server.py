from zombie import world
from zombie import net


# TODO(termie): allow requesting pubkey via http


if __name__ == '__main__':
  bind = 'ipc:///tmp/foo'

  foo = world.World.load('foo')
  server = net.Server(foo)
  server.listen(bind)
