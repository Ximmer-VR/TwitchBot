#!/usr/bin/env python3

__author__ = 'Ximmer'
__copyright__ = 'Copyright 2023, Ximmer'

import time

import spotipy
from spotipy.oauth2 import SpotifyOAuth

from . import Gear

MAX_DURATION_MS = 10 * 60 * 1000
UPDATE_RATE_S = 10

class Spotify(Gear):

    def __init__(self):
        super().__init__()

        client_id = self.config_get('SPOTIPY_CLIENT_ID')
        client_secret = self.config_get('SPOTIPY_CLIENT_SECRET')
        redirect_uri = self.config_get('SPOTIPY_REDIRECT_URI')

        self._log.obfuscate(client_id)
        self._log.obfuscate(client_secret)
        self._log.obfuscate(redirect_uri)

        self._spotify = spotipy.Spotify(client_credentials_manager=SpotifyOAuth(client_id, client_secret, redirect_uri, scope='user-read-currently-playing,user-modify-playback-state,user-read-playback-state'))

        self._queue = []
        self._current_song = None
        self._last_song = None

        self._next_update = time.time()

    @staticmethod
    def name():
        return 'Spotify'

    def get_artists_str(self, item):
        artists = []

        for i in item['artists']:
            self.log_debug(i)
            artists.append(i['name'])

        return ', '.join(artists)

    def format_time_ms(self, ms):
        h = int(ms / 1000 / 60 / 60)
        m = int(ms / 1000 / 60) % 60
        s = int(ms / 1000) % 60

        result = ''

        if h != 0:
            result += ' {}h'.format(h)

        if m != 0 or h != 0:
            result += ' {}m'.format(m)

        if s != 0 or m != 0:
            result += ' {}s'.format(s)

        return result.strip()

    async def on_message(self, who: str, message: str, user_level: str, tags) -> None:

        if not self.is_live():
            return

        if message.startswith('!request'):
            message = '!sr {}'.format(message[8:])

        if message.startswith('!sr'):

            data = message[3:].strip()

            if data == '':
                await self.send_message('!request [artist song] | !song | !nextsong | !lastsong | !removesong')
                return

            self.log_debug('request: {}'.format(data))

            results = self._spotify.search(data)

            if 'tracks' not in results:
                await self.send_message('no tracks found.')
                return

            if 'items' not in results['tracks']:
                await self.send_message('no tracks found.')
                return

            if len(results['tracks']['items']) == 0:
                await self.send_message('no tracks found.')
                return

            item = results['tracks']['items'][0]
            #self.log_debug('search results: {}'.format(item))

            if item['duration_ms'] > MAX_DURATION_MS:
                await self.send_message('error: {} by {} is {} long. max time is {}'.format(item['name'], self.get_artists_str(item), self.format_time_ms(item['duration_ms']), self.format_time_ms(MAX_DURATION_MS)))
                return

            await self.send_message('{} has requested {} by {}'.format(who, item['name'], self.get_artists_str(item)))

            await self.queue_song(who, item['name'], self.get_artists_str(item), item['uri'])

        if message.startswith('!cs') or message.startswith('!song'):
            result = self._spotify.currently_playing()
            self.log_debug(result)

            progress = result['progress_ms'] * 100 / result['item']['duration_ms']

            await self.send_message('Currently playing: {} by {} ({})'.format(result['item']['name'], self.get_artists_str(result['item']), progress))

        if message.startswith('!nextsong') or message.startswith('!ns'):
            if len(self._queue) > 0:
                await self.send_message('next song is {} by {}. requested by {}'.format(self._queue[0]['name'], self._queue[0]['artists'], self._queue[0]['who']))
            else:
                await self.send_message('queue is empty')

        if message.startswith('!lastsong') or message.startswith('!ls'):
            if self._last_song is not None:
                await self.send_message('last song was {} by {}. requested by {}'.format(self._queue[0]['name'], self._queue[0]['artists'], self._queue[0]['who']))

        if message.startswith('!removesong') or message.startswith('!removelast') or message.startswith('!rs'):
            best = -1
            for i in range(len(self._queue)):
                if who == self._queue[i]['who']:
                    best = i
            if best != -1:
                if best == 0:
                    # todo: message something something already queued in spotify no removal allowed
                    pass
                item = self._queue.pop(i)
                await self.send_message('{} by {} has been removed from the queue'.foramt(item['name'], item['artits']))


    async def queue_song(self, who, name, artists, uri):

        item = {
            'who': who,
            'name': name,
            'artists': artists,
            'uri': uri,
        }

        self._queue.append(item)

        # if the queue was empty add the song to the queue
        if len(self._queue) == 1:
            self.log_info('adding {} by {} to the queue: requested by {}'.format(self._queue[0]['name'], self._queue[0]['artists'], self._queue[0]['who']))
            result = self._spotify.add_to_queue(self._queue[0]['uri'])
            self.log_debug(result)

    async def on_update(self):
        if time.time() < self._next_update:
            return

        self._next_update = time.time() + UPDATE_RATE_S

        item = self._spotify.currently_playing()

        if len(self._queue) > 0:
            if item['item']['uri'] == self._queue[0]['uri']:
                self.log_info('{} by {} is now playing. requested by {}'.format(self._queue[0]['name'], self._queue[0]['artists'], self._queue[0]['who']))
                self._last_song = self._current_song
                self._current_song = self._queue.pop(0)

                if len(self._queue) > 0:
                    self.log_info('adding {} by {} to the queue: requested by {}'.format(self._queue[0]['name'], self._queue[0]['artists'], self._queue[0]['who']))
                    result = self._spotify.add_to_queue(self._queue[0]['uri'])
                    self.log_debug(result)



Export = Spotify
