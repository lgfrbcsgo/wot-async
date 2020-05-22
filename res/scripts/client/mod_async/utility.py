import BigWorld
from mod_async import AsyncResult, CallbackCancelled, async_task


@async_task
def delay(seconds):
    with AsyncResult() as async_result:
        BigWorld.callback(seconds, async_result.resolve)

    try:
        yield async_result
    except CallbackCancelled:
        pass


class TimeoutExpired(Exception):
    pass


def timeout(seconds, async_result):
    @async_task
    def raise_timeout():
        yield delay(seconds)
        raise TimeoutExpired()

    return AsyncResult.select(async_result, raise_timeout())
