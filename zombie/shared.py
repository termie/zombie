from eventlet import greenpool
from eventlet.green import zmq
from eventlet.hubs import use_hub

use_hub('zeromq')

zctx = zmq.Context()
pool = greenpool.GreenPool()
