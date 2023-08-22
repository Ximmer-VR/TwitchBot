#!/usr/bin/env python3

__author__ = 'Ximmer'
__copyright__ = 'Copyright 2023, Ximmer'

import asyncio
import base64
import hashlib
import json

import websockets

from . import Gear

class Obs(Gear):

    def __init__(self):
        super().__init__()

        self._socket = None
        self._auth_state = False

    @staticmethod
    def name():
        return 'Obs'

    async def on_start(self):
        self.create_task(self._obs_run())

    async def on_stream_live(self, live: bool):
        pass

    async def on_redeem(self, who: str, redeem: str) -> None:
        if not self.is_live():
            return

        self.log_info('redeem {}'.format(redeem))

        if redeem == 'Headpats':

            self.log_info('its headpats')

            for sceneName in self._sceneItems:
                scene = self._sceneItems[sceneName]

                for sceneItemId in scene:
                    sceneItem = scene[sceneItemId]

                    if sceneItem['sourceName'] == 'Redeem - Headpat':

                        self.log_info('headpat found')

                        self.create_task(self.activate_redeem(sceneName, sceneItemId))

    async def activate_redeem(self, sceneName, sceneItemId):

        self.log_info('activate redeem')

        await self.set_scene_item_enabled(sceneName, sceneItemId, True)
        await asyncio.sleep(5)
        await self.set_scene_item_enabled(sceneName, sceneItemId, False)

    async def _obs_run(self):

        while True:

            if not self.is_live():
                await asyncio.sleep(1)
                continue

            try:
                self._socket = await websockets.connect('ws://127.0.0.1:4455')
                self._auth_state = False

                while True:
                    data = await self._socket.recv()
                    data = json.loads(data)

                    self.log_debug(data)

                    if self._auth_state is False:
                        await self._handle_auth(data)
                    else:
                        await self._handle_data(data)

                    await asyncio.sleep(0.01)

            except Exception as ex:
                self.log_warning('unable to connect to obs')
                self.log_exception(ex)
                await asyncio.sleep(1)
                continue

    async def _handle_auth(self, d):
        if d['op'] == 0:    # Hello
            if 'authentication' in d['d']:
                await self._send_auth(d['d']['authentication']['salt'], d['d']['authentication']['challenge'])
                return

        if d['op'] == 2:    # Identified
            self._auth_state = True
            await self.get_scene_list()
            return

        self.log_warning('_handle_auth got unexpected op {}'.format(d['op']))

    async def _handle_data(self, d):
        if d['op'] == 7:    # RequestResponse

            requestType = d['d']['requestType']

            if requestType == 'GetSceneList':
                await self.on_get_scene_list(d['d']['responseData'])
                return

            if requestType == 'GetSceneItemList':
                await self.on_get_scene_item_list(d['d']['requestId'], d['d']['responseData'])

            if requestType == 'GetGroupSceneItemList':
                await self.on_get_scene_item_list(d['d']['requestId'], d['d']['responseData'])

    async def on_get_scene_list(self, data):
        self._current_scene = data['currentProgramSceneName']

        self._scenes = {}
        self._sceneItems = {}

        for scene in data['scenes']:
            self._scenes[scene['sceneIndex']] = scene['sceneName']

            await self.get_scene_item_list(scene['sceneName'])

    async def on_get_scene_item_list(self, id, data):

        for sceneItem in data['sceneItems']:

            if sceneItem['isGroup']:
                await self.get_group_scene_item_list(id, sceneItem['sourceName'])
                # Todo: store the group to be able to turn it on and off?
                continue

            if id not in self._sceneItems:
                self._sceneItems[id] = {}

            self._sceneItems[id][sceneItem['sceneItemId']] = sceneItem

    async def _send_auth(self, salt, challenge):
        password = 'ro6byvAffIZROXon'   # Todo: get password from a self.config function call, log error if not configured

        hash = hashlib.sha256()
        hash.update((password + salt).encode())
        base64_secret = hash.digest()
        base64_secret = base64.b64encode(base64_secret)

        hash = hashlib.sha256()
        hash.update((base64_secret.decode() + challenge).encode())

        auth = hash.digest()
        auth = base64.b64encode(auth).decode()

        msg = {
            'op': 1,
            'd': {
                'rpcVersion': 1,
                'authentication': auth,
                #'eventSubscriptions': 33
            }
        }

        msg_j = json.dumps(msg)

        await self._socket.send(msg_j)

    async def get_scene_list(self):
        msg = {
            'op': 6,
            'd': {
                'requestType': 'GetSceneList',
                'requestId': '',
                'requestData': {
                },
            }
        }

        msg_j = json.dumps(msg)

        await self._socket.send(msg_j)

    async def get_scene_item_list(self, sceneName):
        msg = {
            'op': 6,
            'd': {
                'requestType': 'GetSceneItemList',
                'requestId': sceneName,
                'requestData': {
                    'sceneName': sceneName
                },
            }
        }

        msg_j = json.dumps(msg)

        await self._socket.send(msg_j)

    async def get_group_scene_item_list(self, sceneName, groupName):
        msg = {
            'op': 6,
            'd': {
                'requestType': 'GetGroupSceneItemList',
                'requestId': groupName,
                'requestData': {
                    'sceneName': groupName
                },
            }
        }

        msg_j = json.dumps(msg)

        await self._socket.send(msg_j)


    async def set_scene_item_enabled(self, sceneName, sceneItemId, enable):

        self.log_info('{} {} {}'.format('enable' if enable else 'disable', sceneName, sceneItemId))

        msg = {
            'op': 6,
            'd': {
                'requestType': 'SetSceneItemEnabled',
                'requestId': '',
                'requestData': {
                    'sceneName': sceneName,
                    'sceneItemId': sceneItemId,
                    'sceneItemEnabled': enable,
                },
            }
        }

        msg_j = json.dumps(msg)

        await self._socket.send(msg_j)

Export = Obs
