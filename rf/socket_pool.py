import logging
from rf.multithreading import counter
import socket
from threading import local

from rf.util import call_with_timeout
from Queue import Queue


log = logging.getLogger(__name__)

DEFAULT_INITIAL_POOL_SIZE = 5
DEFAULT_MAX_POOL_SIZE = 50
DEFAULT_CONNECT_TIMEOUT = 5


class SocketPoolException(Exception):
    pass


class SocketWrapper(object):

    __slots__ = ('__pool', '_sock', '_sock_closed')

    def __init__(self, pool, sock):
        self.__pool = pool
        self._sock = sock
        self._sock_closed = False

    def __getattr__(self, name):
        if name == "_sock":
            return None
        return getattr(self._sock, name)

    def close(self):
        self._sock.close()
        self._sock_closed = True

    def shutdown(self, how=socket.SHUT_RDWR):
        self._sock.shutdown(how)

    def __del__(self):
        if self._sock is not None:
            self.__pool.return_socket(self)
            del self.__pool
            del self._sock


class NoopPool(local):
    """
    A simple socket pool which always returns the same socket.
    Since this is thread-local, each thread will have its own socket.
    """
    def __init__(self,
                 socket_factory,
                 pool_size=None,
                 max_pool_size=None,
                 connect_timeout=None,
                 name=None,
                 queue_class=None,
                 call_with_timeout_callable=None):
        self.socket_factory = socket_factory
        self.sock = None
        self.name = name

    def socket(self):
        if self.sock is None:
            log.debug("NoopPool.socket() %r creating a new socket", self.name)
            sock = self.socket_factory()
            if isinstance(sock, SocketWrapper):
                self.sock = sock
            else:
                self.sock = SocketWrapper(self, sock)
        return self.sock

    def return_socket(self, sock_wrapper=None):
        if self.sock and self.sock._sock_closed:
            self.sock = None


class SocketPool(object):
    def __init__(self,
                 socket_factory,
                 pool_size=DEFAULT_INITIAL_POOL_SIZE,
                 max_pool_size=DEFAULT_MAX_POOL_SIZE,
                 connect_timeout=DEFAULT_CONNECT_TIMEOUT,
                 name=None,
                 queue_class=None,
                 call_with_timeout_callable=None):
        """
        A socket pool.

        The default queue_class is Queue.Queue
        The default call_with_timeout_callable is util.call_with_timeout
        """
        log.debug("SocketPool.__init__(%r, %r, %r, %r)", socket_factory, pool_size, max_pool_size, name)
        self.socket_factory = socket_factory
        self.pool_size = pool_size
        self.max_pool_size = max_pool_size
        self.connect_timeout = connect_timeout
        self.sockets = None
        self.num_socks = counter('SocketPool %s' % name)
        self.in_use = set()
        self.name = name
        self.queue_class = queue_class or Queue
        self.call_with_timeout_callable = call_with_timeout_callable or call_with_timeout
        
    def socket(self):
        if not self.sockets:
            self._initialize()
        log.debug("SocketPool.socket() START %r num_socks: %r, qsize: %r, in_use: %r",
                  self.name, self.num_socks.get(), self.sockets.qsize(), len(self.in_use))
        if not self.sockets.qsize() and self.num_socks.get() < self.max_pool_size:
            log.warn("SocketPool %r is out of sockets, creating a new one, num_socks: %r, qsize: %r, in_use: %r",
                     self.name, self.num_socks.get(), self.sockets.qsize(), len(self.in_use))
            sock = self._new_socket()
        else:
            if not self.sockets.qsize():
                log.warn("SocketPool %r is out of sockets and at max_pool_size (%r), waiting for a socket to be returned",
                         self.name, self.max_pool_size)
            log.debug("SocketPool.socket() %r getting a socket from the Queue", self.name)
            sock = self.sockets.get()
        self.in_use.add(sock)
        log.debug("SocketPool.socket() END   %r num_socks: %r, qsize: %r, in_use: %r",
                  self.name, self.num_socks.get(), self.sockets.qsize(), len(self.in_use))
        if not isinstance(sock, SocketWrapper):
            sock = SocketWrapper(self, sock)
        return sock
    
    def _initialize(self):
        log.debug("SocketPool._initialize() %r", self.name)
        self.sockets = self.queue_class(self.max_pool_size + 1)
        for i in range(self.pool_size):
            sock = self._new_socket()
            self.sockets.put(sock)

    def _new_socket(self):
        log.debug("SocketPool.new_socket() %r", self.name)
        (success, sock) = self.call_with_timeout_callable(self.socket_factory, self.connect_timeout * 1000, None)
        if not success:
            raise SocketPoolException("Connect timed out after %r seconds" % self.connect_timeout)
        if sock is None:
            raise SocketPoolException("None returned from socket factory %r" % self.socket_factory)
        self.num_socks.inc()
        return sock
    
    def return_socket(self, sock_wrapper=None):
        log.debug("SocketPool.return_socket(%r) %r", sock_wrapper, self.name)
        if sock_wrapper is None:
            return
        if sock_wrapper._sock is None:
            # if _sock is None, we've already reclaimed the socket
            return
        log.debug("SocketPool.return_socket() START %r num_socks: %r, qsize: %r, in_use: %r",
                  self.name, self.num_socks.get(), self.sockets.qsize(), len(self.in_use))
        try:
            try:
                self.in_use.remove(sock_wrapper._sock)
            except:
                log.exception("exception removing %r from self.in_use %r",
                              sock_wrapper._sock, self.in_use)
            if sock_wrapper._sock_closed:
                self._socket_closed()
                return
            
            log.debug("SocketPool.return_socket() returning socket to the Queue")
            self.sockets.put(sock_wrapper._sock)
        finally:
            sock_wrapper._sock = None
        log.debug("SocketPool.return_socket() END   %r num_socks: %r, qsize: %r, in_use: %r",
                  self.name, self.num_socks.get(), self.sockets.qsize(), len(self.in_use))

    def _socket_closed(self):
        log.warn("SocketPool._socket_closed() %r num_socks: %r, qsize: %r",
                 self.name, self.num_socks.get(), self.sockets.qsize())
        self.num_socks.dec()        

