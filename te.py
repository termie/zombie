import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import eventlet
eventlet.monkey_patch()

from lyntin import net as l_net
from lyntin import engine
from lyntin import event
from lyntin import exported

from zombie import character
from zombie import net
from zombie import shared
from zombie import util


pool = shared.pool

OrigSocketCommunicator = l_net.SocketCommunicator

class SocketCommunicator(OrigSocketCommunicator):
  def __init__(self, *args, **kw):
    OrigSocketCommunicator.__init__(self, *args, **kw)
    self.character = character.Character.load('termie')

  def connect(self, host, port, sessionname):
    if not self._sock:
      sock = net.Client(self.character)
      sock.connect('tcp://%s:%s' % (host, port))
      self._host = host
      self._port = port
      self._sock = sock
      self._sessioname = sessionname
      ses = exported.get_session(sessionname)
      exported.hook_spam("connect_hook", \
              {"session": ses, "host": host, "port": port})

  def _pollForData(self):
    data = self._sock.recv()
    return util.serialize(data)


class EventletEngine(engine.Engine):
  def startthread(self, name, func):
    print "STARTTHREAD", name
    return pool.spawn_n(func)

  def _threadCleanup(self):
    pass

  def checkthreads(self):
    return ['    up - up']

  def runtimer(self):
    while True:
      eventlet.sleep(1)
      event.SpamEvent(hookname="timer_hook", 
                argmap={"tick": self._current_tick}
               ).enqueue()
  
  def runengine(self):
    while not self._shutdownflag:
      try:
        # blocks on the event queue
        e = self._event_queue.get()
        e.execute()
      except KeyboardInterrupt:
        return
      except SystemExit:
        return
      except:
        self.tallyError()
        exported.write_traceback("engine: unhandled error in engine.")
      self._num_events_processed += 1
      eventlet.sleep(0.1)

l_net.SocketCommunicator = SocketCommunicator
engine.Engine = EventletEngine

if __name__ == '__main__':
  engine.main({"ui": "curses"})
  
