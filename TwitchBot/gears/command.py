#!/usr/bin/env python3

__author__ = 'Ximmer'
__copyright__ = 'Copyright 2023, Ximmer'

import asyncio
import time

from . import Gear


# Todo: config settings for timeouts and message counts
# Todo: add config system to base gear for configs

class Command(Gear):
    def __init__(self):
        super().__init__()

        self._commands = {}

        self._spam_count = 0
        self._spam_time = time.time() + 3600

        self._collab = None
        self._collab_count = 0
        self._collab_time = time.time() + 1800

    @staticmethod
    def name():
        return 'Command'

    async def on_start(self):
            cursor = self.db_cursor()
            cursor.execute("SELECT * FROM commands")
            rows = cursor.fetchall()

            # TODO: update data structure for spam
            for row in rows:
                 self._commands[row['command']] = {
                     'response': row['response'],
                     'spam' : bool(row['spam'])
                 }

                 self.log_info('loaded command {}'.format(row['command']))

    async def on_stream_live(self, live: bool):
        self._spam_count = 0
        self._spam_time = time.time() + 3600  # hour

    async def on_message(self, who: str, message: str, user_level: str, tags) -> None:

        self._spam_count += 1
        self._collab_count += 1

        if message.startswith('!cmd'):
            if user_level in ['mod', 'streamer']:
                args = message.strip().split(' ')
                if len(args) < 2:
                    await self.send_message('!cmd <add|del> <command> [response]')
                    return

                # TODO: add config stuff
                if args[1] == 'config':
                    # spam_time
                    # spam_messages
                    pass

                # TODO: add -spam flag
                # TODO: overwrite/delete old entries
                if args[1] == 'add':
                    if len(args) < 4:
                        await self.send_message('!cmd add <command> [-spam] <response>')
                        return
                    cmd = args[2]
                    response = ' '.join(args[3:])

                    cursor = self.db_cursor()
                    cursor.execute("INSERT INTO commands(command, response) VALUES(?, ?)", (cmd, response))
                    self.db_commit()
                    self._commands[cmd] = response

                    self.log_info('Command !{} with response \'{}\' added'.format(cmd, response))
                    await self.send_message('Command added.')
                    return

                if args[1] == 'del':
                    cmd = args[2]

                    if cmd in self._commands:

                        cursor.execute("DELETE FROM commands WHERE command=?", (cmd,))
                        self.db_commit()

                        self.log_info('command !{} deleted')
                        await self.send_message('Command deleted.')
                    else:
                        await self.send_message('Unknown command.')

                    return

            return

        if message.startswith('!list'):
            if user_level in ['mod', 'streamer']:
                cmds = 'command list: !cmd, !list'
                for cmd in self._commands:
                    cmds += ', !' + cmd

                await self.send_message(cmds)
            return

        if message.startswith('!collab'):
            if user_level in ['mod', 'streamer']:
                args = message.strip().split(' ')
                if len(args) == 1:
                    self._collab = None
                    await self.send_message('collab disabled')
                else:
                    self._collab = ' '.join(args[1:])
                    self.log_debug('collab message set to {}'.format(self._collab))
                    self._collab_count = 0
                    self._collab_time = 0

        if message.startswith('!') and len(message) > 1:
            args = message[1:].strip().split(' ')
            cmd = args[0]
            if cmd in self._commands:
                await self.send_message(self._commands[cmd])
            else:
                count = 0
                the_cmd = None
                for c in self._commands:
                    if c.startswith(cmd):
                        count += 1
                        the_cmd = c

                if count == 1:
                    await self.send_message(self._commands[the_cmd]['response'])

    async def on_update(self):

        # spam
        if self.is_live():

            if (self._collab_count >= 60 or time.time() > self._collab_time) and self._collab is not None:
                self._collab_count = 0
                self._collab_time = time.time() + 1800

            if self._spam_count >= 60 or time.time() > self._spam_time:
                self._spam_count = 0
                self._spam_time = time.time() + 3600

                for c in self._commands:
                    if self._commands[c]['spam']:
                        await self.send_message(self._commands[c]['response'])

Export = Command