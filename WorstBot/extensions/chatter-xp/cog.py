from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands, utils
from discord.ext import commands

from ...core._types import LRU
from ...core.enums import Events_
from . import Chatter

if TYPE_CHECKING:
    from datetime import datetime
    from typing import Any

    from discord import Guild, Interaction, Member, Message, TextChannel

    from WorstBot import Bot

LEADERBOARD_SIZE: int = 99
LOG_STR: str = "{user_name} (id: {user_id}), {guild_name} (id: {guild_id}) found in {source}"

with open("WorstBot/extensions/chatter-xp/leaderboard.sql", "r") as f:
    leaderboard_sql = f.read()


@app_commands.guild_only()
class ChatterXP(commands.GroupCog, name="chatter"):

    def __init__(self, bot: Bot):
        self.bot = bot
        self.logger = self.bot.log_handler.getChild(self.qualified_name)
        self.logger.setLevel(10)
        self.chatters: LRU[Chatter] = LRU(max_size=50)

    async def cog_load(self) -> None:
        self.logger.info(f"{self.qualified_name} cog loaded")

    async def cog_unload(self) -> None:
        self.logger.info(f"{self.qualified_name} cog unloaded")

    async def set_chatter_info(self, member: Member, message_timestamp: datetime | None = None) -> None:
        await self.bot.pool.execute(
            "INSERT INTO chatter(member, message_timestamp) VALUES ($1, COALESCE($2, NOW()))",
            (member.guild.id, member.id),
            message_timestamp,
        )

    async def fetch_chatter_info(self, member: Member) -> dict[str, Any]:
        row = await self.bot.pool.fetchrow(
            "SELECT member, count(*) as xp, max(message_timestamp) as last_message FROM chatter WHERE member = $1::MEMBER GROUP BY member",
            (member.guild.id, member.id),
        )
        if row:
            return dict(row)
        else:
            return {}

    async def get_chatter(self, member: discord.Member) -> Chatter:
        if chatter := self.chatters.get(member):  # type: ignore
            self.logger.debug(
                LOG_STR.format(
                    user_name=member.name,
                    user_id=member.id,
                    guild_name=member.guild.name,
                    guild_id=member.guild.id,
                    source="cache",
                )
            )
            return chatter

        chatter_info = await self.fetch_chatter_info(member)
        if chatter_info:
            self.logger.debug(
                LOG_STR.format(
                    user_name=member.name,
                    user_id=member.id,
                    guild_name=member.guild.name,
                    guild_id=member.guild.id,
                    source="database",
                )
            )
            return Chatter(member, chatter_info["xp"], chatter_info["last_message"])

        chatter = Chatter(member, 0, utils.utcnow())
        self.chatters[chatter] = utils.utcnow()
        await self.set_chatter_info(member)
        self.logger.debug(
            LOG_STR.format(
                user_name=member.name,
                user_id=member.id,
                guild_name=member.guild.name,
                guild_id=member.guild.id,
                source="NEW",
            )
        )

        return chatter

    async def prepare_leaderboard(self, user: discord.Member) -> dict[int, Chatter]:
        data = await self.bot.pool.fetch(leaderboard_sql, user.guild.id, user.id, LEADERBOARD_SIZE)

        if not data:
            return {}

        leaderboard: dict[int, Chatter] = {}
        for row in data:
            print(row)
            member = user.guild.get_member(row["user_id"])
            if not member:
                continue

            chatter = Chatter(member, row["xp"], row["last_message"])
            if chatter not in self.chatters:
                self.chatters[chatter] = chatter.last_message

            leaderboard[row["rank"]] = chatter
        return leaderboard

    async def send_level_up(self, channel: TextChannel, author: Member, xp: int, level: int) -> None: ...

    async def send_current(self) -> None: ...

    async def send_leaderboard(self) -> None: ...

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        if not message.guild:
            self.logger.debug(f"Message from {message.author} in DMs ignored")
            return
        elif message.author.bot:
            self.logger.debug(f"Message from {message.author} bot ignored")
            return
        elif not await self.bot.event_enabled(message.guild, Events_.chatter_xp):
            self.logger.debug(f"{Events_.chatter_xp} disabled for {message.guild}")
            return

        assert isinstance(message.author, discord.Member)
        assert isinstance(message.channel, discord.TextChannel)
        chatter = await self.get_chatter(message.author)

        if not chatter.can_xp(message.created_at):
            self.logger.debug(f"{message.author} can't gain xp yet due to ratelimit")
            return

        await self.set_chatter_info(message.author, message.created_at)
        level_up: bool = chatter.add_xp(1)
        if level_up:
            await self.send_level_up(message.channel, message.author, chatter.xp, chatter.level)

    @app_commands.command(name="xp")
    async def current(self, interaction: Interaction[Bot]):
        assert isinstance(interaction.user, discord.Member)
        chatter = await self.get_chatter(interaction.user)
        next_level_xp = Chatter.level_to_xp(chatter.level + 1)
        # todo: send embed

    @app_commands.command(name="leaderboard")
    async def leaderboard(self, interaction: Interaction[Bot]):
        assert isinstance(interaction.user, discord.Member)
        leaderboard = await self.prepare_leaderboard(interaction.user)
        # todo: Send paginated embed


async def setup(bot: Bot):
    await bot.add_cog(ChatterXP(bot))
