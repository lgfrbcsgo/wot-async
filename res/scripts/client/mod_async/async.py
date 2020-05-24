import sys
from collections import deque
from functools import wraps

try:
    from debug_utils import LOG_CURRENT_EXCEPTION, LOG_WARNING
except ImportError:
    import traceback

    def LOG_CURRENT_EXCEPTION():
        traceback.print_exc()

    def LOG_WARNING(msg):
        print msg


class Return(StopIteration):
    def __init__(self, value):
        self.value = value


class CallbackCancelled(Exception):
    pass


def async_task(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        gen = func(*args, **kwargs)
        return TaskExecutor(gen)

    return wrapper


class TaskExecutor(object):
    def __init__(self, gen):
        self._gen = gen
        self._callback = None
        self._errback = None
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
        if not self._started:
            self._started = True
            self._callback = callback
            self._errback = errback
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
            self._callback(e.value)
        except StopIteration:
            self._completed = True
            self._callback(None)
        except Exception:
            self._completed = True
            self._errback(sys.exc_info())
        else:
            self._register_callbacks(executor)

    def _register_callbacks(self, executor):
        try:
            once = Once(self._send, self._throw)
            executor(once.callback, once.errback)
        except Exception:
            self._throw(sys.exc_info())


def run(executor):
    def callback(_):
        pass

    def errback(exc_info):
        exc_type, exc_value, exc_traceback = exc_info
        try:
            raise exc_type, exc_value, exc_traceback
        except Exception:
            LOG_CURRENT_EXCEPTION()

    return executor(callback, errback)


def auto_run(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        run(func(*args, **kwargs))

    return wrapper


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


def select(*executors):
    def select_executor(callback, errback):
        once = Once(callback, errback)
        for executor in executors:
            executor(once.callback, once.errback)

    return select_executor


class AsyncValue(object):
    def __init__(self):
        self._value_set = False
        self._value = None
        self._callbacks = []

    def __call__(self, callback, errback):
        if self._value_set:
            callback(self._value)
        else:
            self._callbacks.append(callback)

    def set(self, value=None):
        if not self._value_set:
            self._value_set = True
            self._value = value
            callbacks, self._callbacks = self._callbacks, []
            for callback in callbacks:
                callback(value)

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
            yield AsyncValue.of(None)
        else:
            result = AsyncValue()
            self._deferred.append(result)
            yield result


class AsyncMutex(AsyncSemaphore):
    def __init__(self):
        super(AsyncMutex, self).__init__(1)


def from_adisp(adisp_func):
    def executor(callback, errback):
        return adisp_func(callback)

    return executor


def from_future(future):
    def executor(callback, errback):
        def future_callback(result):
            try:
                value = result.get()
            except Exception:
                errback(sys.exc_info())
            else:
                callback(value)

        future.then(future_callback)

    return executor
