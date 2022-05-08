import discord
from discord import app_commands
from discord.ext import commands, tasks
from typing import Optional
from datetime import datetime as dt, timedelta


class Reminder(commands.Cog, app_commands.Group):
    def __init__(self, bot: commands.Bot):
        super().__init__(name = "reminder")
        self.bot = bot
        self.reminder.start()

    @commands.Cog.listener()
    async def on_ready(self):
        await self.execute(
            "CREATE TABLE IF NOT EXISTS reminder(guild BIGINT NOT NULL, member BIGINT NOT NULL, creationtime TIMESTAMP WITH TIME ZONE NOT NULL, expiretime INTERVAL SECOND NOT NULL, jumplink TEXT NOT NULL)",
            [])
        print("Reminder cog online")

    async def fetch(self, sql: str, args: list):
        async with self.bot.pool.acquire() as conn:
            async with conn.transaction():
                return await conn.fetch(sql, *args)

    async def fetchval(self, sql: str, args: list):
        async with self.bot.pool.acquire() as conn:
            async with conn.transaction():
                return await conn.fetchval(sql, *args)

    async def execute(self, sql: str, args: list):
        async with self.bot.pool.acquire() as conn:
            async with conn.transaction():
                return await conn.fetchval(sql, *args)

    @app_commands.command(name = "create",
                          description = "Set a DM reminder for all your important things (all fields are optional)")
    @app_commands.describe(year = "YYYY", month = "MM", day = "DD", hour = "HH", minute = "MM", second = "SS",
                           message = "reminder message")
    async def ReminderCreate(self, interaction: discord.Interaction,
                             year: int = dt.now().year, month: int = dt.now().month, day: int = dt.now().day,
                             hour: int = dt.now().hour, minute: int = dt.now().minute, second: int = dt.now().second,
                             message: str = "..."):  # TODO:args
        expiretime = timedelta(year, month, day, hour, minute, second)
        await self.execute(
            "INSERT INTO reminder(guild, member, creationtime, expiretime, jumplink) VALUES($1, $2, $3, $4, $5)",
            [interaction.guild.id, interaction.user.id, interaction.created_at, expiretime.total_seconds,
             interaction.message.jump_url])  # TODO:jump link errors, find new way to link back

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
