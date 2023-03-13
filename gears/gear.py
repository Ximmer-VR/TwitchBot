#!/usr/bin/env python3

__author__ = 'Ximmer'
__copyright__ = 'Copyright 2023, Ximmer'

import importlib
import os

from rich import print

import logger
import abc

_log = logger.Logger(__name__)

class Gear(metaclass=abc.ABCMeta):
    def __init__(self):
        self._bot = None
        self._log = logger.Logger('gears.' + self.name())

    async def start(self, bot):
        self._bot = bot
        await self.on_start()

    #
    # Logging
    #

    def log_debug(self, msg):
        self._log.debug(msg)

    def log_info(self, msg):
        self._log.info(msg)

    def log_warning(self, msg):
        self._log.warning(msg)

    def log_error(self, msg):
        self._log.error(msg)

    def log_exception(self, msg):
        self._log.exception(msg)

    #
    # api
    #

    def db_cursor(self):
        return self._bot.db_conn.cursor()

    def db_commit(self):
        self._bot.db_conn.commit()

    async def send_message(self, message):
        await self._bot.send_message(message)

    def ban(self, who, reason) -> None:
        self._bot.api_ban(who, reason)

    def timeout(self, who, reason, duration) -> None:
        self._bot.api_timeout(who, reason, duration)

    # colors: blue, green, orange, purple, primary
    def announce(self, message, color = None) -> None:
        self._bot.api_announce(message, color)

    def is_live(self) -> bool:
        return self._bot.is_live()

    def get_chat_users(self) -> list:
        return self._bot.get_chat_users()

    def login_to_userid(self, login) -> int:
        return self._bot.get_userid_from_login(login)

    #
    # interface
    #

    @abc.abstractstaticmethod
    def name() -> str:
        return 'Unnamed Gear'

    async def on_start(self) -> None:
        pass

    async def on_update(self) -> None:
        pass

    async def on_stream_live(self, live: bool) -> None:
        pass

    async def on_connect(self) -> None:
        pass

    async def on_join(self, who: str) -> None:
        pass

    async def on_message(self, who: str, message: str, user_level: str, tags) -> None:
        '''user_level: [user|mod|streamer]'''
        pass

    async def on_follow(self, who: str) -> None:
        pass

    async def on_subscribe(self, who: str, message: str, emotes) -> None:
        pass

    async def on_redeem(self, who: str, redeem: str) -> None:
        pass

    async def on_cheer(self, who: str, bits: int, message: str) -> None:
        pass

    async def on_raid(self, who: str, how_many: int) -> None:
        pass

def _load(path, module = ''):

    cmd_list = []

    for cmd in os.listdir(path):
        cmd_name, cmd_ext = os.path.splitext(cmd)

        cmd_path = os.path.join(path, cmd)

        if os.path.isdir(cmd_path):
            if not cmd.startswith('_'):
                cmd_list.extend(_load(cmd_path, module + cmd))

        if (cmd_ext == '.py' or cmd_ext == '.pyc') and not cmd.startswith('_') and cmd_name != 'gear':
            cmd_list.append([cmd_name, module])

    return cmd_list

MODULE_LIST = {}
GEAR_LIST = {}

def load(path = 'gears'):

    global MODULE_LIST
    global GEAR_LIST

    cmd_list = _load(path, 'gears')

    _log.info('loading gears...')

    for cmd in cmd_list:
        try:
            reloading = False
            module = cmd[1] + '.' + cmd[0]
            if module in MODULE_LIST:
                reloading = True
                mod = importlib.reload(MODULE_LIST[module])
            else:
                mod = importlib.import_module(module)

            MODULE_LIST[module] = mod

            if 'Export' in dir(mod):
                gear = mod.Export()

                if module in GEAR_LIST:
                    del GEAR_LIST[module]
                GEAR_LIST[module] = gear

                _log.info('{} {}.{}: /[#80FF80]OK '.format('reloading' if reloading else 'loading', cmd[1], cmd[0]))
            else:
                _log.info('{} {}.{}: /[#FFA000]No Export '.format('reloading' if reloading else 'loading', cmd[1], cmd[0]))
        except Exception as ex:
            _log.info('{} {}.{}: /[red]Failed '.format('reloading' if reloading else 'loading', cmd[1], cmd[0]))
            _log.exception(ex)

    return GEAR_LIST.values()