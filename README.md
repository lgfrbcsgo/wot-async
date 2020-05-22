# WoT Async
Library for asynchronous programming inside of WoT mods.

```python
from mod_async import async_task, delay, Return


@async_task
def wait(seconds):
    # delay execution by seconds
    yield delay(seconds)
    # return seconds in milliseconds
    raise Return(seconds * 1000)


@async_task
def main():
    milliseconds = yield wait(10)
    print "Waited for {} milliseconds.".format(milliseconds)


# start task `main`, does not block the thread
main()
```

## Working with callbacks
```python
from mod_async import async_task, AsyncResult


def multiply_callback(a, b, callback):
    # callback based function
    callback(a * b)


def multiply_async(a, b):
    # wrap function into AsyncResult
    # all errors raised within the with block are rerouted into the result
    with AsyncResult() as result:
        # pass result.resolve as callback to multiply_callback
        # result.reject can be used for errbacks
        multiply_callback(a, b, result.resolve)
    
    # return the as a normal value
    return result


@async_task
def main():
    # multiply_async can be called as an async function
    result = yield multiply_async(2, 42)
    # prints 84
    print result
```

## Calling `@adisp.async` functions
```python
import adisp
from mod_async import async_task, AsyncResult


@adisp.async
def multiply_adisp(a, b, callback):
    callback(a * b)


@async_task
def main():
    # wrap returned value into AsyncResult 
    result = yield AsyncResult.from_adisp(multiply_adisp(2, 42))
    # prints 84
    print result
```