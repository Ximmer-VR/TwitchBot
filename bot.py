#! /usr/bin/env python3

__author__ = 'Ximmer'
__copyright__ = 'Copyright 2023, Ximmer'

# python3 -m pip install python-dotenv irc requests

# https://dev.twitch.tv/docs/api/reference/

# BOT_IRC_AUTH_TOKEN
# https://id.twitch.tv/oauth2/authorize?response_type=token&client_id=235jhq1ycndshpkl23mjwstlyx6a5u&redirect_uri=https://localhost&scope=chat:read chat:edit channel:read:redemptions channel:read:subscriptions moderator:manage:banned_users moderator:read:followers channel:moderate
# code for irc

# AUTH_CODE
# https://id.twitch.tv/oauth2/authorize?response_type=code&client_id=235jhq1ycndshpkl23mjwstlyx6a5u&redirect_uri=https://localhost&scope=channel:moderate+channel:read:redemptions+channel:read:subscriptions+moderator:manage:banned_users+moderator:read:followers+channel:moderate
# get code from result url and place into .env AUTH_CODE
#https://id.twitch.tv/oauth2/authorize?response_type=code&client_id=235jhq1ycndshpkl23mjwstlyx6a5u&redirect_uri=https://localhost&scope=analytics:read:extensions+analytics:read:games+bits:read+channel:edit:commercial+channel:manage:broadcast+channel:manage:extensions+channel:manage:moderators+channel:manage:polls+channel:manage:predictions+channel:manage:raids+channel:manage:redemptions+channel:manage:schedule+channel:manage:videos+channel:manage:vips+channel:moderate+channel:read:charity+channel:read:editors+channel:read:goals+channel:read:hype_train+channel:read:polls+channel:read:predictions+channel:read:redemptions+channel:read:stream_key+channel:read:subscriptions+channel:read:vips+chat:edit+chat:read+clips:edit+moderation:read+moderator:manage:announcements+moderator:manage:automod+moderator:manage:automod_settings+moderator:manage:banned_users+moderator:manage:blocked_terms+moderator:manage:chat_messages+moderator:manage:chat_settings+moderator:manage:shield_mode+moderator:manage:shoutouts+moderator:read:automod_settings+moderator:read:blocked_terms+moderator:read:chat_settings+moderator:read:chatters+moderator:read:followers+moderator:read:shield_mode+moderator:read:shoutouts+user:edit+user:edit:follows+user:manage:blocked_users+user:manage:chat_color+user:manage:whispers+user:read:blocked_users+user:read:broadcast+user:read:email+user:read:follows+user:read:subscriptions+whispers:edit+whispers:read


import asyncio
import json
import sqlite3

import requests
import websockets
import websockets.exceptions
from dotenv import dotenv_values

import auth
import gears
import irc
import logger
from timer import Timer


