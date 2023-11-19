#!/usr/bin/env python3

__author__ = 'Ximmer'
__copyright__ = 'Copyright 2023, Ximmer'

from . import Gear
import asyncio
import time

class Chat(Gear):
    def __init__(self):
        super().__init__()

        self.chat = []

        with open('chat.md', 'w') as f:
            f.write(' ')

        self.next_delete = 0

    @staticmethod
    def name():
        return 'Chat'

    async def on_message(self, who: str, message: str, user_level: str, tags) -> None:

        if message.startswith('!'):
            return

        self.log_debug(tags)

        emotes = []

        for data in tags['emotes'].split('/'):
            if data == '':
                break
            emote, data = data.split(':')
            start, end = data.split('-')

            self.log_debug('{} {} {}'.format(emote, start, end))

            emotes.insert(0, {'id': emote, 'start': int(start), 'end': int(end)})

        # replace emotes starting from the back
        for emote in emotes:
            # https://static-cdn.jtvnw.net/emoticons/v2/<id>/<format>/<theme_mode>/<scale>
            #                                                default  light        1.0
            #                                                static   dark         2.0
            #                                                animated              3.0

            message = message[:emote['start']] + '![{}](https://static-cdn.jtvnw.net/emoticons/v2/{}/default/dark/2.0)'.format(message[emote['start']:emote['end'] + 1], emote['id']) + message[emote['end'] + 1:]

        self.chat.append('<span style="color:{}">{}</span>: {}'.format(tags['color'], tags['display-name'], message))

        if len(self.chat) > 10:
            self.chat = self.chat[1:]

        self.write_file()

        self.next_delete = time.time() + 10


    def write_file(self):
        with open('chat.md', 'w') as f:
            f.write('<span style="font: Fira">')
            f.write('\\\n'.join(self.chat))
            f.write('</span>')

    async def on_update(self) -> None:

        if time.time() - self.next_delete < 0:
            return
        self.next_delete = time.time() + 10

        if len(self.chat) == 0:
            return

        self.chat = self.chat[1:]

        self.write_file()

Export = Chat