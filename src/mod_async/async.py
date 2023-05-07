import sys
from collections import deque
from functools import wraps

from mod_async.logging import LOG_WARNING, LOG_CURRENT_EXCEPTION


class Once(object):
    def __init__(self, callback, errback):
        self._callback = callback
        self._errback = errback
        self._called = False

    def callback(self, *args, **kwargs):
        if not self._called:
            self._called = True
            self._callback(*args, **kwargs)

    def errback(self, *args, **kwargs):
        if not self._called:
            self._called = True
            self._errback(*args, **kwargs)


class Deferred(object):
    def __init__(self):
        self._called = False
        self._args = None
        self._kwargs = None
        self._callback_count = 0
        self._callbacks = []

    def __len__(self):
        return self._callback_count

    def call(self, *args, **kwargs):
        if not self._called:
            self._called = True
            self._args = args
            self._kwargs = kwargs

            callbacks, self._callbacks = self._callbacks, []
            for callback in callbacks:
                try:
                    callback(*args, **kwargs)
                except Exception:
                    LOG_WARNING("Unhandled exception.")
                    LOG_CURRENT_EXCEPTION()

    def defer(self, callback):
        self._callback_count += 1
        if self._called:
            callback(*self._args, **self._kwargs)
        else:
            self._callbacks.append(callback)


class Return(StopIteration):
    def __init__(self, *args):
        if len(args) == 0:
            self.value = None
        elif len(args) == 1:
            self.value = args[0]
        else:
            self.value = args


class CallbackCancelled(Exception):
    pass


class TaskExecutor(object):
    def __init__(self, gen):
        self._gen = gen
        self._callbacks = Deferred()
        self._errbacks = Deferred()
        self._started = False
        self._completed = False

    def __del__(self):
        if not self._started:
            LOG_WARNING("Task hasn't been started.")
        elif not self._completed:
            try:
                raise CallbackCancelled()
            except CallbackCancelled:
                self._throw(sys.exc_info())

    def __call__(self, callback, errback):
        self._callbacks.defer(callback)
        self._errbacks.defer(errback)

    def run(self):
        if not self._started:
            self._started = True
            self._send(None)

    def _send(self, value):
        self._step(self._gen.send, value)

    def _throw(self, exc_info):
        self._step(self._gen.throw, *exc_info)

    def _step(self, gen_op, *values):
        try:
            executor = gen_op(*values)
        except Return as e:
            self._completed = True
            self._callbacks.call(e.value)
        except StopIteration:
            self._completed = True
            self._callbacks.call(None)
        except Exception:
            self._completed = True
            self._errbacks.call(sys.exc_info())
            if len(self._errbacks) == 0:
                raise
        else:
            once = Once(self._send, self._throw)
            executor(once.callback, once.errback)


def async_task(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        gen = func(*args, **kwargs)
        executor = TaskExecutor(gen)
        executor.run()
        return executor

    return wrapper


def select(*executors):
    callbacks = Deferred()
    errbacks = Deferred()
    once = Once(callbacks.call, errbacks.call)

    for executor in executors:
        executor(once.callback, once.errback)

    def select_executor(callback, errback):
        callbacks.defer(callback)
        errbacks.defer(errback)

    return select_executor


class AsyncValue(object):
    def __init__(self):
        self._callbacks = Deferred()

    def __call__(self, callback, _errback):
        self._callbacks.defer(callback)

    def set(self, value=None):
        self._callbacks.call(value)

    @staticmethod
    def of(value):
        async_value = AsyncValue()
        async_value.set(value)
        return async_value


class AsyncSemaphore(object):
    def __init__(self, value=1):
        self._value = value
        self._deferred = deque()

    def release(self):
        if len(self._deferred) == 0:
            self._value += 1
        else:
            result = self._deferred.popleft()
            result.set()

    @async_task
    def acquire(self):
        if self._value != 0:
            self._value -= 1
        else:
            result = AsyncValue()
            self._deferred.append(result)
            yield result


class AsyncMutex(AsyncSemaphore):
    def __init__(self):
        super(AsyncMutex, self).__init__(1)
