from __future__ import annotations

import textwrap
from datetime import datetime, UTC
from typing import TYPE_CHECKING

import discord
from discord.ext import commands, tasks
from discord.utils import MISSING, format_dt

if TYPE_CHECKING:
    from discord import User

    from .. import Bot


class Logging(commands.Cog):
    attributes: dict[str, str] = {"INFO": "\U00002139\U0000fe0f", "WARNING": "\U000026a0\U0000fe0f"}

    def __init__(self, bot: Bot):
        self.bot = bot
        self.logger = self.bot.log_handler.getChild(self.qualified_name)

        self.user: User | None = MISSING

        if url := self.bot.config["discord"]["webhook"]:
            self.webhook = discord.Webhook.from_url(url, session=bot.http_session, client=bot)
        else:
            bot.log_handler.warning("Not enabling webhook logging due to missing webhook URL")
            self.webhook = None

    async def cog_load(self) -> None:
        if self.webhook:
            self.logging_loop.start()
        self.logger.info(f"{self.qualified_name} cog loaded")

    async def cog_unload(self) -> None:
        if self.webhook:
            self.logging_loop.cancel()
        self.logger.info(f"{self.qualified_name} cog unloaded")

    @tasks.loop(seconds=0)
    async def logging_loop(self) -> None:
        assert self.webhook, "Config webhook not set"
        to_log = await self.bot.logging_queue.get()
        if "rate limited" in to_log.message:
            return
        emoji = self.attributes.get(to_log.levelname, "\N{CROSS MARK}")
        dt = datetime.fromtimestamp(to_log.created, UTC)

        message = textwrap.shorten(f"{emoji} {format_dt(dt)}\n{to_log.message}", width=1990)
        embed = to_log.__dict__.get("embed") or MISSING

        if self.bot.user:
            avatar_url = self.bot.user.display_avatar.url
        else:
            avatar_url = MISSING
        await self.webhook.send(message, username="WorstBot Logging", avatar_url=avatar_url, embed=embed)


async def setup(bot: Bot):
    await bot.add_cog(Logging(bot))
