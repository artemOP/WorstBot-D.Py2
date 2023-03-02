from datetime import date

import discord
from asyncpg import Record
from dateutil.relativedelta import relativedelta
from discord import Interaction, app_commands
from discord.app_commands import Range
from discord.ext import commands, tasks

from WorstBot import WorstBot
from modules.EmbedGen import SimpleEmbedList
from modules.Paginators import ButtonPaginatedEmbeds


class BirthdayAlert(commands.GroupCog, name = "birthday"):

    def __init__(self, bot: WorstBot):
        self.bot = bot

    async def cog_load(self) -> None:
        await self.bot.execute("CREATE TABLE IF NOT EXISTS birthdaychannel(guild BIGINT PRIMARY KEY, channel BIGINT NOT NULL)")
        await self.bot.execute("CREATE TABLE IF NOT EXISTS birthdays(guild BIGINT, member BIGINT, birthday DATE, PRIMARY KEY(guild, member))")
        self.BirthdayCheck.start()

    async def cog_unload(self) -> None:
        self.BirthdayCheck.stop()

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.logger.info("BirthdayAlert cog online")

    @app_commands.command(name = "alert", description = "Add or remove your Birthday")
    async def BirthdayAdd(self, interaction: Interaction, month: Range[int, 1, 12] = None, day: Range[int, 1, 31] = None):
        if not (month or day):
            await self.bot.execute("DELETE FROM birthdays WHERE member = $1", interaction.user.id)
            return await interaction.response.send_message(f"Birthday removed from bot", ephemeral = True)
        birthday = date(year = date.today().year, month = month, day = day)
        if birthday < date.today():
            birthday += relativedelta(years = +1)
        await self.bot.execute("INSERT INTO birthdays(guild, member, birthday) VALUES($1, $2, $3) ON CONFLICT(guild, member) DO UPDATE SET birthday = excluded.birthday", interaction.guild_id, interaction.user.id, birthday)
        await interaction.response.send_message(f"you will be alerted of your birthday on {birthday.strftime('%d/%m/%Y')}", ephemeral = True)

    @app_commands.command(name = "list")
    async def BirthdayList(self, interaction: Interaction):
        table: list[Record] = await self.bot.fetch("SELECT member, birthday FROM birthdays WHERE guild = $1 ORDER BY birthday", interaction.guild_id)
        descriptions: list[str] = [""]
        for member, birthday in table:
            member = await self.bot.maybe_fetch_member(interaction.guild, member)
            birthday = birthday.strftime("%d/%m")
            if len(descriptions[-1] + str(member) + birthday) < 4000:
                descriptions[-1] += f"{member.mention}: {birthday}\n"
            else:
                descriptions.append(f"{member.mention}: {birthday}\n")
        embed_list = SimpleEmbedList(title = "Birthdays", descriptions = descriptions)

        view = ButtonPaginatedEmbeds(timeout = 30, embed_list = embed_list)
        await interaction.response.send_message(view = view, embed = embed_list[0], ephemeral = True)
        view.response = await interaction.original_response()

    @tasks.loop(hours = 1, reconnect = True)
    async def BirthdayCheck(self):
        birthdays = await self.bot.fetch("SELECT * FROM birthdays WHERE birthday<=NOW()::DATE")
        if not birthdays:
            return
        for birthday in birthdays:
            if await self.bot.events(birthday["guild"], self.bot._events.birthdays) is False:
                continue

            guild = await self.bot.maybe_fetch_guild(birthday["guild"])
            if not guild:
                continue

            channel = await self.bot.fetchval("SELECT channel FROM birthdaychannel WHERE guild = $1", guild.id)
            channel = await self.bot.maybe_fetch_channel(channel)

            member = await self.bot.maybe_fetch_member(guild, birthday["member"])
            if not (channel and member):
                continue

            permissions = channel.permissions_for(guild.me)
            if permissions.send_messages and permissions.view_channel:
                await channel.send(f"Today is {member.mention}'s birthday, dont forget to send them a happy birthday message")
            await self.bot.execute("UPDATE birthdays SET birthday = birthday + INTERVAL '1 year' WHERE member = $1", member.id)

    @BirthdayCheck.before_loop
    async def Before(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(BirthdayAlert(bot))
