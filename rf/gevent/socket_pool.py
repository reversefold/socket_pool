from rf.gevent import call_with_timeout
from gevent.queue import Queue

import logging
import socket

log = logging.getLogger(__name__)

import rf.util.socket_pool
from rf.util.socket_pool import SocketPoolException, SocketWrapper


class SocketPool(rf.SocketPool):
    def __init__(self,
                 *args,
                 **kwargs):
        kwargs.setdefault('queue_class', Queue)
        kwargs.setdefault('call_with_timeout_callable', call_with_timeout)
        super(SocketPool, self).__init__(*args, **kwargs)
