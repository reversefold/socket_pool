import logging
from thread import LockType
from threading import Lock

log = logging.getLogger(__name__)


def counter(name):
    sync = synchronized(name)
    class CounterImpl(object):
        def __init__(self, name):
            self.name = name
            self.value = 0
            # NOTE: I don't think that a simple return of a value needs to be synchronized
            #self.get = sync(self._get)
            self.get = self._get
            self.inc = sync(self._inc)
            self.dec = sync(self._dec)

        def _get(self):
            return self.value

        def _inc(self, n=1):
            self.value += n
            #log.debug("Incremented %r to %r", self.name, self.value)
            return self.value

        def _dec(self, n=1):
            self.value -= n
            #log.debug("Decremented %r to %r", self.name, self.value)
            return self.value

    return CounterImpl(name)


_lock_lock = Lock()
_locks = {}


def synchronized(lock):
    """
    Synchronization decorator.
    Pass in either a lock instance or a key (str preferred) which names a lock.
    """
    if not isinstance(lock, LockType):
        with _lock_lock:
            if lock not in _locks:
                _locks[lock] = Lock()
            lock = _locks[lock]

    def wrap(f):
        def new_function(*args, **kw):
            with lock:
                return f(*args, **kw)
        return new_function
    return wrap


def count_cls(cls):
    if hasattr(cls, '_cls_counted'):
        return cls
    for name, method in cls.__dict__.iteritems():
        if hasattr(method, '_counted') and method._counted:
            method._count_cls = cls
    cls._cls_counted = True
    return cls


def count(f):
    if hasattr(f, '_counted'):
        return f
    def wrapped(*args, **kw):
        if not wrapped._counter:
            wrapped._func_name = str(f)
            if hasattr(f, 'im_class') and f.im_class:
                wrapped._func_name = "%r - %s" % (f.im_class, wrapped._func_name)
            elif hasattr(wrapped, '_count_cls') and wrapped._count_cls:
                wrapped._func_name = "%r - %s" % (wrapped._count_cls, wrapped._func_name)
            wrapped._counter = counter(wrapped._func_name)

        current_count = wrapped._counter.inc()
        log.debug("%r called %r times", wrapped._func_name, current_count)
        return f(*args, **kw)
    wrapped._counted = True
    wrapped._counter = None
    wrapped._func_name = None
    return wrapped
