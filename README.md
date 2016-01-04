# Retry Decorator

[![Build Status](https://travis-ci.org/jealous/retryz.svg?branch=master)](https://travis-ci.org/jealous/retryz)
[![Coverage Status](https://coveralls.io/repos/jealous/retryz/badge.svg?branch=master&service=github)](https://coveralls.io/github/jealous/retryz?branch=master)

## Introduction

Function decorator that helps to retry the function under certain criteria.

This package contains the `retry` decorator and a bunch of configuration 
parameters for this decorator. 

Tested on python 2.7 and python 3.4.

For quick start, check the tutorial section of this page.
Check [test_retryz.py](test/test_retryz.py) for detail examples.

## Installation

``pip install retryz``


## Tutorial

* Retry if `ValueError` is caught.

```python
@retry(on_error=ValueError)
def my_func():
    ...
```

* Retry if `ValueError` or `TypeError` is caught.

```python
@retry(on_errors=[ValueError, TypeError])
def my_func():
    ...
```

* Retry until `TypeError` is caught.

```python
@retry(unless_error=TypeError)
def my_func():
    ...
```

* Retry until `TypeError` or `AttributeError` is caught.

```python
@retry(unless_errors=[TypeError, AttributeError])
def my_func():
    ...
```

* When `on_error` is a callback, 
it will retry until `on_error` returns `False`.  Note that callback could be
a function or an instancemethod.  But it could not be a staticmethod or
class method.  It takes one parameter which is the error instance raised by
the decorated function.

```python
def _error_callback(self, ex):
    assert_that(ex, instance_of(TypeError))
    return self.call_count != 4

@retry(on_error=_error_callback)
def error_call_back(self):
    ...
```

* Retry if returns certain value.

```python
@retry(on_return=True)
def my_func(self):
    ...
```

* Retry if return value in the list.

```python
@retry(on_returns=[1, 2, 3, 4, 5])
def my_func(self):
    ...
```

* Retry until certain value is returned.

```python
@retry(unless_return=4)
def my_func(self):
    ...
```

* Retry until any of the value is returned.

```python
@retry(unless_returns=[3, 4])
def my_func(self):
    ...
```

* When `on_return` is a callback, 
it will retry until `on_return` returns `False`.  Note that callback could be
a function or an instancemethod.  But it could not be a staticmethod or
class method.  It takes one parameter which is the return value of the 
decorated function.

```python
def _return_callback(ret):
    return 4 + ret < 7

@retry(on_return=_return_callback)
def my_func(self):
    ...
```

* Retry until timeout (in seconds)

```python
@retry(timeout=0.1)
def my_func():
    ...
```

* Retry maximum X times.

```python
@retry(limit=3)
def my_func():
    ...
```

* Wait X seconds between each retry.

```python
@retry(wait=0.1, timeout=0.3)
def my_func():
    ...
```

* When `wait` is a callback, it will wait for the amount of
seconds returned by the callback.
The callback could be a function or a instance method.
It takes one parameter which is the current count of retry.

```python
def _wait_callback(self, tried):
    return 2 ** tried

@retry(wait=_wait_callback, timeout=0.1)
def my_func():
    ...
```
    

To file issue, please visit:

https://github.com/jealous/retryz


Contact author:

jealous@163.com