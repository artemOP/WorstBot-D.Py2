import discord
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime as dt, timezone
from asyncio import sleep


class Reminder(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.ReminderTask.start()

    @commands.Cog.listener()
    async def on_ready(self):
        await self.execute(
            "CREATE TABLE IF NOT EXISTS reminder(guild BIGINT NOT NULL, member BIGINT NOT NULL, creationtime TIMESTAMP WITH TIME ZONE NOT NULL, expiretime TIMESTAMP WITH TIME ZONE NOT NULL,message TEXT NOT NULL, jumplink TEXT NOT NULL)", [])
        print("Reminder cog online")

    async def execute(self, sql: str, args: list):
        async with self.bot.pool.acquire() as conn:
            async with conn.transaction():
                return await conn.execute(sql, *args)

    @app_commands.command(name = "remindme", description = "Set a DM reminder for all your important things (all fields are optional)")
    @app_commands.describe(year = "YYYY", month = "MM", day = "DD", hour = "HH", minute = "MM", second = "SS", message = "reminder message")
    async def ReminderCreate(self, interaction: discord.Interaction, year: int = None, month: int = None, day: int = None, hour: int = None, minute: int = None, second: int = None, message: str = "..."):
        expiretime = dt(year or dt.now().year, month or dt.now().month, day or dt.now().day, hour or dt.now().hour, minute or dt.now().minute, second or dt.now().second)
        await interaction.response.send_message(f"""Reminding you about "{message}" at {str(expiretime).split("+")[0]} """)
        response = await interaction.original_message()
        await self.execute("INSERT INTO reminder(guild, member, creationtime, expiretime,message, jumplink) VALUES($1, $2, $3, $4, $5, $6)", [interaction.guild.id, interaction.user.id, interaction.created_at, expiretime, message, response.jump_url])
        if self.ReminderTask.is_running():
            self.ReminderTask.restart()
        else:
            self.ReminderTask.start()


    @tasks.loop(seconds = 30, reconnect = True)
    async def ReminderTask(self):
        print("run")
        async with self.bot.pool.acquire() as conn:
            async with conn.transaction():
                reminder = await conn.fetchrow("SELECT * FROM reminder WHERE expiretime = (SELECT MIN(expiretime) FROM reminder)")

        if not reminder:
            self.ReminderTask.stop()
            return

        if (reminder["expiretime"] - dt.now(timezone.utc)).days > 7:
            self.ReminderTask.stop()
        else:
            await discord.utils.sleep_until(reminder["expiretime"])
            user = self.bot.get_user(reminder["member"])
            embed = discord.Embed(colour = discord.Color.random(), title = "**Reminder**", description = f"""You asked to be reminded of: "{reminder["message"]}" """)
            embed.add_field(name = "**original message:**", value = reminder["jumplink"])
            await user.send(embed=embed)

            async with self.bot.pool.acquire() as conn:
                async with conn.transaction():
                    await conn.execute("DELETE FROM reminder WHERE expiretime<=now()")


    @ReminderTask.before_loop
    async def BeforeReminder(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(Reminder(bot))
