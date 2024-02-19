import asyncio
import logging.config
import tomllib

import aiohttp
import discord
from discord.ext import commands
import orjson

from . import Bot, Pool


async def main():
    with open("WorstBot/core/configs/config.toml", "rb") as f:
        config = tomllib.load(f)
    with open("WorstBot/core/configs/logging.toml", "rb") as f:
        logging.config.dictConfig(tomllib.load(f))
    intents = discord.Intents(
        bans=True,
        emojis=True,
        guilds=True,
        integrations=True,
        invites=True,
        members=True,
        guild_messages=True,
        guild_scheduled_events=True,
        voice_states=True,
        webhooks=True,
    )

    async with (
        Pool(
            database=config["postgres"]["db"],
            user=config["postgres"]["user"],
            password=config["postgres"]["password"],
            host=config["postgres"]["host"],
            command_timeout=1,
            min_size=1,
            max_size=25,
        ) as pool,
        aiohttp.ClientSession(json_serialize=lambda x: str(orjson.dumps(x), "utf-8")) as http_session,
        Bot(
            prefix=commands.when_mentioned,
            activity=discord.Game(name="With ones and zeros"),
            intents=intents,
            owner_ids=config["discord"]["owners"],
            config=config,
            pool=pool,
        ) as bot,
    ):
        bot.logging_queue = asyncio.Queue()
        bot.log_handler = logging.getLogger("WorstBot")
        logging.getLogger().handlers[0].queue = bot.logging_queue
        bot.pool = pool
        bot.http_session = http_session

        token = config["discord"]["token"]
        await bot.start(token)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
