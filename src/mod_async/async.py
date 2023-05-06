import sys
from collections import deque
from functools import wraps

from mod_async.logging import LOG_CURRENT_EXCEPTION, LOG_WARNING


class Once(object):
    def __init__(self, callback, errback):
        self._callback = callback
        self._errback = errback
        self._called = False

    def callback(self, value):
        if not self._called:
            self._called = True
            self._callback(value)

    def errback(self, exc_info):
        if not self._called:
            self._called = True
            self._errback(exc_info)


class Deferred(object):
    def __init__(self):
        self._called = False
        self._args = None
        self._kwargs = None
        self._callbacks = []

    def __len__(self):
        return len(self._callbacks)

    def call(self, *args, **kwargs):
        if not self._called:
            self._called = True
            self._args = args
            self._kwargs = kwargs

            callbacks, self._callbacks = self._callbacks, []
            for callback in callbacks:
                callback(*args, **kwargs)

    def defer(self, callback):
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
        self.run()

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
            if len(self._errbacks) == 0:
                LOG_WARNING("Task raised an unhandled exception.")
                LOG_CURRENT_EXCEPTION()

            self._completed = True
            self._errbacks.call(sys.exc_info())
        else:
            self._register_callbacks(executor)

    def _register_callbacks(self, executor):
        once = Once(self._send, self._throw)
        try:
            executor(once.callback, once.errback)
        except Exception:
            once.errback(sys.exc_info())


def async_task(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        gen = func(*args, **kwargs)
        return TaskExecutor(gen)

    return wrapper


def run(executor):
    executor.run()
    return executor


def auto_run(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        executor = func(*args, **kwargs)
        return run(executor)

    return wrapper


def select(*executors):
    def select_executor(callback, errback):
        once = Once(callback, errback)
        for executor in executors:
            executor(once.callback, once.errback)

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
