#!/usr/bin/env python3

__author__ = 'Ximmer'
__copyright__ = 'Copyright 2023, Ximmer'

import sqlite3
import time
import asyncio
import requests

from . import Gear

#                 S    M    H
UPDATE_PERIOD_S = 60 * 60 * 24
BAN_REASON = 'known bot account.'

class BotMurder(Gear):
    def __init__(self):
        super().__init__()

    @staticmethod
    def name():
        return 'BanBots'

    async def on_start(self) -> None:
        try:
            cursor = self.db_cursor()
            cursor.execute("SELECT * FROM config WHERE key='bots_last_updated'")
            row = cursor.fetchone()

            if row is None or time.time() > float(row['value']) + UPDATE_PERIOD_S:
                self.log_info('bot list out of date')
                asyncio.create_task(self.update_bots())

        except sqlite3.Error as ex:
            self.log_exception(ex)

    async def update_bots(self):

        self.log_debug('downloading bot list')
        response = requests.get('https://api.twitchinsights.net/v1/bots/all')

        if response.status_code == 200:
            json = response.json()

            data = []
            for bot in json['bots']:
                # 0=username, 1=live_in_channels, 2=last_seen(unix timestamp?)
                data.append((bot[0], bot[1], bot[2]))

            try:
                cursor = self.db_cursor()
                cursor.executemany('INSERT OR REPLACE INTO bots (username, live_in, last_seen) VALUES (?, ?, ?)', data)
                self.db_commit()
            except sqlite3.Error as ex:
                self.log_exception(ex)
        else:
            self.log_warning('downloading bot list failed {}'.format(response.status_code))

        try:
            cursor = self.db_cursor()
            cursor.execute('INSERT OR REPLACE INTO config(key, value) VALUES(?, ?)', ('bots_last_updated', time.time(),))
            self.db_commit()
        except sqlite3.Error as ex:
            self.log_exception(ex)

    async def on_update(self) -> None:
        pass

    async def on_join(self, who: str) -> None:
        try:
            cursor = self.db_cursor()
            cursor.execute('SELECT * FROM bots WHERE username=?', (who,))
            row = cursor.fetchone()
            if row is not None:
                self._log.info('banning known bot {}'.format(who))
                self.ban(who, 'registered bot')
        except sqlite3.Error as ex:
            self.log_exception(ex)

Export = BotMurder