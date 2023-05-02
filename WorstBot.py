import asyncio
import datetime
import typing
from typing import Any, Optional
from enum import StrEnum, auto
import logging
from logging import ERROR, INFO
import pathlib
import re
from math import sqrt, floor

import discord
from discord import abc, app_commands, AppCommandType
from discord.ext import commands as discord_commands, tasks
from discord.app_commands import Group, Command, ContextMenu

import asyncpg
from aiohttp import ClientSession
from dotenv import dotenv_values
import orjson

emoji_servers = (
    1099821517350637629,
    1099836627171430400,
    1099836647132119062,
    1099836641570471946,
    1099836635627126876,
)

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

    def __init__(self, command_prefix, activity, intents, owner_id, env_values):
        super().__init__(command_prefix, intents = intents, owner_id = owner_id, activity = activity, tree_cls = CommandTree)
        self.pool: Optional[asyncpg.Pool] = None
        self.session: Optional[ClientSession] = None
        self._event_toggles = {}
        self._events = _events
        self.logger = logging.getLogger(self.__class__.__name__)
        self.cog_dir = pathlib.Path("./cogs")
        self.dotenv: dict[str, Optional[str]] = env_values
        self.custom_emoji: list[discord.Emoji] = []

    async def setup_hook(self) -> None:
        self.pool = await asyncpg.create_pool(database = self.dotenv.get("postgresdb"), user = self.dotenv.get("postgresuser"), password = self.dotenv.get("postgrespassword"), command_timeout = 10, min_size = 1, max_size = 100, loop = self.loop)
        self.session = ClientSession(loop = self.loop, json_serialize=lambda x: orjson.dumps(x).decode())
        self.prepare_mentions.start()
        self.load_emoji.start()

        for file in self.collect_cogs(self.cog_dir):
            extension = str(file.relative_to("./"))[:-3]
            extension = re.sub(r"(\\)|(/)", ".", extension)
            await self.load_extension(extension)

    def collect_cogs(self, root: pathlib.Path) -> typing.Generator[pathlib.Path, None, None]:
        for file in root.iterdir():
            if file.match("[!-|_]*.py"):
                yield file
            elif file.is_dir():
                yield from self.collect_cogs(file)

    async def on_ready(self):
        self.logger.warning(f"Connected as {self.user} at {datetime.datetime.now().strftime('%d/%m/%y %H:%M')}")

    async def post(self, *, url: str, params: dict = None, headers: dict = None) -> dict:
        async with self.session.post(url = url, params = params, headers = headers) as response:
            content = await response.json()
            content["status"] = response.status
            return content

    async def get(self, *, url: str, params: dict = None, headers: dict = None) -> dict:
        async with self.session.get(url = url, params = params, headers = headers) as response:
            try:
                content: list | dict = await response.json()
            except orjson.JSONDecodeError:
                content = {}
            if isinstance(content, list):
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

    async def executemany(self, sql: str, args: typing.Iterable[typing.Sequence]) -> Optional[Any]:
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                return await conn.executemany(sql, args)

    async def maybe_fetch_guild(self, guild_id: int) -> Optional[discord.Guild]:
        try:
            return self.get_guild(guild_id) or await self.fetch_guild(guild_id)
        except (discord.Forbidden, discord.HTTPException):
            return

    async def maybe_fetch_channel(self, channel_id: int) -> Optional[abc.GuildChannel | abc.PrivateChannel | discord.Thread]:
        try:
            return self.get_channel(channel_id) or await self.fetch_channel(channel_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            return

    async def maybe_fetch_event(self, guild: discord.Guild, event_id: int) -> Optional[discord.ScheduledEvent]:
        try:
            return guild.get_scheduled_event(event_id) or await guild.fetch_scheduled_event(event_id)
        except (discord.NotFound, discord.HTTPException):
            return

    async def maybe_fetch_member(self, source: discord.Guild | discord.Thread, member_id: int = None) -> Optional[discord.Member]:
        try:
            return source.get_member(member_id) or await source.fetch_member(member_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            return

    async def maybe_fetch_user(self, user_id: int) -> Optional[discord.User]:
        try:
            return self.get_user(user_id) or await self.fetch_user(user_id)
        except (discord.NotFound, discord.HTTPException):
            return

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

    @staticmethod
    def pair(guild_id: int, member_id: int) -> int:
        """Returns a unique id for a guild and member using cantor pairing function
        
        :param guild_id: Guild to pair
        :param member_id: Member to pair
        :return: combined id
        """
        return int((((guild_id + member_id) * (guild_id + member_id + 1)) / 2) + member_id)

    def unpair(self, pair: int) -> tuple[Optional[discord.Guild], Optional[discord.Member]]:
        """Returns the guild and member from a paired id

        :param pair: Paired id
        :return: guild, member
        """
        w = floor((sqrt(8 * pair + 1) - 1) / 2)
        y = int(pair - (w ** 2 + w) / 2)
        x = int(w - y)
        return self.get_guild(x), self.get_user(y)

    @staticmethod
    async def add_to_extra(command: Command, mention: str, guild_id: Optional[int] = None) -> None:
        if guild_id:
            command.extras[f"mention for {guild_id}"] = mention
        else:
            command.extras[f"mention"] = mention

    @tasks.loop(count = 1)
    async def prepare_mentions(self):
        for guild in [*self.guilds, None]:
            for fetched_command in await self.tree.fetch_commands(guild = guild):
                command = self.tree.get_command(fetched_command.name, guild = guild, type = fetched_command.type)
                if command is None:
                    self.logger.debug("command not found")
                    continue
                await self.add_to_extra(command, fetched_command.mention, None if not guild else guild.id)
                if isinstance(command, Group):
                    for child in command.walk_commands():
                        await self.add_to_extra(child, f"</{child.qualified_name}:{fetched_command.id}>", None if not guild else guild.id)

    @tasks.loop(count = 1)
    async def load_emoji(self):
        for guild_id in emoji_servers:
            guild = self.get_guild(guild_id)
            if not guild:
                self.logger.error(f"Failed to get guild {guild_id}")
                continue
            for emoji in guild.emojis:
                self.custom_emoji.append(emoji)
        self.logger.info(f"Loaded {len(self.custom_emoji)} custom emoji")

    @prepare_mentions.before_loop
    @load_emoji.before_loop
    async def before_prepare_mentions(self):
        await self.wait_until_ready()

class CommandTree(app_commands.CommandTree):
    def __init__(self, bot):
        super().__init__(bot)

    async def interaction_check(self, interaction: discord.Interaction, /) -> bool:
        if not interaction.guild:
            await interaction.response.send_message("This bot cannot be used in dm's, sorry", ephemeral = True)
            return False
        return True

    def get_command(self, command_name: str, /, *, guild: Optional[abc.Snowflake] = None, type: AppCommandType = AppCommandType.chat_input) -> Optional[Command | ContextMenu | Group]:
        command = super().get_command(command_name, guild = guild, type = type)
        if not command:
            command = super().get_command(command_name, guild = None, type = type)
        return command

    def get_commands(self, *, guild: Optional[abc.Snowflake] = None, type: Optional[AppCommandType] = None) -> list[Command | ContextMenu | Group]:
        guild_commands = super().get_commands(guild = guild, type = type)
        global_commands = super().get_commands(guild = None, type = type)
        for global_command in global_commands:
            if global_command.name not in [guild_command.name for guild_command in guild_commands]:
                guild_commands.append(global_command)
        return guild_commands

    @staticmethod
    def flatten_commands(command_list: list[app_commands.Command | app_commands.Group | discord_commands.Command | discord_commands.Group]) -> list[app_commands.Command | discord_commands.Command]:
        flat_commands = []
        for command in command_list:
            if isinstance(command, app_commands.Group | discord_commands.Command):
                for child in command.walk_commands():
                    flat_commands.append(child)
            else:
                flat_commands.append(command)
        return flat_commands

async def start() -> typing.NoReturn:
    await asyncio.gather(discord_bot.start(env_values.get("discord")), return_exceptions = False)

if __name__ == "__main__":
    discord.utils.setup_logging(level = INFO)
    logging.getLogger("discord.gateway").setLevel(ERROR)
    logging.getLogger("discord.voice_client").setLevel(ERROR)
    logging.getLogger("matplotlib.category").setLevel(ERROR)
    intents = discord.Intents(
        bans = True,
        emojis = True,
        guilds = True,
        integrations = True,
        invites = True,
        members = True,
        guild_messages = True,
        guild_scheduled_events = True,
        voice_states = True,
        webhooks = True
    )
    env_values = dotenv_values()
    discord_bot = WorstBot(command_prefix = discord_commands.when_mentioned,
                           activity = discord.Streaming(name = "With ones and zeros", url = "http://definitelynotarickroll.lol/", game = "a little bit of trolling", platform = "YouTube"),
                           intents = intents,
                           owner_id = int(env_values.get("owner")),
                           env_values = env_values)
    asyncio.run(start())
