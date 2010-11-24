import eventlet
from eventlet import wsgi
from eventlet import websocket
import static

from zombie import log as logging
from zombie import shared
from zombie.ui import base


class WebSocketUi(base.Ui):
  def __init__(self, *args, **kw):
    super(WebSocketUi, self).__init__(*args, **kw)
  
  def init(self):
    super(WebSocketUi, self).init()
    def static_server():
      wsgi.server(eventlet.listen(('', 8080)), static.Cling('/Users/termie/p/zombie/www'))
    shared.pool.spawn(static_server)
    

  def ws_app(self):
    def _new_websocket(ws):
      ws.send('bleep bloop')
      data = ws.wait()
      print data
    
    return websocket.WebSocketWSGI(_new_websocket)


  def input_loop(self):
    wsgi.server(eventlet.listen(('', 8090)), self.ws_app())

