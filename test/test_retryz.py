# coding=utf-8
# Copyright (c) 2015 EMC Corporation.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
from unittest import TestCase

from hamcrest import assert_that, instance_of, equal_to, raises, \
    greater_than, less_than, contains_string

from retryz import retry, RetryTimeoutError


def _return_callback(ret):
    return 4 + ret < 7


def func_wait_callback(tried):
    if tried <= 6:
        ret = 0.01
    else:
        ret = 1000
    return ret


class AnotherDemoClass(object):
    def __init__(self):
        self.a = 0

    @classmethod
    def class_wait_callback(cls, tried):
        if tried <= 3:
            ret = 0.01
        else:
            ret = 1000
        return ret

    @staticmethod
    def static_wait_callback(tried):
        if tried <= 4:
            ret = 0.01
        else:
            ret = 1000
        return ret

    def other_method_wait_callback(self, tried):
        self.a += 1
        if tried <= 2:
            ret = 0.01
        else:
            ret = 1000
        return ret


class RetryDemo(object):
    def __init__(self):
        self._call_count = 0

    @property
    def call_count(self):
        return self._call_count

    @retry(on_error=ValueError)
    def on_error(self):
        self._call_count += 1
        if self.call_count <= 3:
            raise ValueError()
        else:
            return self.call_count

    @retry(on_error=lambda e: isinstance(e, (ValueError, TypeError)))
    def on_errors(self):
        self._call_count += 1
        if self.call_count == 1:
            raise ValueError()
        elif self.call_count == 2:
            raise TypeError()
        else:
            raise AttributeError()

    @retry(on_error=lambda e: not isinstance(e, TypeError))
    def unless_error(self):
        self._call_count += 1
        if self.call_count <= 2:
            raise ValueError()
        else:
            raise TypeError()

    @retry(on_error=lambda e: not isinstance(e, (TypeError, AttributeError)))
    def unless_errors(self):
        self._call_count += 1
        if self.call_count == 1:
            raise ValueError()
        elif self.call_count == 2:
            raise TypeError()
        else:
            raise AttributeError()

    def _error_callback(self, ex):
        assert_that(ex, instance_of(TypeError))
        return self.call_count != 4

    @retry(on_error=_error_callback)
    def error_callback(self):
        self._call_count += 1
        raise TypeError()

    @retry(timeout=0.05, wait=lambda x: 0 if x < 5 else 100)
    def timeout(self):
        self._call_count += 1
        return self.call_count

    @retry(timeout=lambda: 0.05, wait=lambda x: 0 if x < 6 else 100)
    def timeout_callback(self):
        self._call_count += 1
        return self.call_count

    @retry(on_return=True)
    def on_return(self):
        self._call_count += 1
        if self.call_count < 3:
            ret = True
        else:
            ret = False
        return ret

    @retry(on_return=lambda x: x in (1, 2, 3, 4, 5))
    def on_returns(self):
        self._call_count += 1
        return self.call_count

    @retry(on_return=lambda x: x != 4)
    def unless_return(self):
        self._call_count += 1
        return self.call_count

    @retry(on_return=lambda x: x not in [3, 4])
    def unless_returns(self):
        self._call_count += 1
        return self.call_count

    @retry(on_return=_return_callback)
    def return_callback(self):
        self._call_count += 1
        return self.call_count

    @retry(limit=3)
    def limit(self):
        self._call_count += 1
        return self.call_count

    @retry(wait=0.1, timeout=0.3)
    def wait(self):
        self._call_count += 1
        return self.call_count

    def _wait_callback(self, tried):
        if tried <= 2 or self.call_count <= 5:
            ret = 0.01
        else:
            ret = 1000
        return ret

    @retry(wait=_wait_callback, timeout=0.1)
    def wait_callback(self):
        self._call_count += 1
        return self.call_count

    @retry(wait=AnotherDemoClass.class_wait_callback, timeout=0.1)
    def class_wait_callback(self):
        self._call_count += 1
        return self.call_count

    @retry(wait=AnotherDemoClass.static_wait_callback, timeout=0.1)
    def static_wait_callback(self):
        self._call_count += 1
        return self.call_count

    @retry(wait=func_wait_callback, timeout=0.1)
    def func_wait_callback(self):
        self._call_count += 1
        return self.call_count

    @retry(wait=AnotherDemoClass().other_method_wait_callback, timeout=0.1)
    def other_method_wait_callback(self):
        self._call_count += 1
        return self.call_count

    def _on_retry(self):
        self._call_count += 1

    @retry(on_retry=_on_retry, limit=3)
    def on_retry(self):
        """ doc string for on retry

        :return: call count
        """
        self._call_count += 1
        return self.call_count

    @retry(limit=lambda: 3)
    def limit_callback(self):
        self._call_count += 1
        return self.call_count

    @retry(on_error=ValueError)
    def unexpected_error(self):
        raise AttributeError('unexpected attribute error.')

    @retry(on_error=ValueError, wait=15, timeout=60 * 60 * 24 * 7)
    def same_function(self):
        self._call_count += 1
        return self._call_count

    def call(self):
        self._call_count += 1
        return self._call_count


