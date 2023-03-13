#! /usr/bin/env python3

__author__ = 'Ximmer'
__copyright__ = 'Copyright 2023, Ximmer'

import asyncio

import websockets

import logger


class Irc(object):

    on_welcome = None
    on_message = None
    on_join = None

    def __init__(self, username, password):
        self._log = logger.Logger(__class__.__name__)

        self._server = None
        self._username = username
        self._password = password
        self._channel = None

        self._users = []

        self._socket = None
        self._shutdown = False

    async def connect(self, address):
        self._shutdown = False
        self._server = address

        # create a socket data receiver
        loop = asyncio.get_event_loop()
        loop.create_task(self._handle(), name='Irc')

    async def close(self):
        self._shutdown = True
        await self._socket.close()

    async def join(self, channel):
        self._channel = channel
        await self._send('JOIN {}'.format(channel))

    def get_users(self):
        return self._users

    def _parse_ident(self, ident):
        nick_user, host = ident.split('@')
        user, nick = nick_user.split('!')
        return [nick, user, host]

    def _parse_tags(self, tags):

        results = {}

        for tag in tags.strip('@').split(';'):
            key, value = tag.split('=')
            if value.isdigit():
                value = int(value)
            results[key] = value

        self._log.debug(results)
        return results

    async def _irc_message(self, message):

        self._log.debug('< {}'.format(message))

        # handle the oddball server messages
        if message.startswith('PING'):
            await self._send('PONG {}'.format(message[5:]))
            return

        if message[0] == ':':
            message = ' ' + message

        # handle regular irc message
        t = message.split(' :')

        tags = t[0]
        cmd = t[1]
        data = t[2] if len(t) > 2 else ''

        parts = cmd.split(' ')

        if len(parts) >= 3:
            ident = parts[0]
            command = parts[1]
            channel = parts[2]

            if command == 'JOIN':
                if self.on_join is not None:
                    nick, user, host = self._parse_ident(ident)
                    self._users.append(nick)
                    asyncio.create_task(self.on_join(nick))
                    return

            if command == 'PART':
                nick, user, host = self._parse_ident(ident)
                self._users.remove(nick)
                return

            if command == 'PRIVMSG':
                if self.on_message is not None:
                    nick, user, host = self._parse_ident(ident)
                    tags = self._parse_tags(tags)
                    asyncio.create_task(self.on_message(nick, data, tags))
                    return

            # welcome message
            if command == '001':
                if self.on_welcome is not None:
                    asyncio.create_task(self.on_welcome())
                    return

            # names list
            if command == '353':
                return

    async def _handle(self):

        async for self._socket in websockets.connect(self._server):
            try:
                await self._on_connect()

                data_buffer = str()

                while True:
                    data = await self._socket.recv()
                    data_buffer += data

                    while '\r\n' in data_buffer:
                        offset = data_buffer.find('\r\n')
                        line = data_buffer[:offset]
                        data_buffer = data_buffer[offset + 2:]

                        await self._irc_message(line)
            except websockets.ConnectionClosed:
                if self._shutdown:
                    break
                continue

        self._socket = None

    async def _send(self, line):
        if line.upper().startswith('PASS'):
            self._log.debug('> PASS ******')
        else:
            self._log.debug('> {}'.format(line))
        await self._socket.send('{}'.format(line))

    async def send_message(self, message):
        await self._send('PRIVMSG {} :{}'.format(self._channel, message))

    async def _on_connect(self):
        await self._send('CAP LS')
        await self._send('PASS {}'.format(self._password))
        await self._send('NICK {}'.format(self._username))
        await self._send('CAP REQ :twitch.tv/commands')
        await self._send('CAP REQ :twitch.tv/membership')
        await self._send('CAP REQ :twitch.tv/tags')
