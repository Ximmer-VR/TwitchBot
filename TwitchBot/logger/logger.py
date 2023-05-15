#!/usr/bin/env python3

__author__ = 'Ximmer'
__copyright__ = 'Copyright 2023, Ximmer'

import datetime
import logging
import logging.handlers
import os
import re
import time
from logging.handlers import TimedRotatingFileHandler

from rich import console, print

os.makedirs('./logs', exist_ok=True)

# Timed file rotation
# NOTE: has issue with websockets causing unicode exceptions from debug printing
handler = TimedRotatingFileHandler('logs/bot.log', 'midnight', backupCount=10)
handler.namer = lambda name: name.replace('.log', '') + '.log'

logging.basicConfig(handlers=[handler], level=logging.DEBUG, format='%(name)25s - %(asctime)s [%(levelname)s] %(message)s')

_obfuscations = []

_default_colors = [
    '#CCFFFF',
    '#FFCCFF',
    '#FFFFCC',
    '#FFCCCC',
    '#CCFFCC',
    '#CCCCFF',
    '#CCFF00',
    '#00CCFF',
    '#FF00CC',
    '#CC00FF',
    '#FFCC00',
    '#00FFCC',
]
_next_color = 0

_bg = True

_log_spam = {}

class Logger(object):
    def __init__(self, name, name_color=None) -> None:
        global _next_color

        self._name = name

        if name_color is None:
            self._name_color = _default_colors[_next_color]
            _next_color = (_next_color + 1) % len(_default_colors)
        else:
            self._name_color = name_color

        self._log = logging.getLogger(str(name))

        self._console = console.Console()

    def _escape(self, msg):

        result = str(msg)
        result = result.replace('/[', chr(8))   # replace /[ with backspace
        result = result.replace('[', '\\[')     # escape [ for text
        result = result.replace(chr(8), '[')    # replace backspace with [

        return result

    def _clean(self, msg):
        result = str(msg)
        return re.sub(r'\/\[.*?\]', '', msg)

    def _obfuscate(self, msg):
        result = str(msg)
        for secret in _obfuscations:
            #skrt = secret[0:int(len(secret) / 8)] + '...' + secret[-int(len(secret) / 8):]
            skrt = '******'
            result = result.replace(secret, skrt)

        return result
    #
    # Utility
    #

    def obfuscate(self, secret):
        global _obfuscations

        if secret is None:
            return

        _obfuscations.append(secret[2:-2])

    def _now(self):
        return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def _bg(self):
        global _bg
        _bg = not _bg
        if _bg:
            return 'on #323232'
        return 'on'

    #
    # Logging Interface
    #

    _msg_format = '[{bg}]{when} - [{name_color}]{name:24s}[/] [{color}] {level:11s}[/] {msg}{padding}'

    def info(self, msg):
        msg = self._obfuscate(msg)
        self._log.info(self._clean(msg))
        padding = ' ' * (self._console.width - len(msg))
        print(self._msg_format.format(color='#B5CE89', level='[INFO]', when=self._now(), name_color=self._name_color, name=self._name, msg=self._escape(msg), bg=self._bg(), padding=padding))

    def debug(self, msg):
        msg = self._obfuscate(msg)
        self._log.debug(self._clean(msg))

        if len(_log_spam) > 50:
            cleaned = 0
            for spam in list(_log_spam.keys()):
                if time.time() - _log_spam[spam]['time'] > 60 * 10:
                    del _log_spam[spam]
                    cleaned += 1
            # self.debug('cleaned out {} log messages'.format(cleaned))

        if msg in _log_spam:
            msg_entry = _log_spam[msg]

            msg_entry['time'] = time.time()

            if msg_entry['count'] > 3:
                return

            msg_entry['count'] += 1
            if msg_entry['count'] > 3:
                self.warning('muting log message: {}'.format(msg))

        else:
            _log_spam[msg] = {
                'time': time.time(),
                'count': 1
            }
        padding = ' ' * (self._console.width - len(msg))
        print(self._msg_format.format(color='#358CD5', level='[DEBUG]', when=self._now(), name_color=self._name_color, name=self._name, msg=self._escape(msg), bg=self._bg(), padding=padding))

    def warning(self, msg):
        msg = self._obfuscate(msg)
        self._log.warning(self._clean(msg))
        padding = ' ' * (self._console.width - len(msg))
        print(self._msg_format.format(color='#FFA000', level='[WARNING]', when=self._now(), name_color=self._name_color, name=self._name, msg=self._escape(msg), bg=self._bg(), padding=padding))

    def error(self, msg):
        msg = self._obfuscate(msg)
        self._log.error(self._clean(msg))
        padding = ' ' * (self._console.width - len(msg))
        print(self._msg_format.format(color='#FF0000', level='[ERROR]', when=self._now(), name_color=self._name_color, name=self._name, msg=self._escape(msg), bg=self._bg(), padding=padding))

    def exception(self, ex):
        self._log.exception(ex)
        padding = ''
        print(self._msg_format.format(color='#FF0000', level='[EXCEPTION]', when=self._now(), name_color=self._name_color, name=self._name, msg=ex, bg=self._bg(), padding=padding))
