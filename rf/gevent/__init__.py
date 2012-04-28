from gevent import Timeout

def call_with_timeout(callable, timeout_duration=1000, default=None):
    with Timeout(timeout_duration, False):
        return (True, callable())
    return (False, default)
