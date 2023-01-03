import asyncio
import datetime
import typing
from enum import Enum, auto
from logging import WARN, INFO, DEBUG
from os import environ, listdir

import discord
from discord.ext import commands as discord_commands

import asyncpg
from aiohttp import ClientSession
from dotenv import load_dotenv

class _events(Enum):
    autorole = auto()
    autoevent = auto()
    birthdays = auto()
    roles = auto()
    opinion = auto()
    calls = auto()
    textarchive = auto()
    twitch = auto()
    usage = auto()

class WorstBot(discord_commands.Bot):

    def __init__(self, command_prefix, activity, intents, owner_id):
        super().__init__(command_prefix, intents = intents, owner_id = owner_id)
        self.pool = None
        self.session = None
        self._event_toggles = {}
        self.activity = activity
        self._events = _events

    async def setup_hook(self) -> None:
        self.pool = await asyncpg.create_pool(database = environ.get("postgresdb"), user = environ.get("postgresuser"), password = environ.get("postgrespassword"), command_timeout = 10, max_size = 100, min_size = 25)
        self.session = ClientSession()

        for filename in listdir("cogs"):
            if filename.endswith(".py") and not filename.startswith("-"):
                await self.load_extension(f'cogs.{filename[:-3]}')
                pass

    async def on_ready(self):
        print(f"Connected as {self.user} at {datetime.datetime.now().strftime('%d/%m/%y %H:%M')}")

    async def post(self, *, url: str, params: dict = None, headers: dict = None) -> dict:
        async with self.session.post(url = url, params = params, headers = headers) as response:
            content = await response.json()
            content["status"] = response.status
            return content

    async def get(self, *, url: str, params: dict = None, headers: dict = None) -> dict:
        async with self.session.get(url = url, params = params, headers = headers) as response:
            content = await response.json()
            if not isinstance(content, dict):
                content = {"data": content[0] if len(content) == 1 else content}
            content["status"] = response.status
            return content

    async def getstatus(self, *, url: str, params: dict = None, headers: dict = None) -> int:
        async with self.session.get(url = url, params = params, headers = headers) as response:
            return response.status

    async def fetch(self, sql: str, *args) -> list[asyncpg.Record] | None:
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                return await conn.fetch(sql, *args)

    async def fetchrow(self, sql: str, *args) -> asyncpg.Record | None:
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                return await conn.fetchrow(sql, *args)

    async def fetchval(self, sql: str, *args) -> typing.Any:
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                return await conn.fetchval(sql, *args)

    async def execute(self, sql: str, *args) -> typing.Any:
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                return await conn.fetchval(sql, *args)

    @staticmethod
    def current(current: str) -> typing.Literal["%"] | str:
        return "%" if not current else current

    @staticmethod
    def to_codeblock(language: str, code: str) -> str:
        """
        Returns codeblock in the format of:
        ```{language}
        code
        ```
        """
        return f"```{language}\n{code}```"

    async def events(self, guild_int: int, event: _events) -> bool:
        """Returns True/False to determine if event is enabled in guild"""
        if not self._event_toggles.get(guild_int):  # Adds guild to cache with no events
            self._event_toggles[guild_int] = {}

        if self._event_toggles[guild_int].get(event.name) is None:  # Adds event to guild on request
            toggle_value = await self.fetchval(f"SELECT {event.name} FROM events WHERE guild = $1", guild_int)
            self._event_toggles[guild_int][event.name] = toggle_value

        return self._event_toggles[guild_int][event.name]  # returns event bool


async def start():
    await asyncio.gather(discord_bot.start(environ.get("discord")), return_exceptions = False)

if __name__ == "__main__":
    load_dotenv()
    discord.utils.setup_logging(level = WARN)
    discord_bot = WorstBot(command_prefix = discord_commands.when_mentioned,
                           activity = discord.Streaming(name = "With ones and zeros", url = "http://definitelynotarickroll.lol/", game = "a little bit of trolling", platform = "YouTube"),
                           intents = discord.Intents.all(),
                           owner_id = environ.get("owner"))

    asyncio.run(start())
