#!/usr/bin/env python3

__author__ = 'Ximmer'
__copyright__ = 'Copyright 2023, Ximmer'

import os
import threading

import playsound

from . import Gear


class AudioAlert(Gear):
    def __init__(self):
        super().__init__()

    @staticmethod
    def name():
        return 'AudioAlert'

    async def on_redeem(self, who: str, redeem: str) -> None:
        if redeem.lower().startswith('audio'):
            self.play(redeem.lower())

    def play(self, name: str) -> None:
        file_name_mp3 = os.path.join(os.getcwd(), 'audio/{}.mp3'.format(name)).replace('\\', '/')
        file_name_wav = os.path.join(os.getcwd(), 'audio/{}.wav'.format(name)).replace('\\', '/')

        if os.path.exists(file_name_mp3):
            self.log_info('playing sound {}'.format(file_name_mp3))
            threading.Thread(target=playsound.playsound, args=(file_name_mp3,), daemon=True).start()
        elif os.path.exists(file_name_wav):
            self.log_info('playing sound {}'.format(file_name_wav))
            threading.Thread(target=playsound.playsound, args=(file_name_wav,), daemon=True).start()

Export = AudioAlert