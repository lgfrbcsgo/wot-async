import BigWorld
from mod_async.async import AsyncValue, async_task, select


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
