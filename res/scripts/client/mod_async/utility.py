import BigWorld
from mod_async import AsyncResult, async_task


def delay(seconds):
    @AsyncResult.executor
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
