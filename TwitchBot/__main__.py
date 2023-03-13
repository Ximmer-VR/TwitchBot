#! /usr/bin/env python3

import bot
import asyncio

async def main():
    tb = bot.TwitchBot()

    await tb.start()

    while True:
        await asyncio.sleep(1)


if __name__ == '__main__':
    asyncio.run(main())
