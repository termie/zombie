from eventlet import greenpool
from eventlet.green import zmq


zctx = zmq.Context()
pool = greenpool.GreenPool()
