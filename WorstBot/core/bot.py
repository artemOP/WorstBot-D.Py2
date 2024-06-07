from __future__ import annotations

from pathlib import Path
import re
from typing import TYPE_CHECKING

from discord.app_commands import Group
from discord.ext import commands, tasks

import wavelink

from .tree import CommandTree

if TYPE_CHECKING:
    from asyncio import Queue
    from logging import LogRecord, Logger
    from typing import Any, Generator, Iterator, TypeAlias

    from aiohttp import ClientSession
    from discord import BaseActivity, Guild, Intents, Object, Emoji
    from discord.app_commands import AppCommand, Command, ContextMenu

    from .enums import _events
    from .. import Pool

    from discord.ext.commands._types import MaybeAwaitableFunc

    Prefix: TypeAlias = str | Iterator[str] | MaybeAwaitableFunc


class Bot(commands.Bot):
    log_handler: Logger
    logging_queue: Queue[LogRecord]
    pool: Pool
    http_session: ClientSession
    tree: CommandTree

    def __init__(
        self,
        prefix: Prefix,
        activity: BaseActivity,
        intents: Intents,
        owner_ids: list[int],
        config: dict[str, Any],
        **kwargs: Any,
    ) -> None:
        super().__init__(
            command_prefix=prefix,
            activity=activity,
            intents=intents,
            owner_ids=owner_ids,
            tree_cls=CommandTree,
            **kwargs,
        )
        self.config = config
        self._event_toggles: dict[Object, dict[_events, bool]] = {}
        self.custom_emoji: list[Emoji] = []

    async def setup_hook(self) -> None:
        assert self.config["discord"]["extension_path"], "Config extension path not set"
        cog_dir = Path(self.config["discord"]["extension_path"])

        for file in self.collect_cogs(cog_dir):
            extension = str(file.relative_to("./"))[:-3]
            extension = re.sub(r"(\\)|(/)", ".", extension)
            try:
                await self.load_extension(extension)
            except commands.NoEntryPointError:
                self.log_handler.debug("Skipping extension %s", extension)
            except Exception as e:
                self.log_handler.exception(f"Failed to load extension {extension}", exc_info=e)

        if self.config["lavalink"]["enabled"] is True:
            nodes = [wavelink.Node(uri=self.config["lavalink"]["uri"], password=self.config["lavalink"]["password"])]
            await wavelink.Pool.connect(nodes=nodes, client=self, cache_capacity=100)

    async def on_ready(self) -> None:
        self.log_handler.info("Bot Ready")

    def collect_cogs(self, root: Path) -> Generator[Path, None, None]:
        for file in root.iterdir():
            if file.match("[!-|_]*.py"):
                yield file
            elif file.is_dir():
                yield from self.collect_cogs(file)

    async def event_enabled(self, guild: Object, event: _events) -> bool:
        assert self.config["discord"]["toggles"]["tasks"], "Config toggles not set"
        if not self.config["discord"]["toggles"]["tasks"]:
            return False

        if guild not in self._event_toggles:
            self._event_toggles[guild] = {}

        if event not in self._event_toggles[guild]:
            toggles = await self.pool.fetchrow("SELECT * FROM event_toggles WHERE guild_id = $1", guild.id) or {}
            self._event_toggles[guild][event] = toggles.get(event, False)

        return self._event_toggles[guild][event]

    @tasks.loop(count=1)
    async def prepare_emoji(self) -> None:
        assert self.config["discord"]["emoji_server_ids"], "Config emoji servers not set"

        for guild_id in self.config["discord"]["emoji_server_ids"]:
            guild: Guild | None = self.get_guild(guild_id)

            if guild is None:
                self.log_handler.warning("Guild with ID %s not found", guild_id)
                continue

            self.custom_emoji.extend(guild.emojis)
        self.log_handler.debug(f"{len(self.custom_emoji)} custom emoji loaded")

    @tasks.loop(count=1)
    async def prepare_mentions(self) -> None:
        for guild in [*self.guilds, None]:
            guild_id = None if not guild else guild.id
            fetched_commands = await self.tree.fetch_commands(guild=guild)

            for fetched_command in fetched_commands:
                command = self.tree.get_command(
                    fetched_command.name,
                    guild=guild,
                    type=fetched_command.type,
                )

                if command is None:
                    continue

    @staticmethod
    async def add_to_extra(
        fetched_command: AppCommand,
        command: Command[Any, ..., Any] | ContextMenu | Group,
        *,
        child: bool = False,
    ) -> None:
        if isinstance(command, Group):
            for subcommand in command.walk_commands():
                await Bot.add_to_extra(fetched_command, subcommand, child=True)
            return

        if child:
            mention = f"</{command.qualified_name}:{fetched_command.id}>"
        else:
            mention = fetched_command.mention

        if fetched_command.guild_id:
            command.extras[f"mention for {fetched_command.guild_id}"] = mention
        else:
            command.extras["mention"] = mention

    @prepare_emoji.before_loop
    @prepare_mentions.before_loop
    async def before_task(self) -> None:
        await self.wait_until_ready()
