import asyncio
import datetime
from logging import WARN, INFO, DEBUG
from os import environ, listdir

import discord
from discord.ext import commands as discord_commands

import asyncpg
from aiohttp import ClientSession
from dotenv import load_dotenv


class WorstBot(discord_commands.Bot):
    def __init__(self, command_prefix, activity, intents):
        super().__init__(command_prefix, intents = intents)
        self.pool = None
        self.session = None
        self.activity = activity

    async def setup_hook(self) -> None:
        self.pool = await asyncpg.create_pool(database = environ.get("postgresdb"), user = environ.get("postgresuser"), password = environ.get("postgrespassword"), command_timeout = 10, max_size = 100, min_size = 25)
        self.session = ClientSession()
        self.post = self.post
        self.get = self.get
        self.getstatus = self.getstatus
        self.fetch = self.fetch
        self.fetchrow = self.fetchrow
        self.fetchval = self.fetchval
        self.execute = self.execute
        self.current = self.current

        for filename in listdir("cogs"):
            if filename.endswith(".py") and not filename.startswith("-"):
                await self.load_extension(f'cogs.{filename[:-3]}')
                pass

    async def on_ready(self):
        print(f"Connected as {self.user} at {datetime.datetime.now().strftime('%d/%m/%y %H:%M')}")

    async def post(self, *, url: str, params: dict = None, headers: dict = None):
        async with self.session.post(url = url, params = params, headers = headers) as response:
            content = await response.json()
            content["status"] = response.status
            return content

    async def get(self, *, url: str, params: dict = None, headers: dict = None):
        async with self.session.get(url = url, params = params, headers = headers) as response:
            content = await response.json()
            if not isinstance(content, dict):
                content = {"data": content[0] if len(content) == 1 else content}
            content["status"] = response.status
            return content

    async def getstatus(self, *, url: str, params: dict = None, headers: dict = None):
        async with self.session.get(url = url, params = params, headers = headers) as response:
            return response.status

    async def fetch(self, sql: str, *args):
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                return await conn.fetch(sql, *args)

    async def fetchrow(self, sql: str, *args):
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                return await conn.fetchrow(sql, *args)

    async def fetchval(self, sql: str, *args):
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                return await conn.fetchval(sql, *args)

    async def execute(self, sql: str, *args):
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                return await conn.fetchval(sql, *args)

    @staticmethod
    def current(current: str) -> str:
        return "%" if not current else current


async def start():
    await asyncio.gather(discord_bot.start(environ.get("discord")), return_exceptions = True)


load_dotenv()
discord.utils.setup_logging(level = WARN)
discord_bot = WorstBot(command_prefix = discord_commands.when_mentioned,
                       activity = discord.Streaming(name = "With ones and zeros", url = "http://definitelynotarickroll.lol/", game = "a little bit of trolling", platform = "YouTube"),
                       intents = discord.Intents.all())

asyncio.run(start())
