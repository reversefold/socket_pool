from queue import Empty
from rf.socket_pool import SocketPool
from pymongo import pool


class Error(Exception):
    pass


class NoopLock(object):
    def acquire(self):
        pass

    def release(self):
        pass


class SetSocketPool(SocketPool):
    def __init__(self, *args, **kwargs):
        super(SetSocketPool, self).__init__(*args, **kwargs)

    def add(self, sock):
        self.return_socket(sock)

    def pop(self):
        return self.socket()

    def __iter__(self):
        # special case, we're always going to remove all sockets when iterating
        socks = []
        while True:
            try:
                socks.append(self.sockets.get(False))
            except Empty:
                break
        return iter(socks)


class MongoDBPool(pool.Pool):
    def __init__(self, *args, **kwargs):
        pool_size = kwargs.pop('pool_size', None)
        max_pool_size = kwargs.pop('max_pool_size', None)
        super(MongoDBPool, self).__init__(*args, **kwargs)

        self.sockets = SetSocketPool(
            self.socket_factory,
            pool_size,
            max_pool_size,
            kwargs.get('conn_timeout'))
        self.lock = NoopLock()

    def socket_factory(self):
        return self.connect(self.pair)

    def get_socket(self, pair=None):
        if pair is not None:
            raise Error('This socket pool does not support on-demand socket pairs')
        super(MongoDBPool, self).get_socket(pair)

    def _return_socket(self, sock_info):
        self.sockets.add(sock_info)
