import sys
from enum import IntEnum
from types import TracebackType
from typing import Any, Callable, Generic, List, Optional, Tuple, Type, TypeVar, Union

from debug_utils import LOG_CURRENT_EXCEPTION

T = TypeVar("T")
U = TypeVar("U")
Exc = Tuple[Type[BaseException], BaseException, Optional[TracebackType]]


class CallbackCancelled(Exception):
    pass


class AsyncResult(Generic[T]):
    class State(IntEnum):
        PENDING = 0
        OK = 1
        ERROR = 2

    def __init__(self):
        # type: () -> None

        self._state = self.State.PENDING  # type: int
        self._value = None  # type: Optional[T]
        self._exc_info = None  # type: Optional[Exc]
        self._exc_handled = False  # type: bool

        self._resolved_callbacks = []  # type: List[Callable[[T], Any]]
        self._rejected_callbacks = []  # type: List[Callable[[Exc], Any]]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if exc_traceback:
            self.reject((exc_type, exc_value, exc_traceback))
            return True

    def __del__(self):
        if self._state == self.State.ERROR and not self._exc_handled:
            try:
                exc_type, exc_value, exc_traceback = self._exc_info
                raise exc_type, exc_value, exc_traceback
            except Exception:
                LOG_CURRENT_EXCEPTION()
        elif self._state == self.State.PENDING:
            self.reject((CallbackCancelled, CallbackCancelled(), None))

    def and_then(self, func):
        # type: (Callable[[T], Union[AsyncResult[U], U]]) -> AsyncResult[U]
        with AsyncResult() as async_result:
            self._add_resolved_callback(
                self._and_callback(func, async_result.resolve, async_result.reject)
            )
            self._add_rejected_callback(async_result.reject)

        return async_result

    def and_error(self, func):
        # type: (Callable[[Exc], Union[AsyncResult[T], T]]) -> AsyncResult[T]
        with AsyncResult() as async_result:
            self._add_resolved_callback(async_result.resolve)
            self._add_rejected_callback(
                self._and_callback(func, async_result.resolve, async_result.reject)
            )
        return async_result

    @staticmethod
    def _and_callback(func, resolve, reject):
        def callback(value):
            try:
                next_result = func(value)
            except Exception:
                reject(sys.exc_info())
            else:
                if isinstance(next_result, AsyncResult):
                    next_result._add_resolved_callback(resolve)
                    next_result._add_rejected_callback(reject)
                else:
                    resolve(next_result)

        return callback

    def _add_resolved_callback(self, func):
        # type: (Callable[[T], Any]) -> None
        if self._state == self.State.OK:
            func(self._value)
        elif self._state == self.State.PENDING:
            self._resolved_callbacks.append(func)

    def _add_rejected_callback(self, func):
        # type: (Callable[[Exc], Any]) -> None
        self._exc_handled = True
        if self._state == self.State.ERROR:
            func(self._exc_info)
        elif self._state == self.State.PENDING:
            self._rejected_callbacks.append(func)

    def resolve(self, value=None):
        # type: (T) -> None
        if self._state == self.State.PENDING:
            self._state = self.State.OK
            self._value = value
            for callback in self._resolved_callbacks:
                callback(value)
            self._resolved_callbacks = []
            self._rejected_callbacks = []

    def reject(self, exc_info):
        # type: (Exc) -> None
        if self._state == self.State.PENDING:
            self._state = self.State.ERROR
            self._exc_info = exc_info
            for callback in self._rejected_callbacks:
                callback(exc_info)
            self._resolved_callbacks = []
            self._rejected_callbacks = []

    @staticmethod
    def from_adisp(caller):
        # type: (Callable[[Callable[[T], None]], None]) -> AsyncResult[T]
        with AsyncResult() as async_result:
            caller(async_result.resolve)

        return async_result

    @staticmethod
    def ok(value=None):
        # type: (T) -> AsyncResult[T]
        with AsyncResult() as async_result:
            async_result.resolve(value)
        return async_result

    @staticmethod
    def error(exc_info):
        # type: (Exc) -> AsyncResult[Any]
        with AsyncResult() as async_result:
            async_result.reject(exc_info)
        return async_result

    @staticmethod
    def select(*results):
        # type: (List[AsyncResult[T]]) -> AsyncResult[T]
        if len(results) == 0:
            return AsyncResult.ok(None)

        with AsyncResult() as selected_result:
            for result in results:
                result.and_then(selected_result.resolve).and_error(
                    selected_result.reject
                )

        return selected_result

    @staticmethod
    def all(*results):
        # type: (List[AsyncResult[T]]) -> AsyncResult[List[T]]
        return All(results).await_all()


class All(object):
    def __init__(self, results):
        # type: (List[AsyncResult[T]]) -> None
        self._resolved_values = [None] * len(results)
        self._pending = {
            index: result.and_then(lambda value: (index, value))
            for index, result in enumerate(results)
        }

    def await_all(self):
        # type: () -> AsyncResult[List[T]]
        return self._select()

    def _select(self, tagged_result=None):
        if tagged_result:
            index, value = tagged_result
            self._resolved_values[index] = value
            del self._pending[index]

        if len(self._pending) == 0:
            return AsyncResult.ok(self._resolved_values)
        else:
            return AsyncResult.select(self._pending.values()).and_then(self._select)
