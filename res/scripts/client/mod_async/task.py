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
        return TaskExecutor(gen).run()

    return wrapper


class TaskExecutor(object):
    def __init__(self, gen):
        self._result = None
        self._gen = gen

    def run(self):
        if not self._result:
            self._result = self._await(AsyncResult.ok(None))
        return self._result

    def _await(self, async_result):
        if not isinstance(async_result, AsyncResult):
            async_result = AsyncResult.ok(async_result)

        return async_result.and_then(self._send).and_error(self._throw)

    def _step(self, func, *args):
        try:
            async_result = func(*args)
        except Return as r:
            return AsyncResult.ok(r.value)
        except StopIteration:
            return AsyncResult.ok(None)
        else:
            return self._await(async_result)

    def _throw(self, exc_info):
        return self._step(self._gen.throw, *exc_info)

    def _send(self, value):
        return self._step(self._gen.send, value)
