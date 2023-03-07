from datetime import date

import discord
from dateutil.relativedelta import relativedelta
from discord import Interaction, app_commands
from discord.app_commands import Range
from discord.ext import commands, tasks

from WorstBot import WorstBot
from modules import EmbedGen, Paginators


class BirthdayAlert(commands.GroupCog, name = "birthday"):

    def __init__(self, bot: WorstBot):
        self.bot = bot
        self.birthdays: dict[discord.User, date] | None = None

    async def cog_load(self) -> None:
        await self.bot.execute("CREATE TABLE IF NOT EXISTS birthdaychannel(guild BIGINT PRIMARY KEY, channel BIGINT NOT NULL)")
        await self.bot.execute("CREATE TABLE IF NOT EXISTS birthdays(member BIGINT PRIMARY KEY, birthday DATE)")
        self.birthdays = {}
        self.populate_birthdays.start()

    async def cog_unload(self) -> None:
        del self.birthdays
        self.birthday_check.stop()

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.logger.info("BirthdayAlert cog online")

    @app_commands.command(name = "alert")
    async def BirthdayAdd(self, interaction: Interaction, month: Range[int, 1, 12] = None, day: Range[int, 1, 31] = None):
        """Add or remove your birthday GLOBALLY

        :param interaction: Internal Discord Interaction
        :param month: 1-12: The Month of your birthday
        :param day: 1-31: The Day of your birthday
        """
        if not (month and day):
            await self.bot.execute("DELETE FROM birthdays WHERE member = $1", interaction.user.id)
            self.birthdays.pop(interaction.user, None)
            return await interaction.response.send_message(f"Birthday alert removed", ephemeral = True)
        birthday = date(year = date.today().year, month = month, day = day)
        if birthday < date.today():
            birthday += relativedelta(years = +1)
        await self.bot.execute("INSERT INTO birthdays(member, birthday) VALUES($1, $2) ON CONFLICT(member) DO UPDATE SET birthday = excluded.birthday", interaction.user.id, birthday)
        self.birthdays[interaction.user] = birthday
        await interaction.response.send_message(f"you will be alerted of your birthday on {birthday.strftime('%d/%m/%Y')}", ephemeral = True)

    @app_commands.command(name = "list")
    async def BirthdayList(self, interaction: Interaction):
        """List all the Birthdays WorstBot knows about in the server

        :param interaction: Internal interaction
        """
        birthdays = [""]
        for user, birthday in self.birthdays.items():
            if user not in interaction.guild.members:
                continue

            string = f"{user.mention}: {birthday.strftime('%d/%m')}\n"
            if len(birthdays[-1] + string) < 4000:
                birthdays[-1] += string
            else:
                birthdays.append(string)

        embed_list = EmbedGen.SimpleEmbedList(title = "Birthdays", descriptions = birthdays)
        view = Paginators.ButtonPaginatedEmbeds(embed_list = embed_list)
        await interaction.response.send_message(view = view, embed = embed_list[0], ephemeral = True)
        view.response = await interaction.original_response()

    @tasks.loop(count = 1)
    async def populate_birthdays(self):
        table = await self.bot.fetch("SELECT * FROM birthdays")
        for user_id, birthday in table:
            user = await self.bot.maybe_fetch_user(user_id)
            self.birthdays[user] = birthday
        self.bot.logger.debug(self.birthdays)

    @tasks.loop(hours = 1)
    async def birthday_check(self):
        birthday_channels = await self.bot.fetch("SELECT * FROM birthdaychannel")
        if not birthday_channels:
            return
        birthday_channels = {await self.bot.maybe_fetch_guild(guild_id): await self.bot.maybe_fetch_channel(channel_id) for guild_id, channel_id in birthday_channels}
        for user, birthday in self.birthdays.items():  # type: discord.User, date
            if birthday != discord.utils.utcnow().date():
                continue

            for guild, channel in birthday_channels.items():  # type: discord.Guild, discord.TextChannel
                if user not in guild.members:
                    continue

                permissions = channel.permissions_for(guild.me)
                if permissions.send_messages and permissions.view_channel:
                    await channel.send(f"Today is {user.mention}'s birthday, dont forget to send them a happy birthday message")

            await self.bot.execute("UPDATE birthdays SET birthday = birthday + INTERVAL '1 year' WHERE member = $1", user.id)
            self.birthdays[user] += relativedelta(years = 1)

    @populate_birthdays.before_loop
    async def before_birthdays(self):
        await self.bot.wait_until_ready()

    @populate_birthdays.after_loop
    async def before_check(self):
        await self.birthday_check.start()

async def setup(bot):
    await bot.add_cog(BirthdayAlert(bot))
