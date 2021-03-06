import discord
from discord import app_commands, Interaction, ui
from discord.app_commands import Range
from discord.ext import commands, tasks
from datetime import date, time
from dateutil.relativedelta import relativedelta
from asyncpg import Record


class BirthdayView(ui.View):
    def __init__(self, timeout: int, embedlist: list[discord.Embed]):
        super().__init__(timeout = timeout)
        self.response = None
        self.embedlist = embedlist
        self.page = 0

    async def on_timeout(self) -> None:
        await self.response.edit(view = None)

    @ui.button(label = 'First page', style = discord.ButtonStyle.red)
    async def first(self, interaction: Interaction, button: ui.Button):
        await interaction.response.edit_message(embed = self.embedlist[0])
        self.page = 0

    @ui.button(label = 'Previous page', style = discord.ButtonStyle.red)
    async def previous(self, interaction: Interaction, button: ui.Button):
        if self.page >= 1:
            self.page -= 1
            await interaction.response.edit_message(embed = self.embedlist[self.page])
        else:
            self.page = len(self.embedlist) - 1
            await interaction.response.edit_message(embed = self.embedlist[self.page])

    @ui.button(label = 'Stop', style = discord.ButtonStyle.grey)
    async def exit(self, interaction: Interaction, button: ui.Button):
        await self.on_timeout()

    @ui.button(label = 'Next Page', style = discord.ButtonStyle.green)
    async def next(self, interaction: Interaction, button: ui.Button):
        self.page += 1
        if self.page > len(self.embedlist) - 1:
            self.page = 0
        await interaction.response.edit_message(embed = self.embedlist[self.page])

    @ui.button(label = 'Last Page', style = discord.ButtonStyle.green)
    async def last(self, interaction: Interaction, button: ui.Button):
        self.page = len(self.embedlist) - 1
        await interaction.response.edit_message(embed = self.embedlist[self.page])


class BirthdayAlert(commands.GroupCog, name = "birthday"):

    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot
        self.BirthdayCheck.start()

    @staticmethod
    async def EmbedFormer(Birthday: dict) -> list[discord.Embed]:
        EmbedList: list[discord.Embed] = []
        description = ""
        for item in Birthday.items():
            if len(description + str(item[0]) + item[1].strftime("%d/%m")) < 4000:
                description += f"{item[0].mention}: {item[1].strftime('%d/%m')}\n"
                continue
            EmbedList.append(discord.Embed(title = "Birthdays", colour = discord.Colour.random(), description = description))
            description = ""
        EmbedList.append(discord.Embed(title = "Birthdays", colour = discord.Colour.random(), description = description))
        return EmbedList

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.execute("CREATE TABLE IF NOT EXISTS birthdaychannel(guild BIGINT PRIMARY KEY, channel BIGINT NOT NULL)")
        await self.bot.execute("CREATE TABLE IF NOT EXISTS birthdays(guild BIGINT, member BIGINT, birthday DATE, PRIMARY KEY(guild, member))")
        print("BirthdayAlert cog online")

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
        birthdays: dict[discord.Member: date] = {interaction.guild.get_member(member): birthday for member, birthday in table}
        embedlist: list[discord.Embed] = await self.EmbedFormer(birthdays)
        view = BirthdayView(timeout = 30, embedlist = embedlist)
        await interaction.response.send_message(view = view, embed = embedlist[0], ephemeral = True)
        view.response = await interaction.original_message()

    @tasks.loop(time = time(1, 0), reconnect = True)
    async def BirthdayCheck(self):
        birthdays = await self.bot.fetch("SELECT * FROM birthdays WHERE birthday = NOW()::DATE")
        if not birthdays:
            return
        print(birthdays)
        for birthday in birthdays:
            if await self.bot.fetchval("SELECT birthdays FROM events WHERE guild = $1", birthday["guild"]):
                return
            guild = self.bot.get_guild(birthday["guild"])
            if not guild:
                return await self.bot.execute("DELETE FROM birthdays WHERE guild = $1", birthday["guild"])
            channel = await self.bot.fetchval("SELECT channel FROM birthdaychannel WHERE guild = $1", guild.id)
            channel = guild.get_channel(channel)
            member = guild.get_member(birthday["member"])
            await channel.send(f"Today is {member.mention}'s birthday, dont forget to send them a happy birthday message")
            await self.bot.execute("UPDATE birthdays SET birthday = birthday + INTERVAL '1 year' WHERE member = $1", member.id)

    @BirthdayCheck.before_loop
    async def Before(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(BirthdayAlert(bot))
