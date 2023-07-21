#!/usr/bin/env python3

__author__ = 'Ximmer'
__copyright__ = 'Copyright 2023, Ximmer'

from . import Gear


class AudioAlert(Gear):
    def __init__(self):
        super().__init__()

    @staticmethod
    def name():
        return 'AudioAlert'

    async def on_redeem(self, who: str, redeem: str) -> None:
        if self.is_live():
            self.play_sound(redeem.lower())

Export = AudioAlert