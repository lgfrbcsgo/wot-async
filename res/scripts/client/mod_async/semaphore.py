from collections import deque
from typing import Deque

from mod_async.result import AsyncResult


class AsyncSemaphore(object):
    def __init__(self, value=1):
        # type: (int) -> None
        self._value = value
        self._deferred = deque()  # type: Deque[AsyncResult]

    def release(self):
        if len(self._deferred) == 0:
            self._value += 1
        else:
            result = self._deferred.popleft()
            result.resolve()

    def acquire(self):
        if self._value != 0:
            self._value -= 1
            return AsyncResult.ok()
        else:
            result = AsyncResult()
            self._deferred.append(result)
            return result


class AsyncMutex(AsyncSemaphore):
    def __init__(self):
        super(AsyncMutex, self).__init__(1)
