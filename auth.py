#! /usr/bin/env python3

__author__ = 'Ximmer'
__copyright__ = 'Copyright 2023, Ximmer'

import datetime
import json
import os
import time

import requests

import logger


class Token(object):
    def __init__(self, name, client_id, client_secret, code):
        self._log = logger.Logger(__class__.__name__)
        self._client_id = client_id
        self._client_secret = client_secret
        self._code = code

        self._name = name
        self._token = None
        self._refresh_token = None
        self._token_expires = None
        self._scope = None

    def get(self):

        # check for cached token
        if self._token is None:
            if os.path.exists('tokens.json'):
                with open('tokens.json') as fp:
                    token = json.load(fp)
                    if self._name in token:
                        if 'token' in token[self._name]:
                            self._token = token[self._name]['token']
                            self._refresh_token = token[self._name]['refresh_token']
                            self._token_expires = token[self._name]['token_expires']
                            self._log.obfuscate(self._token)
                            self._log.obfuscate(self._refresh_token)

        # check for expired token
        if self._token_expires is None or time.time() > self._token_expires:

            if self._refresh_token is not None:
                self._log.info('refreshing token {}'.format(self._name))
                # refresh token
                url = 'https://id.twitch.tv/oauth2/token?client_id={client_id}&client_secret={client_secret}&grant_type=refresh_token&refresh_token={refresh_token}'.format(client_id=self._client_id, client_secret=self._client_secret, refresh_token=self._refresh_token)
                headers = { 'Accept': 'application/vnd.twitchtv.v5+json', }
                response = requests.post(url, headers=headers).json()
                if 'access_token' not in response:
                    self._log.error('error getting token')
                    self._log.error(response)
                else:
                    self._token = response['access_token']
                    self._refresh_token = response['refresh_token']
                    self._token_expires = time.time() + response['expires_in']
                    if 'scope' in response:
                        self._scope = response['scope']
                    else:
                        self._scope = None
                    self._log.obfuscate(self._token)
                    self._log.obfuscate(self._refresh_token)
                    self._log.debug(response)

            else:
                self._log.info('Getting token {}'.format(self._name))
                url = 'https://id.twitch.tv/oauth2/token?client_id={client_id}&client_secret={client_secret}&code={auth_code}&grant_type=authorization_code&redirect_uri=https://localhost'.format(client_id=self._client_id, client_secret=self._client_secret, auth_code=self._code)
                headers = { 'Accept': 'application/vnd.twitchtv.v5+json', }
                response = requests.post(url, headers=headers).json()
                if 'access_token' not in response:
                    self._log.error('error getting user token')
                    self._log.error(response)
                else:
                    self._token = response['access_token']
                    self._refresh_token = response['refresh_token']
                    self._token_expires = time.time() + response['expires_in']
                    if 'scope' in response:
                        self._scope = response['scope']
                    else:
                        self._scope = None
                    self._log.obfuscate(self._token)
                    self._log.obfuscate(self._refresh_token)
                    self._log.debug('token: {}'.format(self._token))
                    self._log.debug('token expires in: {}'.format(str(datetime.timedelta(seconds=response['expires_in']))))
                    self._log.warning(response)

            if os.path.exists('tokens.json'):
                with open('tokens.json') as fp:
                    token = json.load(fp)
            else:
                token = {}

            token[self._name] = {
                'token': self._token,
                'refresh_token': self._refresh_token,
                'token_expires': self._token_expires,
                'scope': self._scope
            }

            with open('tokens.json', 'w') as fp:
                json.dump(token, fp, indent=4)

        return self._token

