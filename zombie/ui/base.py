import eventlet
import logging


from zombie import net
from zombie import shared


class Ui(object):
  def __init__(self, character, waddress):
    self.character = character
    self.wclient = None
    self.lclient = None
    self.waddress = waddress
    self._cmds = {}

  def init(self):
    self._init_cmds()

  def _init_cmds(self):
    self._cmds['connect'] = self._cmd_connect
    self._cmds['join'] = self._cmd_join

  def _cmd_join(self, cmd, args):
    if self.lclient:
      self.lclient.rpc('leave')
      self.lclient.close()
      self.lclient = None

    self.lclient = net.NodeClient(self.character)
    self.lclient.connect_control(args)
    #self.lclient.connect_pubsub()

    shared.pool.spawn_n(self.lclient.control_loop)
    #shared.pool.spawn_n(self.lclient.pubsub_loop)

    #self._cmd_look('look', '')

  def _cmd_nop(self):
    return None

  def _cmd_connect(self, cmd, args):
    if self.wclient:
      self.wclient.rpc('leave')
      self.wclient.close()
      self.wclient = None

    logging.debug('connect args: %s' % args)
    self.wclient = net.NodeClient(self.character)
    self.wclient.connect_control(self.waddress, args.split(' ')[1])
    #self.wclient.connect_pubsub()
    shared.pool.spawn_n(self.wclient.control_loop)
    #shared.pool.spawn_n(self.wclient.pubsub_loop)

  def input_loop(self):
    while True:
      eventlet.sleep(0.1)

  def handle_input(self, data):
    cmd, sep, rest = data.partition(' ')
    if not cmd.strip():
      return shared.pool.spawn(self._cmd_nop)
    if cmd in self._cmds:
      return shared.pool.spawn(self._cmds[cmd], cmd, rest)
    if self.lclient:
      return shared.pool.spawn(self.lclient.rpc, cmd, args=rest)
    else:
      return shared.pool.spawn(self.wclient.rpc, cmd, args=rest)