class TwitchBot(object):
    def __init__(self):

        self._log = logger.Logger(__class__.__name__)

        # Load Config
        self.config = dotenv_values('.env')

        self._log.obfuscate(self.config['CLIENT_ID'])
        self._log.obfuscate(self.config['CLIENT_SECRET'])
        self._log.obfuscate(self.config['BOT_IRC_AUTH_TOKEN'])
        self._log.obfuscate(self.config['BOT_CODE'])
        self._log.obfuscate(self.config['STREAM_CODE'])

        self._bot_token = auth.Token('bot', self.config['CLIENT_ID'], self.config['CLIENT_SECRET'], self.config['BOT_CODE'])
        self._stream_token = auth.Token('stream', self.config['CLIENT_ID'], self.config['CLIENT_SECRET'], self.config['STREAM_CODE'])

        # Setup DB
        self._log.info('connecting to database...')

        try:
            self.db_conn = sqlite3.connect(self.config['DB'])
            self.db_conn.row_factory = sqlite3.Row
        except sqlite3.Error as ex:
            self._log.error('error connecting to database.')
            self._log.exception(ex)
            exit()

        self.setup_db()


        # Live State
        self._is_live = None

        # Active Users
        self._cached_login_to_id = {}
        self._cached_id_to_login = {}
        self._unknown_users = []
        self._user_update_timer = Timer(1)

        # WebSocket
        self._socket = None

        # Gears
        self._gears = []

        # Connect to Twitch

        self._channel = '#{}'.format(self.config['STREAM_USER'].lower())

        self._irc = irc.Irc(self.config['BOT_USERNAME'], 'oauth:{}'.format(self.config['BOT_IRC_AUTH_TOKEN']))
        self._irc.on_welcome = self.on_welcome
        self._irc.on_message = self.on_message
        self._irc.on_join = self.on_join

    async def start(self):
        await self.load_gears()
        await self._irc.connect('wss://irc-ws.chat.twitch.tv:443')
        self.create_task(self.eventsub_loop(), name='EventSub')
        self.create_task(self.timer_loop(), name='Timer')

    def create_task(self, task: asyncio.coroutine, name=None):
        asyncio.create_task(self._exception_wrapper(task), name=name)

    async def _exception_wrapper(self, functor: asyncio.coroutine):
        try:
            await functor
        except Exception as ex:
            self._log.exception(ex)


    def api_request_get(self, url, token):

        headers = {
            'Client-ID': self.config['CLIENT_ID'],
            'Authorization': 'Bearer ' + token.get(),
            'Accept': 'application/vnd.twitchtv.v5+json',
        }

        self._log.debug('api request: {}'.format(url))
        self._log.debug('headers: {}'.format(headers))

        try:
            response = requests.get(url, headers=headers).json()
        except ConnectionError as ex:
            self._log.exception(ex)
            return None

        return response

    def api_request_post(self, url, data, token):

        if not isinstance(data, str):
            data = json.dumps(data)

        headers = {
            'Client-ID': self.config['CLIENT_ID'],
            'Authorization': 'Bearer ' + token.get(),
            'Content-Type': 'application/json',
        }

        self._log.debug('api request post: {}'.format(url))
        self._log.debug('headers: {}'.format(headers))

        try:
            response = requests.post(url, data=data, headers=headers)
            if response.status_code != 204:
                response = response.json()
            else:
                response = {}
        except ConnectionError as ex:
            self._log.exception(ex)
            return None

        return response

    # requires moderator:manage:banned_users
    def api_ban(self, who, reason):

        url = 'https://api.twitch.tv/helix/moderation/bans?broadcaster_id={}&moderator_id={}'.format(self.get_userid_from_login(self.config['STREAM_USER']), self.get_userid_from_login(self.config['BOT_USER']))
        data = {
            'data': {
                'user_id': self.get_userid_from_login(who),
                'reason': reason
            }
        }

        result = self.api_request_post(url, data, self._bot_token)

        if 'error' in result:
            self._log.error('error banning {}'.format(who))

        self._log.debug(result)

    # requires moderator:manage:banned_users
    def api_timeout(self, who, reason, duration):

        url = 'https://api.twitch.tv/helix/moderation/bans?broadcaster_id={}&moderator_id={}'.format(self.get_userid_from_login(self.config['STREAM_USER']), self.get_userid_from_login(self.config['BOT_USER']))
        data = {
            'data': {
                'user_id': self.get_userid_from_login(who),
                'duration': duration,
                'reason': reason
            }
        }

        result = self.api_request_post(url, data, self._bot_token)

        if 'error' in result:
            self._log.error('error timing out {}'.format(who))

        self._log.debug(result)

    # requires moderator:manage:announcements
    # colors: blue, green, orange, purple, primary
    def api_announce(self, message, color = None):

        url = 'https://api.twitch.tv/helix/chat/announcements?broadcaster_id={}&moderator_id={}'.format(self.get_userid_from_login(self.config['STREAM_USER']), self.get_userid_from_login(self.config['BOT_USER']))
        data = {
            'message': message
        }

        if color is not None:
            data['color'] = color

        result = self.api_request_post(url, data, self._bot_token)

        if 'error' in result:
            self._log.error('error sending announcement {}'.format(message))
            self._log.error(result)


    def setup_db(self):
        try:
            cursor = self.db_conn.cursor()

            with open('tables.sql') as fp:
                text = fp.read()
                cursor.executescript(text)

        except sqlite3.Error as ex:
            self._log.exception(ex)

    async def on_welcome(self):
        self._log.info('joining {}'.format(self._channel))
        await self._irc.join(self._channel)

        self._log.info('{} has successfully joined {}'.format(self.config['BOT_USERNAME'], self._channel))

    async def on_message(self, who, message, tags):

        self._log.info('/[#FFA000]Chat/[/]: /[{}]{}/[/] - {}'.format(tags['color'], who, message))

        for gear in self._gears:
            #tags = self.tags(event['event'])
            user_level = 'user'
            if tags['mod'] != 0:
                user_level = 'mod'
            if tags['display-name'].lower() == self.config['STREAM_USER']:
                user_level = 'streamer'

            await gear.on_message(who, message, user_level, tags)

        # TODO: move functionality to gear?
        try:
            cursor = self.db_conn.cursor()
            cursor.execute('INSERT INTO chat_log(display_name, user_id, tags, message) VALUES(?, ?, ?, ?)', (tags['display-name'], tags['user-id'], json.dumps(tags), message))
            self.db_conn.commit()
        except sqlite3.Error as ex:
            self._log.exception(ex)

    async def send_message(self, message):
        self._log.info('send_message(\'{}\')'.format(message))
        await self._irc.send_message(message)

    async def on_join(self, who):
        for gear in self._gears:
            self.create_task(gear.on_join(who))

    def is_live(self):

        if self._is_live is not None:
            return self._is_live

