#!/usr/bin/env python3

__author__ = 'Ximmer'
__copyright__ = 'Copyright 2023, Ximmer'

import re
import sqlite3

from . import Gear

TIMEOUT_TIME_S = 3600
BAN_PHRASE_PASS_PERCENTAGE = 85
TIMEOUT_REASON = 'message was too close to banned phrase.'

class BanText(Gear):
    def __init__(self):
        super().__init__()

    @staticmethod
    def name():
        return 'BanText'

    async def on_start(self) -> None:
        self.banned_phrases = []
        self.load_bantext()

    async def on_message(self, who: str, message: str, user_level: str, tags) -> None:

        if user_level == 'streamer' or user_level == 'mod':
            # TODO: make a command system for gears?
            command = message.split()
            if command[0] == '!bantext':
                if len(command) != 2:
                    await self.send_message('usage: !bantext <user>')
                    return
                self.ban_user_phrase(command[1])
            return

        # check for banned message
        if self.check_phrase_is_banned(message):
            self.timeout(who, TIMEOUT_REASON, TIMEOUT_TIME_S)

    def add_banned_phrase(self, phrase):

        phrase = re.sub(r'[^\w\s]', ' ', phrase)

        bag = phrase.split()

        self.banned_phrases.append(bag)

    def load_bantext(self):
        self.log_info('loading banned phrases')
        try:
            cursor = self.db_cursor()
            cursor.execute("SELECT message FROM banned_text")
            rows = cursor.fetchall()

            for row in rows:
                self.add_banned_phrase(row['message'])

        except sqlite3.Error as ex:
            self.log_exception(ex)

    def check_phrase_is_banned(self, phrase):

        phrase = re.sub(r'[^\w\s]', ' ', phrase)
        bag = phrase.split()

        best_match = 0

        for banned_bag in self.banned_phrases:
            words_in = 0
            words_total = 0

            for word in banned_bag:
                words_total += 1
                if word in bag:
                    words_in += 1

            if words_total == 0:
                continue

            match = words_in / words_total
            if match > best_match:
                best_match = match

        self._log.debug('banned phrase match score: {}'.format(match))

        if best_match > BAN_PHRASE_PASS_PERCENTAGE / 100.0:
            return True
        return False

    def ban_user_phrase(self, who):

        self.log_info('banning last phrase from {}'.format(who))

        try:
            cursor = self.db_cursor()
            cursor.execute("SELECT message FROM chat_log WHERE LOWER(display_name)=LOWER(?) ORDER BY id DESC", (who,))
            row = cursor.fetchone()
            self.log_debug(row)

            if row is not None:
                cursor = self.db_cursor()
                cursor.execute('INSERT INTO banned_text(message) VALUES(?)', (row['message'],))
                self.db_commit()

                self.add_banned_phrase(row['message'])

                self.timeout(who, TIMEOUT_REASON, TIMEOUT_TIME_S)

        except sqlite3.Error as ex:
            self.log_exception(ex)

Export = BanText