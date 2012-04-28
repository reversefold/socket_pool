
def flatten(l, ltypes=(list, tuple)):
    """
    Takes a list or tuple with other lists or tuples within it
    and flattens them all down to a single list.

    If you want to flatten lists but not tuples (or vice-versa)
    pass in an amended ltypes argument.

    Ex:
    flatten([[1, 2, 3], [4, 5, 6]])
    [1, 2, 3, 4, 5, 6]
    
    flatten([1, 2, [3, 4, [5, 6]]])
    [1, 2, 3, 4, 5, 6]
    """
    ltype = type(l)
    l = list(l)
    i = 0
    while i < len(l):
        while isinstance(l[i], ltypes):
            if not l[i]:
                l.pop(i)
                i -= 1
                break
            else:
                l[i:i + 1] = l[i]
        i += 1
    return ltype(l)


def tail(f, window=20, sentinel='\n'):
    """
    Returns the last `window` lines of file `f` as a list.
    """
    BUFSIZ = 1024
    f.seek(0, 2)
    bytes = f.tell()
    size = window + 1
    block = -1
    data = []
    while size > 0 and bytes > 0:
        if bytes - BUFSIZ > 0:
            # Seek back one whole BUFSIZ
            f.seek(block * BUFSIZ, 2)
            # read BUFFER
            data.insert(0, f.read(BUFSIZ))
        else:
            # file too small, start from begining
            f.seek(0,0)
            # only read what was not read
            data.insert(0, f.read(bytes))
        linesFound = data[0].count(sentinel)
        size -= linesFound
        bytes -= BUFSIZ
        block -= 1
    return ''.join(data).splitlines()[-window:]


class _InterruptableThread(threading.Thread):
    def __init__(self, callable):
        threading.Thread.__init__(self)
        self.result = None
        self.exc_info = None
        self.callable = callable

    def run(self):
        try:
            self.result = self.callable()
        except:
            self.exc_info = sys.exc_info()

def call_with_timeout(callable, timeout_duration=1000, default=None):
    """
    Calls callable and returns its value. If callable doesn't return
    within timeout_duration milliseconds, default will be returned instead.

    If timeout_duration is None, callable will be called normally, without a
    timeout, and the return value will always indicate "success".

    Returns a tuple containing whether or not callable returned before the
    timeout was reached and the value returned by callable or default.

    Examples:
    def foo():
        import time
        import random
        time.sleep(random.random() + 0.5)
        return "ok"

    (success, value) = call_with_timeout(foo)
    if not success:
        raise Exception("yo")

    (success, value) = call_with_timeout(foo)
    return value if success else 'default'

    return call_with_timeout(foo, 'default')[1]
    """
    if timeout_duration is None:
        return (True, callable())

    it = _InterruptableThread(callable)
    it.daemon = True
    it.start()
    it.join(timeout_duration / 1000.0)
    if it.isAlive():
        paste.util.killthread.async_raise(it.ident, SystemExit)
        return (False, default)
    else:
        if it.exc_info:
            raise it.exc_info[1], None, it.exc_info[2]
        return (True, it.result)


def unique(s):
     """Return a list of the elements in s, but without duplicates.

     For example, unique([1,2,3,1,2,3]) is some permutation of
     [1,2,3],
     unique("abcabc") some permutation of ["a", "b", "c"], and
     unique(([1, 2], [2, 3], [1, 2])) some permutation of
     [[2, 3], [1, 2]].

     For best speed, all sequence elements should be hashable.  Then
     unique() will usually work in linear time.

     If not possible, the sequence elements should enjoy a total
     ordering, and if list(s).sort() doesn't raise TypeError it's
     assumed that they do enjoy a total ordering.  Then unique() will
     usually work in O(N*log2(N)) time.

     If that's not possible either, the sequence elements must support
     equality-testing.  Then unique() will usually work in quadratic
     time.
     """

     n = len(s)
     if n == 0:
         return []

     # Try using a dict first, as that's the fastest and will usually
     # work.  If it doesn't work, it will usually fail quickly, so it
     # usually doesn't cost much to *try* it.  It requires that all
     # the
     # sequence elements be hashable, and support equality comparison.
     u = {}
     try:
         for x in s:
             u[x] = 1
     except TypeError:
         del u  # move on to the next method
     else:
         return u.keys()

     # We can't hash all the elements.  Second fastest is to sort,
     # which brings the equal elements together; then duplicates are
     # easy to weed out in a single pass.
     # NOTE:  Python's list.sort() was designed to be efficient in the
     # presence of many duplicate elements.  This isn't true of all
     # sort functions in all languages or libraries, so this approach
     # is more effective in Python than it may be elsewhere.
     try:
         t = list(s)
         t.sort()
     except TypeError:
         del t  # move on to the next method
     else:
         assert n > 0
         last = t[0]
         lasti = i = 1
         while i < n:
             if t[i] != last:
                 t[lasti] = last = t[i]
                 lasti += 1
             i += 1
         return t[:lasti]

     # Brute force is all that's left.
     u = []
     for x in s:
         if x not in u:
             u.append(x)
     return u
