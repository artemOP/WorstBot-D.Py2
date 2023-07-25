from __future__ import annotations

from asyncio import sleep
from datetime import timedelta
from math import sqrt
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands
from discord.utils import utcnow

from modules import EmbedGen, Paginators

if TYPE_CHECKING:
    from WorstBot import WorstBot
    from discord import User, Member, Interaction, Guild
    from datetime import datetime

class Chatter:
    def __init__(self, user: User | Member, xp: int, last_message: datetime):
        self.user: User | Member = user
        self._xp: int = xp
        self._level: int = 0
        self.update_level()
        self.last_message: datetime = last_message

    @property
    def xp(self) -> int:
        return self._xp

    @property
    def level(self) -> int:
        return self._level

    def update_level(self) -> bool:
        level = int((sqrt(1 + 8 * self.xp / 5) - 1) / 2)
        if level > self._level:
            self._level = level
            return True
        return False

    def add_xp(self, value: int) -> bool:
        self._xp += value
        return self.update_level()

    def __repr__(self) -> str:
        return f"<Chatter user={self.user} xp={self.xp} level={self.level} last_message={self.last_message}>"

    def __hash__(self) -> int:
        return hash(self.user)

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, Chatter):
            return False
        return self.user == o.user


class ChatterXP(commands.GroupCog, name = "chatter-xp"):

    def __init__(self, bot: WorstBot):
        self.bot = bot
        self.logger = self.bot.logger.getChild(self.qualified_name)
        self.chatters: dict[User | Member, Chatter] = {}

    async def cog_load(self) -> None:
        await self.bot.execute("CREATE TABLE IF NOT EXISTS chatter_xp(user_id BIGINT PRIMARY KEY, xp INT DEFAULT 0, last_message TIMESTAMPTZ DEFAULT NOW())")
        self.logger.info(f"{self.qualified_name} cog loaded")

    async def cog_unload(self) -> None:
        self.logger.info(f"{self.qualified_name} cog unloaded")

    async def prepare_guild(self, guild: Guild) -> list[Chatter]:
        self.logger.debug(f"Preparing guild {guild}")
        chatters = []
        for member in guild.members:
            if member.bot:
                continue
            chatter = await self.get_chatter(member)
            if chatter.xp > 1:
                chatters.append(chatter)
            await sleep(0)
        return chatters

    async def get_chatter(self, key: User | Member):
        if key in self.chatters:
            self.logger.debug(f"Found {key} in cache")
            return self.chatters[key]

        row = await self.bot.fetchrow("SELECT * FROM chatter_xp WHERE user_id = $1", key.id)
        if row:
            chatter = Chatter(key, row["xp"], row["last_message"])
            self.chatters[key] = chatter
            self.logger.debug(f"Found {key} in database")
            return chatter
        else:
            chatter = Chatter(key, 0, utcnow())
            self.chatters[key] = chatter
            await self.bot.execute("INSERT INTO chatter_xp(user_id) VALUES($1)", key.id)
            self.logger.debug(f"Created {key} in database")
            return chatter

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.guild is None:
            self.logger.debug(f"Message from {message.author} in DMs ignored")
            return
        if message.author.bot:
            self.logger.debug(f"Message from {message.author} bot ignored")
            return

        chatter = await self.get_chatter(message.author)
        if chatter.last_message + timedelta(minutes = 1) > utcnow():
            self.logger.debug(f"Message from {message.author} too soon, time remaining: {chatter.last_message + timedelta(minutes = 1) - utcnow()}")
            return

        chatter.last_message = utcnow()
        level_up = chatter.add_xp(1)
        await self.bot.execute("UPDATE chatter_xp SET xp = $1, last_message = $2 WHERE user_id = $3", chatter.xp, chatter.last_message, chatter.user.id)

        if level_up:
            await message.channel.send(
                embed = EmbedGen.FullEmbed(
                    author = {"name": message.author.name, "icon_url": message.author.display_avatar.url},
                    title = "Level Up!",
                    fields = [
                        EmbedGen.EmbedField(name = "level", value = chatter.level),
                        EmbedGen.EmbedField(name = "xp", value = chatter.xp),
                    ]
                ),
                delete_after = 60)

    @app_commands.command(name = "progress")
    async def current_xp(self, interaction: Interaction):
        """View your current xp and level.

        :param interaction:
        :return:
        """
        await interaction.response.defer(ephemeral = True)
        chatter = await self.get_chatter(interaction.user)
        next_level = int((5 * (chatter.level + 1) * (chatter.level + 2)) / 2)
        await interaction.followup.send(
            embed = EmbedGen.FullEmbed(
                author = {"name": interaction.user.name, "icon_url": interaction.user.display_avatar.url},
                title = "Current XP",
                fields = [
                    EmbedGen.EmbedField(name = "level", value = chatter.level),
                    EmbedGen.EmbedField(name = "xp", value = chatter.xp),
                    EmbedGen.EmbedField(name = "level progress", value = f"{chatter.xp/next_level:.2%}")
                ]
            )
        )

    @app_commands.command(name = "leaderboard")
    async def leaderboard(self, interaction: Interaction):
        """Earn xp by sending messages, view your spot on the leaderboard here.

        :param interaction:
        :return:
        """
        await interaction.response.defer(ephemeral = True)
        chatters = await self.prepare_guild(interaction.guild)
        chatters.sort(key = lambda chatter: chatter.xp, reverse = True)

        embed_list = EmbedGen.EmbedFieldList(
            title = "Leaderboard",
            fields = [
                EmbedGen.EmbedField(name = f"{i + 1}: {chatter.user.display_name}", value = f"Level {chatter.level} ({chatter.xp} xp)", inline = False)
                for i, chatter in enumerate(chatters)
            ],
            max_fields = 10
        )
        view = Paginators.ButtonPaginatedEmbeds(embed_list)
        await interaction.followup.send(view = view, embed = embed_list[0], ephemeral = True)
        view.response = await interaction.original_response()

async def setup(bot):
    await bot.add_cog(ChatterXP(bot))
