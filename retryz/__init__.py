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
import functools
import inspect
import numbers
import threading
from threading import Thread

__author__ = 'Cedric Zhuang'


class RetryTimeoutError(Exception):
    pass


def retry(func=None, on_error=None, on_return=None,
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

    def is_function(f):
        return (inspect.ismethod(f) or
                inspect.isfunction(f) or
                isinstance(f, (classmethod, staticmethod)))

    def background(func_ref, *args, **kwargs):
        if not callable(func_ref):
            raise ValueError('background only accept callable inputs.')
        t = Thread(target=func_ref, args=args, kwargs=kwargs)
        t.setDaemon(True)
        t.start()
        return t

    def call(f, func_args, *args):
        try:
            ret = f(*args)
        except TypeError:
            inst = get_inst(func_args)
            ret = f(inst, *args)
        return ret

    def get_inst(args):
        if len(args) > 0:
            inst = args[0]
        else:
            inst = None
        return inst

    def check_return(args, r):
        ret = None
        if on_return:
            if is_function(on_return):
                ret = call(on_return, args, r)
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
                ret = call(on_error, args, err)
            else:
                ret = isinstance(err, on_error)

        if ret is None:
            ret = True

        return ret

    def get_limit(args):
        ret = None
        if limit is None:
            ret = float("inf")
        elif isinstance(limit, numbers.Number):
            ret = limit
        elif is_function(limit):
            ret = call(limit, args)

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
                ret = call(timeout, args)

        return ret

    def get_wait(args, retry_count):
        ret = None
        if wait is None or retry_count == 0:
            ret = 0
        elif isinstance(wait, numbers.Number):
            ret = wait
        elif is_function(wait):
            ret = call(wait, args, retry_count)

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
            call(on_retry, args)
        else:
            raise ValueError('on_retry should be a method accept two params:'
                             ' value, retry_count.')

    if func is not None:
        return retry(None,
                     on_error=on_error,
                     on_return=on_return,
                     limit=limit,
                     wait=wait,
                     timeout=timeout,
                     on_retry=on_retry)(func)

    # the event to break sleep when timeout
    event_holder = EventHolder()

    def decorator(function):
        @functools.wraps(function)
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
                    ret = function(*args, **kwargs)
                    need_retry = check_return(args, ret)
                    if tried >= max_try:
                        need_retry = False
                # noinspection PyBroadException
                except Exception as e:
                    need_retry = check_error(args, e)
                    if tried >= max_try or not need_retry:
                        event_holder.end_timeout_check_thread()
                        raise
            event_holder.end_timeout_check_thread()
            return ret

        return func_wrapper

    return decorator
