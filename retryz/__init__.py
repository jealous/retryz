import inspect
import numbers
import threading
from threading import Thread

__author__ = 'Cedric Zhuang'

__all__ = ('retry', 'RetryTimeoutError')


class RetryTimeoutError(Exception):
    pass


def is_function(func):
    return (inspect.ismethod(func) or
            inspect.isfunction(func) or
            isinstance(func, (classmethod, staticmethod)))


def retry(on_error=None, on_errors=None,
          unless_error=None, unless_errors=None,
          on_return=None, on_returns=None,
          unless_return=None, unless_returns=None,
          limit=None, wait=None, timeout=None, on_retry=None):
    def background(func_ref, *args, **kwargs):
        if not callable(func_ref):
            raise ValueError('background only accept callable inputs.')
        t = Thread(target=func_ref, args=args, kwargs=kwargs)
        t.setDaemon(True)
        t.start()
        return t

    def init_list(the_list, the_single):
        if the_list is None:
            the_list = []
        if the_single is not None and not is_function(the_single):
            the_list.append(the_single)
        return the_list

    def check_exclusive(list1, list2):
        if len(list1) and len(list2):
            raise ValueError('positive and negative criteria cannot be '
                             'specified at the same time.')

    def call(func, inst, *args):
        try:
            ret = func(*args)
        except TypeError:
            ret = func(inst, *args)
        return ret

    def check_return(args, r):
        ret = None
        if len(on_returns) > 0:
            ret = r in on_returns
        elif is_function(on_return):
            ret = call(on_return, args[0], r)
        if r in unless_returns:
            ret = False

        if ret is None:
            ret = not has_error_option()
        return ret

    def has_error_option():
        return on_errors or unless_errors or is_function(on_error)

    def check_error(args, err):
        ret = None
        if len(on_errors) > 0:
            ret = isinstance(err, tuple(on_errors))
        elif is_function(on_error):
            ret = call(on_error, args[0], err)

        if len(unless_errors) > 0:
            if ret is None:
                ret = True
            ret &= not isinstance(err, tuple(unless_errors))

        if ret is None:
            ret = True

        if not ret:
            raise err
        return ret

    # noinspection PyCallingNonCallable
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

    def on_timeout(evt_holder):
        evt_holder.bg_event = threading.Event()
        evt_holder.bg_event.wait(timeout)
        evt_holder.set_main_event()

    def call_retry_callback(args, retry_count):
        if on_retry is None or retry_count == 0:
            pass
        elif is_function(on_retry):
            call(on_retry, args[0])
        else:
            raise ValueError('on_retry should be a method accept two params:'
                             ' value, retry_count.')

    if limit is None:
        limit = float("inf")
    on_errors = init_list(on_errors, on_error)
    unless_errors = init_list(unless_errors, unless_error)
    check_exclusive(on_errors, unless_errors)

    on_returns = init_list(on_returns, on_return)
    unless_returns = init_list(unless_returns, unless_return)
    check_exclusive(on_returns, unless_returns)

    # the event to break sleep when timeout
    event_holder = EventHolder()

    def decorator(func):
        def func_wrapper(*args, **kwargs):
            if timeout is not None:
                background(on_timeout, event_holder)
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
                    if tried >= limit:
                        need_retry = False
                # noinspection PyBroadException
                except Exception as e:
                    need_retry = check_error(args, e)
                    if tried >= limit:
                        event_holder.end_timeout_check_thread()
                        raise e
            event_holder.end_timeout_check_thread()
            return ret

        return func_wrapper

    return decorator


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