# {'data': [], 'pagination': {}}
#            'game_name': 'VRChat',
#            'id': '43093526477',
#            'is_mature': False,
#            'language': 'en',
#            'started_at': '2021-08-01T23:36:01Z',
#            'tag_ids': ['6ea6bca4-4712-4ab9-a906-e3336a9d8039',
#                        '52d7e4cc-633d-46f5-818c-bb59102d9549',
#                        '6606e54c-f92d-40f6-8257-74977889ccdd',
#                        '8bbdb07d-df18-4f82-a928-04a9003e9a7e'],
#            'thumbnail_url': 'https://static-cdn.jtvnw.net/previews-ttv/live_user_ximmer_vr_-{width}x{height}.jpg',
#            'title': '...',
#            'type': 'live',
#            'user_id': '218191839',
#            'user_login': 'ximmer_vr',
#            'user_name': 'Ximmer_VR',
#            'viewer_count': 205}],
#  'pagination': {}}

        self._log.debug('checking live status')
        data = self.api_request_get('https://api.twitch.tv/helix/streams?user_login={}'.format(self.config['STREAM_USER']), self._bot_token)

        if data is not None:
            if len(data['data']) != 0:
                self._log.info('Stream is Live')
                self._is_live = True
                return True

        self._log.info('Stream is Not Live')
        self._is_live = False
        return False

    def get_userid_from_login(self, login):

        if login in self._cached_login_to_id:
            return self._cached_login_to_id[login]

        try:
            cursor = self.db_conn.cursor()
            cursor.execute('SELECT * FROM users WHERE login=?', (login,))
            row = cursor.fetchone()
            if row is None:
                self._log.warning('unknown user: {}'.format(login))
                self._unknown_users.append(login)
            else:
                self._cached_login_to_id[login] = row['id']
                self._cached_id_to_login[row['id']] = login
                return row['id']
        except sqlite3.Error as ex:
            self._log.exception(ex)

        return None

    def get_login_from_userid(self, id):

        if id in self._cached_id_to_login:
            return self._cached_id_to_login[id]

        try:
            cursor = self.db_conn.cursor()
            cursor.execute('SELECT * FROM users WHERE id=?', (id,))
            row = cursor.fetchone()
            if row is not None:
                self._cached_id_to_login[id] = row['login']
                self._cached_login_to_id[row['login']] = id
                return row['login']
        except sqlite3.Error as ex:
            self._log.exception(ex)

        return None

    def get_chat_users(self):
        return self._irc.get_users()

    def update_users(self):
        if len(self._unknown_users) == 0:
            return

        url = 'https://api.twitch.tv/helix/users?'

        logins = []

        unknowns = self._unknown_users.copy()

        while len(unknowns) > 0 and len(logins) < 75:
            user = unknowns.pop()
            logins.append(user)

        for login in logins:
            url += 'login={}&'.format(login)

        self._log.debug('updating users')
        response = self.api_request_get(url, self._bot_token)

        if response is None:
            self._log.warning('error updating users')
            return

