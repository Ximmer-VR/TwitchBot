#! /usr/bin/env python3

import bot
import asyncio

async def main():
    tb = bot.TwitchBot()

    await tb.start()

    try:
        while True:
            await asyncio.sleep(1)
    except Exception as ex:
        print(ex)

if __name__ == '__main__':

    try:
        asyncio.run(main())
    except Exception as ex:
        print(ex)
