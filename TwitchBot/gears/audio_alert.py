#!/usr/bin/env python3

__author__ = 'Ximmer'
__copyright__ = 'Copyright 2023, Ximmer'

import os
import threading

import pyaudio
import wave
import random

from . import Gear


class AudioAlert(Gear):
    def __init__(self):
        super().__init__()

    @staticmethod
    def name():
        return 'AudioAlert'

    async def on_redeem(self, who: str, redeem: str) -> None:
        if self.is_live():
            self.play(redeem.lower())

    def play(self, name: str) -> None:
        self._log.warning(name)

        stripped_name = ''.join(e for e in name if e.isalnum())

        file_name_dir = os.path.join(os.getcwd(), 'audio/{}/'.format(stripped_name)).replace('\\', '/')
        file_name_wav = os.path.join(os.getcwd(), 'audio/{}.wav'.format(stripped_name)).replace('\\', '/')

        if os.path.exists(file_name_wav):
            self.log_info('playing sound {}'.format(file_name_wav))
            threading.Thread(target=self._play_thread, args=(file_name_wav,), daemon=True).start()

        elif os.path.exists(file_name_dir):
            files = os.listdir(file_name_dir)

            file_name_wav = os.path.join(file_name_dir, random.choice(files))
            self.log_info('playing sound {}'.format(file_name_wav))
            threading.Thread(target=self._play_thread, args=(file_name_wav,), daemon=True).start()

    def _play_thread(self, filename):
        #define stream chunk
        chunk = 1024

        #open a wav format music
        f = wave.open(filename, 'rb')
        p = pyaudio.PyAudio()

        stream = p.open(format = p.get_format_from_width(f.getsampwidth()),
                        channels = f.getnchannels(),
                        rate = f.getframerate(),
                        output = True)
        #read data
        data = f.readframes(chunk)

        #play stream
        while data:
            stream.write(data)
            data = f.readframes(chunk)

        #stop stream
        stream.stop_stream()
        stream.close()

        #close PyAudio
        p.terminate()

Export = AudioAlert