# {'data': [{'broadcaster_type': '',
#            'created_at': '2021-04-20T21:38:52.572299Z',
#            'description': 'Beep Boop',
#            'display_name': 'XimmerBot',
#            'id': '678229757',
#            'login': 'ximmerbot',
#            'offline_image_url': '',
#            'profile_image_url': 'https://static-cdn.jtvnw.net/jtv_user_pictures/3b32dbbc-0486-4723-89b4-d7a5279d77e4-profile_image-300x300.png',
#            'type': '',
#            'view_count': 0}]}

        cursor = self.db_conn.cursor()
        for user in response['data']:
            cursor.execute(
                '''INSERT INTO users(id, broadcaster_type, description, display_name, login, offline_image_url, profile_image_url, type, view_count, created_at) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET broadcaster_type=excluded.broadcaster_type, description=excluded.description, display_name=excluded.display_name, login=excluded.login, offline_image_url=excluded.offline_image_url, profile_image_url=excluded.profile_image_url, type=excluded.type, view_count=excluded.view_count, created_at=excluded.created_at''',
                (
                    user['id'],
                    user['broadcaster_type'],
                    user['description'],
                    user['display_name'],
                    user['login'],
                    user['offline_image_url'],
                    user['profile_image_url'],
                    user['type'],
                    user['view_count'],
                    user['created_at'],
                )
            )

        self.db_conn.commit()

        self._unknown_users = unknowns

    async def timer_loop(self):
        while True:
            await asyncio.sleep(1)

            for gear in self._gears:
                self.create_task(gear.on_update())

            # process user update
            if self._user_update_timer.is_triggered():
                self.update_users()

    async def _subscribe(self, event_type, token):

        self._log.info('subscribing to {}'.format(event_type))

        if event_type == 'channel.raid':
            data = {
                "type": event_type,
                "version":"1",
                "condition":
                {
                    "to_broadcaster_user_id": str(self.get_userid_from_login(self.config['STREAM_USER']))
                },
                "transport":
                {
                    "method":"websocket",
                    "session_id": self._session_id
                }
            }
        elif event_type == 'channel.follow':
            data = {
                "type": event_type,
                "version":"2",
                "condition":
                {
                    "broadcaster_user_id": str(self.get_userid_from_login(self.config['STREAM_USER'])),
                    "moderator_user_id": str(self.get_userid_from_login(self.config['STREAM_USER']))
                },
                "transport":
                {
                    "method":"websocket",
                    "session_id": self._session_id
                }
            }
        else:
            data = {
                "type": event_type,
                "version":"1",
                "condition":
                {
                    "broadcaster_user_id": str(self.get_userid_from_login(self.config['STREAM_USER']))
                },
                "transport":
                {
                    "method":"websocket",
                    "session_id": self._session_id
                }
            }


        json_data = json.dumps(data)

        self._log.debug('request: {}'.format(json_data))

        url = 'https://api.twitch.tv/helix/eventsub/subscriptions'

        result = self.api_request_post(url, data, token)

        if self.get_val(result, 'error') is not None:
            self._log.error('error subscribing to an event')
            self._log.error('result: {}'.format(result))
        else:
            self._log.debug('result: {}'.format(result))

    async def _on_session_welcome(self, meta, payload):
        self._session_id = payload['session']['id']
        self._log.obfuscate(self._session_id)
        self._keep_alive_timeout_s = payload['session']['keepalive_timeout_seconds']

        asyncio.create_task(self._subscribe('channel.follow', self._stream_token))
        asyncio.create_task(self._subscribe('channel.subscribe', self._stream_token))
        asyncio.create_task(self._subscribe('channel.subscription.gift', self._stream_token))
        asyncio.create_task(self._subscribe('channel.subscription.message', self._stream_token))
        asyncio.create_task(self._subscribe('channel.raid', self._stream_token))
        asyncio.create_task(self._subscribe('channel.channel_points_custom_reward_redemption.add', self._stream_token))
        asyncio.create_task(self._subscribe('channel.cheer', self._stream_token))
        asyncio.create_task(self._subscribe('stream.online', self._stream_token))
        asyncio.create_task(self._subscribe('stream.offline', self._stream_token))

    def get_val(self, obj, key):
        keys = str(key).split('.')

        node = obj

        while len(keys) > 0:
            if keys[0] in node:
                node = node[keys[0]]
                keys.pop(0)
            else:
                return None

        return node

    async def _on_notification(self, meta, payload):

        subscription_type = self.get_val(meta, 'subscription_type')

        self._log.debug('received subscription notification: {}'.format(subscription_type))
        self._log.debug('metadata: {}'.format(meta))
        self._log.debug('payload: {}'.format(payload))

        if subscription_type == 'channel.channel_points_custom_reward_redemption.add':
            reward_username = self.get_val(payload, 'event.user_name')
            reward_title = self.get_val(payload, 'event.reward.title')

            # pass the redeem to the gears
            for gear in self._gears:
                self.create_task(gear.on_redeem(reward_username, reward_title))
        elif subscription_type == 'channel.cheer':
            anon = self.get_val(payload, 'event.is_anonymous')
            who = 'Anonymous'
            if not anon:
                who = self.get_val(payload, 'event.user_name')
            bits = self.get_val(payload, 'event.bits')
            message = self.get_val(payload, 'event.message')

            for gear in self._gears:
                self.create_task(gear.on_cheer(who, bits, message))
        elif subscription_type == 'channel.follow':
            follow_username = self.get_val(payload, 'event.user_name')

            for gear in self._gears:
                self.create_task(gear.on_follow(follow_username))
        elif subscription_type == 'channel.subscribe':
            subscribe_username = self.get_val(payload, 'event.user_name')

            for gear in self._gears:
                self.create_task(gear.on_subscribe(subscribe_username, None, None))
        elif subscription_type == 'channel.subscription.message':
            subscribe_username = self.get_val(payload, 'event.user_name')
            message = self.get_val(payload, 'event.message.text')
            emotes = self.get_val(payload, 'event.message.emotes')

            for gear in self._gears:
                self.create_task(gear.on_subscribe(subscribe_username, message, emotes))
        elif subscription_type == 'stream.online':
            self._log.info('stream state has changed from {} to online'.format('unknown' if self._is_live is None else 'offline'))
            self._is_live = True
            for gear in self._gears:
                self.create_task(gear.on_stream_live(True))
        elif subscription_type == 'stream.offline':
            self._log.info('stream state has changed from {} to offline'.format('unknown' if self._is_live is None else 'online'))
            self._is_live = False
            for gear in self._gears:
                self.create_task(gear.on_stream_live(False))
        elif subscription_type == 'channel.raid':
            raider_username = self.get_val(payload, 'event.from_broadcaster_user_name')
            raid_size = self.get_val(payload, 'event.viewers')
            for gear in self._gears:
                self.create_task(gear.on_raid(raider_username, raid_size))
        else:
            self._log.warning('subscription notification unhandled: {}'.format(subscription_type))

    async def eventsub_loop(self):

        async for self._socket in websockets.connect('wss://eventsub-beta.wss.twitch.tv/ws'):
            try:
                while True:

                    data = await self._socket.recv()
                    data = json.loads(data)

                    if 'metadata' not in data:
                        self._log.warning('no metadata in message')
                        continue

                    if 'message_type' not in data['metadata']:
                        self._log.warning('no message type')
                        continue

                    message_type = data['metadata']['message_type']

                    if message_type == 'session_welcome':
                        self.create_task(self._on_session_welcome(data['metadata'], data['payload']))
                    elif message_type == 'session_keepalive':
                        pass
                    elif message_type == 'notification':
                        self.create_task(self._on_notification(data['metadata'], data['payload']))
                    elif message_type == 'session_reconnect':
                        self._log.info('session_reconnect received. websocket reconnecting...')

                        new_socket = await websockets.connect(self.get_val(data, 'payload.session.reconnect_url'))
                        welcome_data = await new_socket.recv()
                        welcome_data = json.loads(welcome_data)
                        new_message_type = self.get_val(welcome_data, 'metadata.message_type')
                        new_session_id = self.get_val(welcome_data, 'payload.session.id')
                        if new_message_type != 'session_welcome':
                            self._log.error('first message on reconnect was not session_welcome')
                            return

                        if new_session_id != self._session_id:
                            self._log.warning('session id changed')
                            self._session_id = new_session_id

                        await self._socket.close()
                        self._socket = new_socket

                        self._log.info('reconnect complete')

                    else:
                        self._log.warning('no handler for message type {}'.format(message_type))
                        self._log.warning(data)

            except websockets.exceptions.ConnectionClosed:
                continue

    async def load_gears(self):
        self._gears = gears.load()

        for gear in self._gears:
            await gear.start(self)

async def main():
    bot = TwitchBot()

    await bot.start()

    while True:
        await asyncio.sleep(1)


if __name__ == '__main__':
    asyncio.run(main())
