# WoT Async
Library to make asynchronous programming easier for WoT mods.

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
from mod_async import async_task, AsyncValue


def multiply_callback(a, b, callback):
    # callback based function
    callback(a * b)


def multiply_async(a, b):
    result = AsyncValue()
    multiply_callback(a, b, result.set)
    return result


@async_task
def main():
    # multiply_async can be called as an async function
    result = yield multiply_async(2, 42)
    # prints 84
    print result


# start task `main`, does not block the thread
main()
```

## Calling `@adisp.async` functions
```python
import adisp
from mod_async import async_task, from_adisp


@adisp.async
def multiply_adisp(a, b, callback):
    callback(a * b)


@async_task
def main():
    # wrap returned value into AsyncResult 
    result = yield from_adisp(multiply_adisp(2, 42))
    # prints 84
    print result


# start task `main`, does not block the thread
main()
```

## Calling functions which return a future
```python
from async import async
from BWUtil import AsyncReturn
from mod_async import async_task, from_future


@async
def multiply_future(a, b):
    if False:
        # @async functions need to be generators
        # just ignore this yield statement
        yield  
    raise AsyncReturn(a * b)


@async_task
def main():
    # wrap returned value into AsyncResult 
    result = yield from_future(multiply_future(2, 42))
    # prints 84
    print result


# start task `main`, does not block the thread
main()
```