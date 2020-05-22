import sys
from functools import wraps

from mod_async.result import AsyncResult


class Return(StopIteration):
    def __init__(self, value):
        super(Return, self).__init__()
        self.value = value


def async_task(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        gen = func(*args, **kwargs)
        return AsyncTaskExecutor(gen).run()

    return wrapper


class AsyncTaskExecutor(object):
    def __init__(self, gen):
        self._result = AsyncResult()
        self._gen = gen
        self._started = False

    def run(self):
        if not self._started:
            self._started = True
            self._await(AsyncResult.ok())
        return self._result

    def _await(self, async_result):
        if not isinstance(async_result, AsyncResult):
            async_result = AsyncResult.ok(async_result)

        async_result.and_then(self._send).and_error(self._throw)

    def _step(self, func, *args):
        try:
            async_result = func(*args)
        except Return as r:
            self._result.resolve(r.value)
        except StopIteration:
            self._result.resolve()
        except Exception:
            self._result.reject(sys.exc_info())
        else:
            self._await(async_result)

    def _throw(self, exc_info):
        self._step(self._gen.throw, *exc_info)

    def _send(self, value):
        self._step(self._gen.send, value)
