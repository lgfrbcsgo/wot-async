import BigWorld
from Event import Event
from mod_async.async import AsyncValue, Return, async_task, select


def delay(seconds):
    value = AsyncValue()
    BigWorld.callback(seconds, value.set)
    return value


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
