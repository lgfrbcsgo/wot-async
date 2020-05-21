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
`AsyncResults` allow you to work with callback based APIs. The API is similar to [JS Promises](https://developer.mozilla.org/de/docs/Web/JavaScript/Reference/Global_Objects/Promise).

`AsyncResults` can be awaited using `yield` inside of functions marked with `@async_task`.