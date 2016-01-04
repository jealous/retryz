from unittest import TestCase

from hamcrest import assert_that, instance_of, equal_to, raises, greater_than, \
    less_than

from retryz import retry, RetryTimeoutError


def _return_callback(ret):
    return 4 + ret < 7


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

    @retry(on_errors=[ValueError, TypeError])
    def on_errors(self):
        self._call_count += 1
        if self.call_count == 1:
            raise ValueError()
        elif self.call_count == 2:
            raise TypeError()
        else:
            raise AttributeError()

    @retry(unless_error=TypeError)
    def unless_error(self):
        self._call_count += 1
        if self.call_count <= 2:
            raise ValueError()
        else:
            raise TypeError()

    @retry(unless_errors=[TypeError, AttributeError])
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

    @retry(timeout=0.05)
    def timeout(self):
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

    @retry(on_returns=[1, 2, 3, 4, 5])
    def on_returns(self):
        self._call_count += 1
        return self.call_count

    @retry(unless_return=4)
    def unless_return(self):
        self._call_count += 1
        return self.call_count

    @retry(unless_returns=[3, 4])
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
        try:
            demo.timeout()
        except RetryTimeoutError:
            assert_that(demo.call_count, greater_than(100))

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
