import BigWorld
from mod_async import AsyncResult, async_task


def delay(seconds):
    with AsyncResult() as async_result:
        BigWorld.callback(seconds, async_result.resolve)
    return async_result


class TimeoutExpired(Exception):
    pass


def timeout(seconds, async_result):
    @async_task
    def raise_timeout():
        yield delay(seconds)
        raise TimeoutExpired()

    return AsyncResult.select(async_result, raise_timeout())
