import sys
from enum import IntEnum
from types import TracebackType
from typing import Any, Callable, Generic, List, Optional, Tuple, Type, TypeVar, Union

from debug_utils import LOG_CURRENT_EXCEPTION

T = TypeVar("T")
U = TypeVar("U")
Exc = Tuple[Type[BaseException], BaseException, TracebackType]


class CallbackCancelled(Exception):
    pass


class AsyncResultState(IntEnum):
    PENDING = 0
    OK = 1
    ERROR = 2


class AsyncResult(Generic[T]):
    def __init__(self, func):
        # type: (Callable[[Callable[[T], None], Callable[[Union[Exc, BaseException]], None]], None]) -> None

        self._state = AsyncResultState.PENDING  # type: int
        self._value = None  # type: Optional[T]
        self._exc_info = None  # type: Optional[Exc]
        self._exc_handled = False  # type: bool

        self._resolved_callbacks = []  # type: List[Callable[[T], Any]]
        self._rejected_callbacks = []  # type: List[Callable[[Exc], Any]]

        try:
            func(self._resolve, self._reject)
        except Exception:
            self._reject(sys.exc_info())

    def __del__(self):
        if self._state == AsyncResultState.ERROR and not self._exc_handled:
            try:
                exc_type, exc_value, exc_traceback = self._exc_info
                raise exc_type, exc_value, exc_traceback
            except Exception:
                LOG_CURRENT_EXCEPTION()
        elif self._state == AsyncResultState.PENDING:
            self._reject(CallbackCancelled())

    def and_then(self, func):
        # type: (Callable[[T], AsyncResult[U]]) -> AsyncResult[U]
        @AsyncResult
        def async_result(resolve, reject):
            def on_value(value):
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

            self._add_resolved_callback(on_value)
            self._add_rejected_callback(reject)

        return async_result

    def and_error(self, func):
        # type: (Callable[[Exc], AsyncResult[T]]) -> AsyncResult[T]
        @AsyncResult
        def async_result(resolve, reject):
            def on_error(value):
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

            self._add_resolved_callback(resolve)
            self._add_rejected_callback(on_error)

        return async_result

    def _add_resolved_callback(self, func):
        # type: (Callable[[T], Any]) -> None
        if self._state == AsyncResultState.OK:
            func(self._value)
        elif self._state == AsyncResultState.PENDING:
            self._resolved_callbacks.append(func)

    def _add_rejected_callback(self, func):
        # type: (Callable[[Exc], Any]) -> None
        self._exc_handled = True
        if self._state == AsyncResultState.ERROR:
            func(self._exc_info)
        elif self._state == AsyncResultState.PENDING:
            self._rejected_callbacks.append(func)

    def _resolve(self, value=None):
        # type: (T) -> None
        if self._state == AsyncResultState.PENDING:
            self._state = AsyncResultState.OK
            self._value = value
            for callback in self._resolved_callbacks:
                callback(value)
            self._resolved_callbacks = []

    def _reject(self, exc_info):
        # type: (Union[Exc, BaseException]) -> None
        if self._state == AsyncResultState.PENDING:
            self._state = AsyncResultState.ERROR
            if not isinstance(exc_info, tuple):
                exc_info = get_stacktrace(exc_info)

            self._exc_info = exc_info
            for callback in self._rejected_callbacks:
                callback(exc_info)
            self._rejected_callbacks = []

    @staticmethod
    def ok(value=None):
        # type: (T) -> AsyncResult[T]
        @AsyncResult
        def async_result(resolve, _):
            resolve(value)

        return async_result

    @staticmethod
    def error(exc_info):
        # type: (Union[Exc, BaseException]) -> AsyncResult[Any]
        @AsyncResult
        def async_result(_, reject):
            reject(exc_info)

        return async_result

    @staticmethod
    def select(*results):
        # type: (List[AsyncResult[T]]) -> AsyncResult[T]
        if len(results) == 0:
            return AsyncResult.ok(None)

        @AsyncResult
        def async_result(resolve, reject):
            for result in results:
                result.and_then(resolve).and_error(reject)

        return async_result

    @staticmethod
    def all(*results):
        # type: (List[AsyncResult[T]]) -> AsyncResult[List[T]]
        return All(results)()


class All(object):
    def __init__(self, results):
        # type: (List[AsyncResult[T]]) -> None
        self._resolved_values = [None] * len(results)
        self._pending = {
            index: result.and_then(lambda value: (index, value))
            for index, result in enumerate(results)
        }

    def __call__(self):
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


def get_stacktrace(exc):
    try:
        raise exc
    except Exception:
        return sys.exc_info()
