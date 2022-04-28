import discord
from discord import app_commands
from discord.ext import commands, tasks
from typing import Optional
from datetime import datetime as dt


class Reminder(commands.Cog, app_commands.Group):
    def __init__(self, bot: commands.Bot):
        super().__init__(name = "reminder")
        self.bot = bot
        self.reminder.start()

    @commands.Cog.listener()
    async def on_ready(self):
        print("Reminder cog online")

    @app_commands.command(name = "create")
    async def ReminderCreate(self, year: int = dt.now().year, month: int = dt.now().month, day: int = dt.now().day,
                             hour: int = dt.now().hour, minute: int = dt.now().minute, second: int = dt.now().second,
                             message: str = "..."):  # TODO:args
        pass

    """
    reminder create YY, MM, DD, HH, MM, SS, message
    database: guild user creationTime expireTime message, jumpLink
    restart task on invoke
    """

    @tasks.loop(seconds = 30, reconnect = True)
    async def reminder(self):
        pass

    """
    get first reminder sorted by soonest expiring
    sleep until expire
    get user
    send dm containing message
    include jumpLink as button
    """

    @reminder.before_loop
    async def BeforeReminder(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(Reminder(bot))
