from collections import deque
from typing import Deque

import BigWorld
from mod_async.result import AsyncResult, CallbackCancelled
from mod_async.task import Return, async_task


def delay(seconds):
    @AsyncResult
    def async_result(resolve, _):
        BigWorld.callback(seconds, resolve)

    # ignore CallbackCancelled error
    return async_result.and_error(lambda exc: None)


class TimeoutExpired(Exception):
    pass


def timeout(seconds, async_result):
    @async_task
    def raise_timeout():
        yield delay(seconds)
        raise TimeoutExpired()

    return AsyncResult.select(async_result, raise_timeout())


class Deferred(object):
    def __init__(self):
        self._callback = None

        @AsyncResult
        def async_result(resolve, _):
            self._callback = resolve

        self._result = async_result

    def set(self, value=None):
        self._callback(value)

    @async_task
    def wait(self):
        yield self._result


class AsyncSemaphore(object):
    def __init__(self, value=1):
        # type: (int) -> None
        self._value = value
        self._deferred = deque()  # type: Deque[Deferred]

    def release(self):
        if len(self._deferred) == 0:
            self._value += 1
        else:
            deferred = self._deferred.popleft()
            deferred.set()

    def acquire(self):
        if self._value != 0:
            self._value -= 1
            return AsyncResult.ok()
        else:
            deferred = Deferred()
            self._deferred.append(deferred)
            return deferred.wait()