class RetryTest(TestCase):
    def test_on_error(self):
        demo = RetryDemo()
        demo.on_error()
        assert_that(demo.call_count, equal_to(4))

    def test_on_errors_and_limit(self):
        demo = RetryDemo()
        assert_that(demo.on_errors, raises(AttributeError))
        assert_that(demo.call_count, equal_to(3))

    def test_unless_error(self):
        demo = RetryDemo()
        assert_that(demo.unless_error, raises(TypeError))
        assert_that(demo.call_count, equal_to(3))

    def test_unless_errors(self):
        demo = RetryDemo()
        assert_that(demo.unless_errors, raises(TypeError))
        assert_that(demo.call_count, equal_to(2))

    def test_error_callback(self):
        demo = RetryDemo()
        assert_that(demo.error_callback, raises(TypeError))
        assert_that(demo.call_count, equal_to(4))

    def test_timeout(self):
        demo = RetryDemo()
        assert_that(demo.timeout, raises(RetryTimeoutError))
        assert_that(demo.call_count, equal_to(5))

    def test_timeout_callback(self):
        demo = RetryDemo()
        assert_that(demo.timeout_callback, raises(RetryTimeoutError))
        assert_that(demo.call_count, equal_to(6))

    def test_on_return(self):
        demo = RetryDemo()
        assert_that(demo.on_return(), equal_to(False))
        assert_that(demo.call_count, equal_to(3))

    def test_on_returns(self):
        demo = RetryDemo()
        assert_that(demo.on_returns(), equal_to(6))

    def test_unless_return(self):
        demo = RetryDemo()
        assert_that(demo.unless_return(), equal_to(4))

    def test_unless_returns(self):
        demo = RetryDemo()
        assert_that(demo.unless_returns(), equal_to(3))

    def test_return_callback(self):
        demo = RetryDemo()
        assert_that(demo.return_callback(), equal_to(3))

    def test_limit(self):
        demo = RetryDemo()
        assert_that(demo.limit(), equal_to(3))

    def test_wait(self):
        demo = RetryDemo()
        assert_that(demo.wait, raises(RetryTimeoutError))
        assert_that(demo.call_count, greater_than(2))
        assert_that(demo.call_count, less_than(6))

    def test_wait_callback(self):
        demo = RetryDemo()
        assert_that(demo.wait_callback, raises(RetryTimeoutError))
        assert_that(demo.call_count, equal_to(6))

    def test_func_wait_callback(self):
        demo = RetryDemo()
        assert_that(demo.func_wait_callback, raises(RetryTimeoutError))
        assert_that(demo.call_count, equal_to(7))

    def test_class_wait_callback(self):
        demo = RetryDemo()
        assert_that(demo.class_wait_callback, raises(RetryTimeoutError))
        assert_that(demo.call_count, equal_to(4))

    def test_static_wait_callback(self):
        demo = RetryDemo()
        assert_that(demo.static_wait_callback, raises(RetryTimeoutError))
        assert_that(demo.call_count, equal_to(5))

    def test_other_method_wait_callback(self):
        demo = RetryDemo()
        assert_that(demo.other_method_wait_callback, raises(RetryTimeoutError))
        assert_that(demo.call_count, equal_to(3))

    def test_on_retry(self):
        demo = RetryDemo()
        assert_that(demo.on_retry(), equal_to(5))

    def test_limit_callback(self):
        demo = RetryDemo()
        assert_that(demo.limit_callback(), equal_to(3))

    def test_unexpected_error(self):
        demo = RetryDemo()
        assert_that(demo.unexpected_error,
                    raises(AttributeError, 'unexpected'))

    def test_functional_limit(self):
        demo = RetryDemo()
        assert_that(retry(demo.call, limit=3)(), equal_to(3))

    def test_functional_on_return(self):
        demo = RetryDemo()
        assert_that(retry(demo.call, on_return=lambda x: x < 5)(), equal_to(5))

    def test_function_wrap(self):
        demo = RetryDemo()
        assert_that(demo.on_retry.__doc__,
                    contains_string('doc string for on retry'))

    def test_same_function_first_entry(self):
        demo = RetryDemo()
        assert_that(demo.same_function(), equal_to(1))

    def test_same_function_second_entry(self):
        demo = RetryDemo()
        assert_that(demo.same_function(), equal_to(1))

    def test_error_wait_type(self):
        def f():
            @retry(wait='string')
            def g():
                pass

            g()

        assert_that(f, raises(ValueError, 'should be a number or a callback'))

    def test_retry_retry_type(self):
        def f():
            @retry(on_retry=123)
            def g():
                pass

            g()

        assert_that(f, raises(ValueError, 'should be a function'))
