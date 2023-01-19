import asyncio
import datetime
import typing
from typing import Any, Optional
from enum import StrEnum, auto
import logging
from logging import WARN, INFO, DEBUG
from os import environ, listdir

import discord
from discord import abc
from discord.ext import commands as discord_commands

import asyncpg
from aiohttp import ClientSession
from dotenv import load_dotenv
import orjson

class _events(StrEnum):
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
        super().__init__(command_prefix, intents = intents, owner_id = owner_id, activity = activity)
        self.pool: Optional[asyncpg.Pool] = None
        self.session: Optional[ClientSession] = None
        self._event_toggles = {}
        self._events = _events
        self.logger = logging.getLogger(self.__class__.__name__)

    async def setup_hook(self) -> None:
        self.pool = await asyncpg.create_pool(database = environ.get("postgresdb"), user = environ.get("postgresuser"), password = environ.get("postgrespassword"), command_timeout = 10, min_size = 1, max_size = 100, loop = self.loop)
        self.session = ClientSession(loop = self.loop, json_serialize=lambda x: orjson.dumps(x).decode())

        for filename in listdir("cogs"):
            if filename.endswith(".py") and not filename.startswith("-"):
                await self.load_extension(f'cogs.{filename[:-3]}')
                pass

    async def on_ready(self):
        self.logger.info(f"Connected as {self.user} at {datetime.datetime.now().strftime('%d/%m/%y %H:%M')}")

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

    async def fetch(self, sql: str, *args) -> Optional[list[asyncpg.Record]]:
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                return await conn.fetch(sql, *args)

    async def fetchrow(self, sql: str, *args) -> Optional[asyncpg.Record]:
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                return await conn.fetchrow(sql, *args)

    async def fetchval(self, sql: str, *args) -> Optional[Any]:
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                return await conn.fetchval(sql, *args)

    async def execute(self, sql: str, *args) -> Optional[Any]:
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                return await conn.fetchval(sql, *args)

    async def maybe_fetch_guild(self, guild_id: int) -> Optional[discord.Guild]:
        try:
            return self.get_guild(guild_id) or await self.fetch_guild(guild_id)
        except discord.Forbidden | discord.HTTPException:
            return None

    async def maybe_fetch_channel(self, channel_id: int) -> Optional[abc.GuildChannel | abc.PrivateChannel | discord.Thread]:
        try:
            return self.get_channel(channel_id) or await self.fetch_channel(channel_id)
        except discord.HTTPException | discord.NotFound | discord.Forbidden:
            return None

    async def maybe_fetch_member(self, source: discord.Guild | discord.Thread, member_id: int = None) -> Optional[discord.Member]:
        try:
            source.get_member(member_id) or await source.fetch_member(member_id)
        except discord.HTTPException | discord.NotFound | discord.Forbidden:
            return None

    async def maybe_fetch_user(self, user_id: int) -> Optional[discord.User]:
        try:
            return self.get_user(user_id) or await self.fetch_user(user_id)
        except discord.HTTPException | discord.NotFound:
            return None

    @staticmethod
    def current(current: str) -> typing.Literal["%"] | str:
        return "%" if not current else current

    async def events(self, guild_int: int, event: _events) -> bool:
        """Returns True/False to determine if event is enabled in guild"""
        if not self._event_toggles.get(guild_int):  # Adds guild to cache with no events
            self._event_toggles[guild_int] = {}

        if self._event_toggles[guild_int].get(event.name) is None:  # Adds event to guild on request
            toggle_value = await self.fetchval(f"SELECT {event.name} FROM events WHERE guild = $1", guild_int)
            self._event_toggles[guild_int][event.name] = toggle_value

        return self._event_toggles[guild_int][event.name]  # returns event bool


async def start() -> typing.NoReturn:
    await asyncio.gather(discord_bot.start(environ.get("discord")), return_exceptions = False)

if __name__ == "__main__":
    load_dotenv()
    discord.utils.setup_logging(level = INFO)
    intents = discord.Intents(
        auto_moderation_execution = True,
        bans = True,
        emojis = True,
        guilds = True,
        integrations = True,
        invites = True,
        members = True,
        messages = True,
        voice_states = True,
        webhooks = True
    )
    discord_bot = WorstBot(command_prefix = discord_commands.when_mentioned,
                           activity = discord.Streaming(name = "With ones and zeros", url = "http://definitelynotarickroll.lol/", game = "a little bit of trolling", platform = "YouTube"),
                           intents = intents,
                           owner_id = environ.get("owner"))
    asyncio.run(start())
