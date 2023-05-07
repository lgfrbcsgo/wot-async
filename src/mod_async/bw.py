import sys

import BigWorld
from Event import Event
from mod_async.async import AsyncValue, Return, async_task, select, Deferred


def delay(seconds):
    async_value = AsyncValue()
    BigWorld.callback(seconds, async_value.set)
    return async_value


class TimeoutExpired(Exception):
    pass


def timeout(seconds, async_result):
    @async_task
    def raise_timeout():
        yield delay(seconds)
        raise TimeoutExpired()

    return select(async_result, raise_timeout())


@async_task
def await_event(event):
    # type: (Event) -> ...
    async_value = AsyncValue()

    def handler(*args, **kwargs):
        async_value.set((args, kwargs))

    event += handler
    try:
        value = yield async_value
        raise Return(value)
    finally:
        event -= handler


def from_adisp(adisp_func):
    async_value = AsyncValue()
    adisp_func(async_value.set)
    return async_value


def from_future(future):
    callbacks = Deferred()
    errbacks = Deferred()

    def future_callback(result):
        try:
            value = result.get()
        except Exception:
            errbacks.call(sys.exc_info())
        else:
            callbacks.call(value)

    future.then(future_callback)

    def executor(callback, errback):
        callbacks.defer(callback)
        errbacks.defer(errback)

    return executor
