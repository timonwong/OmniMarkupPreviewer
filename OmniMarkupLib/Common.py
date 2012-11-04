"""
Copyright (c) 2012 Timon Wong

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import sys
import copy
import thread
from threading import Condition, Lock, current_thread
from contextlib import contextmanager
from time import time
import log


class Singleton(object):
    def __init__(self, decorated):
        decorated.__lock_obj = thread.allocate_lock()
        decorated.__instance = None
        self.__decorated = decorated

    def instance(self):
        with self.__decorated.__lock_obj:
            if self.__decorated.__instance is None:
                self.__decorated.__instance = self.__decorated()
            return self.__decorated.__instance

    def __call__(self):
        raise TypeError('Singletons must be accessed through `Instance()`.')

    def __instancecheck__(self, inst):
        return isinstance(inst, self.__decorated)


## {{{ http://code.activestate.com/recipes/502283/ (r1)
# Read write lock
class RWLock(object):
    def __init__(self, lock=None):
        """Initialize this read-write lock."""

        # Condition variable, used to signal waiters of a change in object
        # state.
        if lock is None:
            self.__condition = Condition(Lock())
        else:
            self.__condition = Condition(lock)

        # Initialize with no writers.
        self.__writer = None
        self.__upgradewritercount = 0
        self.__pendingwriters = []

        # Initialize with no readers.
        self.__readers = {}

    def acquireRead(self, blocking=True, timeout=None):
        """Acquire a read lock for the current thread, waiting at most
        timeout seconds or doing a non-blocking check in case timeout is <= 0.

        In case timeout is None, the call to acquireRead blocks until the
        lock request can be serviced.

        In case the timeout expires before the lock could be serviced, a
        RuntimeError is thrown."""

        if not blocking:
            endtime = -1
        elif timeout is not None:
            endtime = time() + timeout
        else:
            endtime = None
        me = current_thread()
        self.__condition.acquire()
        try:
            if self.__writer is me:
                # If we are the writer, grant a new read lock, always.
                self.__writercount += 1
                return
            while True:
                if self.__writer is None:
                    # Only test anything if there is no current writer.
                    if self.__upgradewritercount or self.__pendingwriters:
                        if me in self.__readers:
                            # Only grant a read lock if we already have one
                            # in case writers are waiting for their turn.
                            # This means that writers can't easily get starved
                            # (but see below, readers can).
                            self.__readers[me] += 1
                            return
                        # No, we aren't a reader (yet), wait for our turn.
                    else:
                        # Grant a new read lock, always, in case there are
                        # no pending writers (and no writer).
                        self.__readers[me] = self.__readers.get(me, 0) + 1
                        return
                if timeout is not None:
                    remaining = endtime - time()
                    if remaining <= 0:
                        # Timeout has expired, signal caller of this.
                        raise RuntimeError("Acquiring read lock timed out")
                    self.__condition.wait(remaining)
                else:
                    self.__condition.wait()
        finally:
            self.__condition.release()

    def acquireWrite(self, timeout=None):
        """Acquire a write lock for the current thread, waiting at most
        timeout seconds or doing a non-blocking check in case timeout is <= 0.

        In case the write lock cannot be serviced due to the deadlock
        condition mentioned above, a ValueError is raised.

        In case timeout is None, the call to acquireWrite blocks until the
        lock request can be serviced.

        In case the timeout expires before the lock could be serviced, a
        RuntimeError is thrown."""

        if timeout is not None:
            endtime = time() + timeout
        me, upgradewriter = current_thread(), False
        self.__condition.acquire()
        try:
            if self.__writer is me:
                # If we are the writer, grant a new write lock, always.
                self.__writercount += 1
                return
            elif me in self.__readers:
                # If we are a reader, no need to add us to pendingwriters,
                # we get the upgradewriter slot.
                if self.__upgradewritercount:
                    # If we are a reader and want to upgrade, and someone
                    # else also wants to upgrade, there is no way we can do
                    # this except if one of us releases all his read locks.
                    # Signal this to user.
                    if timeout is not None:
                        raise RuntimeError("Write lock upgrade would deadlock until timeout")
                    else:
                        raise ValueError("Inevitable dead lock, denying write lock")
                upgradewriter = True
                self.__upgradewritercount = self.__readers.pop(me)
            else:
                # We aren't a reader, so add us to the pending writers queue
                # for synchronization with the readers.
                self.__pendingwriters.append(me)
            while True:
                if not self.__readers and self.__writer is None:
                    # Only test anything if there are no readers and writers.
                    if self.__upgradewritercount:
                        if upgradewriter:
                            # There is a writer to upgrade, and it's us. Take
                            # the write lock.
                            self.__writer = me
                            self.__writercount = self.__upgradewritercount + 1
                            self.__upgradewritercount = 0
                            return
                        # There is a writer to upgrade, but it's not us.
                        # Always leave the upgrade writer the advance slot,
                        # because he presumes he'll get a write lock directly
                        # from a previously held read lock.
                    elif self.__pendingwriters[0] is me:
                        # If there are no readers and writers, it's always
                        # fine for us to take the writer slot, removing us
                        # from the pending writers queue.
                        # This might mean starvation for readers, though.
                        self.__writer = me
                        self.__writercount = 1
                        self.__pendingwriters = self.__pendingwriters[1:]
                        return
                if timeout is not None:
                    remaining = endtime - time()
                    if remaining <= 0:
                        # Timeout has expired, signal caller of this.
                        if upgradewriter:
                            # Put us back on the reader queue. No need to
                            # signal anyone of this change, because no other
                            # writer could've taken our spot before we got
                            # here (because of remaining readers), as the test
                            # for proper conditions is at the start of the
                            # loop, not at the end.
                            self.__readers[me] = self.__upgradewritercount
                            self.__upgradewritercount = 0
                        else:
                            # We were a simple pending writer, just remove us
                            # from the FIFO list.
                            self.__pendingwriters.remove(me)
                        raise RuntimeError("Acquiring write lock timed out")
                    self.__condition.wait(remaining)
                else:
                    self.__condition.wait()
        finally:
            self.__condition.release()

    def release(self):
        """Release the currently held lock.

        In case the current thread holds no lock, a ValueError is thrown."""

        me = current_thread()
        self.__condition.acquire()
        try:
            if self.__writer is me:
                # We are the writer, take one nesting depth away.
                self.__writercount -= 1
                if not self.__writercount:
                    # No more write locks; take our writer position away and
                    # notify waiters of the new circumstances.
                    self.__writer = None
                    self.__condition.notifyAll()
            elif me in self.__readers:
                # We are a reader currently, take one nesting depth away.
                self.__readers[me] -= 1
                if not self.__readers[me]:
                    # No more read locks, take our reader position away.
                    del self.__readers[me]
                    if not self.__readers:
                        # No more readers, notify waiters of the new
                        # circumstances.
                        self.__condition.notifyAll()
            else:
                raise ValueError("Trying to release unheld lock")
        finally:
            self.__condition.release()

    @property
    @contextmanager
    def readlock(self):
        self.acquireRead()
        try:
            yield
        finally:
            self.release()

    @property
    @contextmanager
    def writelock(self):
        self.acquireWrite()
        try:
            yield
        finally:
            self.release()
## end of http://code.activestate.com/recipes/502283/ }}}


class Future(object):
    def __init__(self, func, *args, **kwargs):
        self.__done = False
        self.__result = None
        self.__cond = Condition()
        self.__func = func
        self.__args = args
        self.__kwargs = kwargs
        self.__except = None

    def __call__(self):
        with self.__cond:
            try:
                self.__result = self.__func(*self.__args, **self.__kwargs)
            except:
                self.__result = None
                self.__except = sys.exc_info()
            self.__done = True
            self.__cond.notify()

    def result(self):
        with self.__cond:
            while not self.__done:
                self.__cond.wait()
        if self.__except:
            raise self.__except[0], self.__except[1], self.__except[2]
        result = copy.deepcopy(self.__result)
        return result


def generate_timestamp():
    return str(time())


class RenderedMarkupCacheEntry(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

    def __init__(self, timestamp=None, filename='', dirname='', html_part=''):
        timestamp = timestamp or generate_timestamp()
        for name, val in locals().iteritems():
            if name == 'self':
                continue
            self[name] = val
        self['__deepcopy__'] = self.__deepcopy__

    def __deepcopy__(self, memo={}):
        return self.copy()


@Singleton
class RenderedMarkupCache(object):
    def __init__(self):
        self.rwlock = RWLock()
        self.cache = {}

    def exists(self, buffer_id):
        with self.rwlock.readlock:
            return buffer_id in self.cache

    def get_entry(self, buffer_id):
        with self.rwlock.readlock:
            if buffer_id in self.cache:
                return self.cache[buffer_id]
        return None

    def set_entry(self, buffer_id, entry):
        with self.rwlock.writelock:
            self.cache[buffer_id] = entry

    def clean(self, keep_ids=set()):
        with self.rwlock.writelock:
            remove_ids = set(self.cache.keys())
            remove_ids -= keep_ids
            if len(remove_ids) == 0:
                return
            for buffer_id in remove_ids:
                del self.cache[buffer_id]
            log.info("Clean buffer ids in: %s" % list(remove_ids))
