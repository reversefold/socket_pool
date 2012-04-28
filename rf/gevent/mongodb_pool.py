import pymongo

from rf.gevent.socket_pool import SocketPool

pymongo.connection._Pool = SocketPool
