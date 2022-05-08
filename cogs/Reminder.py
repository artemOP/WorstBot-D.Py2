import discord
from discord import app_commands
from discord.ext import commands, tasks
from asyncio import sleep
from datetime import datetime as dt


class Reminder(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.reminder.start()

    @commands.Cog.listener()
    async def on_ready(self):
        await self.execute(
            "CREATE TABLE IF NOT EXISTS reminder(guild BIGINT NOT NULL, member BIGINT NOT NULL, creationtime TIMESTAMP WITH TIME ZONE NOT NULL, expiretime INTEGER NOT NULL,message TEXT NOT NULL, jumplink TEXT NOT NULL)",
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

    @app_commands.describe(year="YYYY", month="MM", day="DD", hour="HH", minute="MM", second="SS", message="reminder message")
    @app_commands.command(name="remindme", description="Set a DM reminder for all your important things (all fields are optional)")
    async def ReminderCreate(self, interaction: discord.Interaction, year: int = None, month: int = None, day: int = None, hour: int = None, minute: int = None, second: int = None, message: str = "..."):
        expiretime = dt(year=year, month=month, day=day, hour=hour, minute=minute, second=second)
        await interaction.response.send_message(f"""Reminding you about "{message}" """)
        response = await interaction.original_message()
        await self.execute(
            "INSERT INTO reminder(guild, member, creationtime, expiretime, message, jumplink) VALUES($1, $2, $3, $4, $5, $6)",
            [interaction.guild.id, interaction.user.id, interaction.created_at, expiretime.timestamp(), message, response.jump_url])
        self.reminder.restart()

    """
    reminder create YY, MM, DD, HH, MM, SS, message
    database: guild user creationTime expireTime message, jumpLink
    restart task on invoke
    """

    @tasks.loop(seconds=30, reconnect=True)
    async def reminder(self):
        #reminder = await self.fetch("SELECT guild, member, creationtime, MIN(expiretime), message, jumplink FROM reminder GROUP BY guild, member, creationtime, message, jumplink",[])
        reminder = await self.fetchval("SELECT MIN(expiretime) FROM Reminder", [])
        await self.execute("DELETE FROM Reminder WHERE expiretime=$1",[reminder])
        print(reminder)

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
