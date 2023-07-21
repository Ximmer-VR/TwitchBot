#!/usr/bin/env python3

__author__ = 'Ximmer'
__copyright__ = 'Copyright 2023, Ximmer'

import asyncio

from . import Gear
import random

# TODO: config system for notification sounds

class Notification(Gear):
    def __init__(self):
        super().__init__()

        self._subscribers = []
        self._followers = []

    @staticmethod
    def name():
        return 'AudioAlert'

    async def on_stream_live(self, live: bool) -> None:
        if live:
            self._subscribers = []
            self._followers = []
            await self.send_message('Stream is live')
        else:
            await self.send_message('Stream has ended')

    async def on_message(self, who: str, message: str, user_level: str, tags) -> None:
        if message == 'ping':
            await self.send_message('pong with space')
            color = random.choice(['blue', 'green', 'orange', 'purple', 'primary'])
            self.announce('pong {}'.format(color), color)

        if self.is_live():
            self.play_sound('MC_Menu_Cursor2')

    async def on_follow(self, who: str) -> None:
        if self.is_live():
            if who not in self._followers:
                self._followers.append(who)
                self.play_sound('OOT_GoldSkulltula_Token')
                await self.send_message('Thank you for following {}!'.format(who))

    async def on_subscribe(self, who: str, message: str, emotes) -> None:
        if self.is_live():
            if who not in self._subscribers:
                self._subscribers.append(who)
                self.play_sound('OOT_Fanfare_SmallItem')
                await self.send_message('Thank you for subscribing {}!'.format(who))

    async def on_raid(self, who: str, how_many: int) -> None:
        if how_many >= 3:
            await asyncio.sleep(2.0)
            await self.send_message('Thank you for the raid {}!'.format(who))
            await self.send_message('/shoutout {}'.format(who))




Export = Notification