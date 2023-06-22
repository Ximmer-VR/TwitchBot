#!/usr/bin/env python3

__author__ = 'Ximmer'
__copyright__ = 'Copyright 2023, Ximmer'

import asyncio

from . import Gear
import random

class Command(Gear):
    def __init__(self):
        super().__init__()

        self.commands = {}

    @staticmethod
    def name():
        return 'Command'

    async def on_start(self):
            cursor = self.db_cursor()
            cursor.execute("SELECT * FROM commands")
            rows = cursor.fetchall()

            for row in rows:
                 self.commands[row['command']] = row['response']
                 self.log_info('loaded command {}'.format(row['command']))

    async def on_message(self, who: str, message: str, user_level: str, tags) -> None:

        if message.startswith('!cmd'):
            if user_level in ['mod', 'streamer']:
                args = message.strip().split(' ')
                if len(args) < 2:
                    await self.send_message('!cmd <add|del> <command> [response]')
                    return

                if args[1] == 'add':
                    if len(args) < 4:
                        await self.send_message('!cmd add <command> <response>')
                        return
                    cmd = args[2]
                    response = ' '.join(args[3:])

                    cursor = self.db_cursor()
                    cursor.execute("INSERT INTO commands(command, response) VALUES(?, ?)", (cmd, response))
                    self.db_commit()
                    self.commands[cmd] = response

                    self.log_info('Command !{} with response \'{}\' added'.format(cmd, response))
                    await self.send_message('Command added.')
                    return

                if args[1] == 'del':
                    cmd = args[2]

                    if cmd in self.commands:

                        cursor.execute("DELETE FROM commands WHERE command=?", (cmd,))
                        self.db_commit()

                        self.log_info('command !{} deleted')
                        await self.send_message('Command deleted.')
                    else:
                        await self.send_message('Unknown command.')

                    return

            return


        if message.startswith('!') and len(message) > 1:
            args = message[1:].strip().split(' ')
            cmd = args[0]
            if cmd in self.commands:
                await self.send_message(self.commands[cmd])
            else:
                #todo: find best matching non-ambiguos command
                pass




        # if message == 'ping':
        #     await self.send_message('pong with space')
        #     color = random.choice(['blue', 'green', 'orange', 'purple', 'primary'])
        #     self.announce('pong {}'.format(color), color)

Export = Command