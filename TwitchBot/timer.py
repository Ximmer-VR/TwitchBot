#!/usr/bin/env python3

__author__ = 'Ximmer'
__copyright__ = 'Copyright 2023, Ximmer'

import time

class Timer(object):
    def __init__(self, interval_s, startup_s=None):
        self._time_start = time.time()
        self._interval = interval_s
        if startup_s is not None:
            self._time_start -= interval_s - startup_s

    def reset(self):
        self._time_start = time.time()

    def is_triggered(self):
        if time.time() - self._time_start > self._interval:
            self.reset()
            return True
        return False
