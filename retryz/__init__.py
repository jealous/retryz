import inspect
import numbers
import threading
from threading import Thread

__author__ = 'Cedric Zhuang'


class RetryTimeoutError(Exception):
    pass


def retry(on_error=None, on_return=None,
          limit=None, wait=None, timeout=None, on_retry=None):
    class EventHolder(object):
        def __init__(self):
            self.main_event = threading.Event()
            self.bg_event = None

        def wait_main(self, seconds):
            self.main_event.wait(seconds)

        def set_main_event(self):
            self.main_event.set()

        def set_bg_event(self):
            if self.bg_event is not None:
                self.bg_event.set()

        def is_main_set(self):
            return self.main_event.is_set()

        def is_bg_set(self):
            ret = True
            if self.bg_event is not None:
                ret = self.bg_event.is_set()
            return ret

        def end_timeout_check_thread(self):
            self.set_bg_event()

        def check_timeout(self):
            if self.is_main_set():
                raise RetryTimeoutError('retry timeout.')

    def is_function(func):
        return (inspect.ismethod(func) or
                inspect.isfunction(func) or
                isinstance(func, (classmethod, staticmethod)))

    def background(func_ref, *args, **kwargs):
        if not callable(func_ref):
            raise ValueError('background only accept callable inputs.')
        t = Thread(target=func_ref, args=args, kwargs=kwargs)
        t.setDaemon(True)
        t.start()
        return t

    def call(func, inst, *args):
        try:
            ret = func(*args)
        except TypeError:
            ret = func(inst, *args)
        return ret

    def check_return(args, r):
        ret = None
        if on_return:
            if is_function(on_return):
                ret = call(on_return, args[0], r)
            else:
                ret = r == on_return

        if ret is None:
            ret = not has_error_option()
        return ret

    def has_error_option():
        return on_error is not None

    def check_error(args, err):
        ret = None
        if on_error:
            if is_function(on_error):
                ret = call(on_error, args[0], err)
            else:
                ret = isinstance(err, on_error)

        if ret is None:
            ret = True

        if not ret:
            raise err
        return ret

    def get_limit(args):
        ret = None
        if limit is None:
            ret = float("inf")
        elif isinstance(limit, numbers.Number):
            ret = limit
        elif is_function(limit):
            ret = call(limit, args[0])

        if ret is None:
            raise ValueError('limit should be a number of'
                             'a callback with no parameter.')
        return ret

    def get_timeout(args):
        ret = None
        if timeout is not None:
            if isinstance(timeout, numbers.Number):
                ret = timeout
            elif is_function(timeout):
                ret = call(timeout, args[0])

        return ret

    def get_wait(args, retry_count):
        ret = None
        if wait is None or retry_count == 0:
            ret = 0
        elif isinstance(wait, numbers.Number):
            ret = wait
        elif is_function(wait):
            ret = call(wait, args[0], retry_count)

        if ret is None:
            raise ValueError('wait should be a number or '
                             'a callback of try count.')
        return ret

    def on_timeout(evt_holder, args):
        evt_holder.bg_event = threading.Event()
        evt_holder.bg_event.wait(get_timeout(args))
        evt_holder.set_main_event()

    def call_retry_callback(args, retry_count):
        if on_retry is None or retry_count == 0:
            pass
        elif is_function(on_retry):
            call(on_retry, args[0])
        else:
            raise ValueError('on_retry should be a method accept two params:'
                             ' value, retry_count.')

    # the event to break sleep when timeout
    event_holder = EventHolder()

    def decorator(func):
        def func_wrapper(*args, **kwargs):
            max_try = get_limit(args)
            if timeout is not None:
                background(on_timeout, event_holder, args)
            need_retry = True
            tried = 0
            ret = None
            while need_retry:
                event_holder.check_timeout()
                to_wait = get_wait(args, tried)
                if to_wait > 0:
                    if not event_holder.is_main_set():
                        event_holder.wait_main(to_wait)
                    event_holder.check_timeout()

                call_retry_callback(args, tried)
                try:
                    tried += 1
                    ret = func(*args, **kwargs)
                    need_retry = check_return(args, ret)
                    if tried >= max_try:
                        need_retry = False
                # noinspection PyBroadException
                except Exception as e:
                    need_retry = check_error(args, e)
                    if tried >= max_try:
                        event_holder.end_timeout_check_thread()
                        raise e
            event_holder.end_timeout_check_thread()
            return ret

        return func_wrapper

    return decorator
