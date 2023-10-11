#!/usr/bin/env python3

__author__ = 'Ximmer'
__copyright__ = 'Copyright 2023, Ximmer'

from . import Gear
import sqlite3
import asyncio

class Points(Gear):
    def __init__(self):
        super().__init__()

    @staticmethod
    def name():
        return 'Points'

    async def on_start(self) -> None:
        self.create_task(self._run())

    async def _run(self):
        while True:
            await asyncio.sleep(60)
            if self.is_live():
                self.add_points_all()

    def add_points_all(self):

        message = 'added 1 point for: '

        users = self.get_chat_users()

        for user in users:
            message += user + ', '
            user_id = self.login_to_userid(user)

            if user_id is not None:
                self.add_points(user_id, 1)

        self.log_info(message)

    def add_points(self, user_id, points):
        cursor = self.db_cursor()

        try:
            cursor.execute('INSERT INTO points(user_id) VALUES(?) ON CONFLICT(user_id) DO UPDATE SET points=points+?', (user_id, points))
            self.db_commit()
        except sqlite3.Error as ex:
            self._log.exception(ex)

Export = Points