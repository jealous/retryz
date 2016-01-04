import inspect
import numbers
import threading
from threading import Thread

__author__ = 'Cedric Zhuang'
__version__ = '0.1.1'


class RetryTimeoutError(Exception):
    pass


def retry(on_error=None, on_errors=None,
          unless_error=None, unless_errors=None,
          on_return=None, on_returns=None,
          unless_return=None, unless_returns=None,
          limit=None, wait=None, timeout=None):
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
        if the_single is not None and not is_callback(the_single):
            the_list.append(the_single)
        return the_list

    def check_exclusive(list1, list2):
        if len(list1) and len(list2):
            raise ValueError('positive and negative criteria cannot be '
                             'specified at the same time.')

    def is_callback(func):
        return callable(func) and not isinstance(func, type)

    def check_return(r, inst=None):
        ret = None
        if len(on_returns) > 0:
            ret = r in on_returns
        if is_callback(on_return):
            if ret is None:
                ret = False
            if inst is not None and is_method(on_return):
                ret |= on_return(inst, r)
            else:
                ret |= on_return(r)
        if r in unless_returns:
            ret = False

        if ret is None:
            ret = not has_error_option()
        return ret

    def has_error_option():
        return on_errors or unless_errors or is_callback(on_error)

    def check_error(err, inst=None):
        ret = None
        if len(on_errors) > 0:
            ret = isinstance(err, tuple(on_errors))
        if is_callback(on_error):
            error_call_back = on_error
            if ret is None:
                ret = False
            if inst is not None and is_method(error_call_back):
                ret |= error_call_back(inst, err)
            else:
                ret |= error_call_back(err)
        if len(unless_errors) > 0:
            if ret is None:
                ret = True
            ret &= not isinstance(err, tuple(unless_errors))

        if ret is None:
            ret = True

        if not ret:
            raise err
        return ret

    def arg_length(f):
        arg_spec = inspect.getargspec(f)
        return len(arg_spec.args)

    def is_method(func=None):
        ret = False
        if func is None:
            if is_callback(on_error):
                ret |= arg_length(on_error) == 2
            if is_callback(on_return):
                ret |= arg_length(on_return) == 2
            if callable(wait):
                ret |= arg_length(wait) == 2
        else:
            ret = arg_length(func) == 2
        return ret

    # noinspection PyCallingNonCallable
    def get_wait(inst, retry_count):
        if wait is None or retry_count == 0:
            ret = 0
        elif isinstance(wait, numbers.Number):
            ret = wait
        elif callable(wait):
            if arg_length(wait) == 1:
                ret = wait(retry_count)
            elif arg_length(wait) == 2:
                ret = wait(inst, retry_count)
            else:
                raise ValueError('wait callback should have one param.')
        else:
            raise ValueError('wait should be a number or '
                             'a callback of try count.')
        return ret

    def on_timeout(evt_holder):
        evt_holder.bg_event = threading.Event()
        evt_holder.bg_event.wait(timeout)
        evt_holder.set_main_event()

    def get_inst(args):
        """ retrieve the `self` parameter of the callback

        :param args: arguments of the callback function
        :return: `self` argument of the method if callback is
                 a instance method.  Otherwise returns `None`.
        """
        if is_method():
            inst = args[0]
        else:
            inst = None
        return inst

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
            inst = get_inst(args)
            while need_retry:
                event_holder.check_timeout()
                to_wait = get_wait(inst, tried)
                if to_wait > 0:
                    if not event_holder.is_main_set():
                        event_holder.wait_main(to_wait)
                    event_holder.check_timeout()
                try:
                    tried += 1
                    ret = func(*args, **kwargs)
                    need_retry = check_return(ret, inst)
                    if tried >= limit:
                        need_retry = False
                # noinspection PyBroadException
                except Exception as e:
                    need_retry = check_error(e, inst)
                    if tried >= limit:
                        event_holder.end_timeout_check_thread()
                        raise e
            event_holder.end_timeout_check_thread()
            return ret

        return func_wrapper

    return decorator
