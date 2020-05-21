from collections import deque
from typing import Callable, Deque

import BigWorld
from mod_async.result import AsyncResult
from mod_async.task import Return, async_task


def delay(seconds):
    @AsyncResult
    def async_result(resolve, _):
        BigWorld.callback(seconds, resolve)

    return async_result


class TimeoutExpired(Exception):
    pass


def timeout(seconds, async_result):
    @async_task
    def raise_timeout():
        yield delay(seconds)
        raise TimeoutExpired()

    return AsyncResult.select(async_result, raise_timeout())


class AsyncSemaphore(object):
    def __init__(self, value=1):
        # type: (int) -> None
        self._value = value
        self._callbacks = deque()  # type: Deque[Callable[[], None]]

    def release(self):
        if len(self._callbacks) == 0:
            self._value += 1
        else:
            callback = self._callbacks.popleft()
            callback()

    def acquire(self):
        if self._value != 0:
            self._value -= 1
            return AsyncResult.ok()
        else:

            @AsyncResult
            def async_result(resolve, _):
                self._callbacks.append(resolve)

            return async_result
