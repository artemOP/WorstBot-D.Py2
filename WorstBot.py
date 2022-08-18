import discord
from discord.ext import commands
from os import listdir, environ
import asyncpg
import datetime
from dotenv import load_dotenv
from aiohttp import ClientSession
from logging import DEBUG, WARN


class WorstBot(commands.Bot):
    def __init__(self, command_prefix, activity, intents):
        super().__init__(command_prefix, intents = intents)
        self.pool = None
        self.session = None
        self.activity = activity

    async def setup_hook(self) -> None:
        bot.pool = await asyncpg.create_pool(database = environ.get("postgresdb"), user = environ.get("postgresuser"), password = environ.get("postgrespassword"), command_timeout = 10, max_size = 100, min_size = 25)
        bot.session = ClientSession()
        bot.post = self.post
        bot.get = self.get
        bot.getstatus = self.getstatus
        bot.fetch = self.fetch
        bot.fetchrow = self.fetchrow
        bot.fetchval = self.fetchval
        bot.execute = self.execute
        bot.current = self.current

        for filename in listdir("cogs"):
            if filename.endswith(".py") and not filename.startswith("-"):
                await bot.load_extension(f'cogs.{filename[:-3]}')
                pass

    async def on_ready(self):
        print(f"Connected as {self.user} at {datetime.datetime.now().strftime('%d/%m/%y %H:%M')}")

    @staticmethod
    async def post(*, url: str, params: dict = None, headers: dict = None):
        async with bot.session.post(url = url, params = params, headers = headers) as response:
            content = await response.json()
            content["status"] = response.status
            return content

    @staticmethod
    async def get(*, url: str, params: dict = None, headers: dict = None):
        async with bot.session.get(url = url, params = params, headers = headers) as response:
            content = await response.json()
            if not isinstance(content, dict):
                content = {"data": content[0] if len(content) == 1 else content}
            content["status"] = response.status
            return content

    @staticmethod
    async def getstatus(*, url: str, params: dict = None, headers: dict = None):
        async with bot.session.get(url = url, params = params, headers = headers) as response:
            return response.status

    @staticmethod
    async def fetch(sql: str, *args):
        async with bot.pool.acquire() as conn:
            async with conn.transaction():
                return await conn.fetch(sql, *args)

    @staticmethod
    async def fetchrow(sql: str, *args):
        async with bot.pool.acquire() as conn:
            async with conn.transaction():
                return await conn.fetchrow(sql, *args)

    @staticmethod
    async def fetchval(sql: str, *args):
        async with bot.pool.acquire() as conn:
            async with conn.transaction():
                return await conn.fetchval(sql, *args)

    @staticmethod
    async def execute(sql: str, *args):
        async with bot.pool.acquire() as conn:
            async with conn.transaction():
                return await conn.fetchval(sql, *args)

    @staticmethod
    def current(current: str) -> str:
        return "%" if not current else current


load_dotenv()
bot = WorstBot(command_prefix = commands.when_mentioned,
               activity = discord.Game(name = "With ones and zeros"),
               intents = discord.Intents.all())
bot.run(environ.get("discord"), log_level = WARN)
