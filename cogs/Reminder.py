import discord
from discord import app_commands
from discord.app_commands import Range
from discord.ext import commands, tasks
from WorstBot import WorstBot
from datetime import datetime as dt, timezone, time
from modules.EmbedGen import FullEmbed, EmbedField

class Reminder(commands.Cog):
    def __init__(self, bot: WorstBot):
        self.bot = bot
        self.logger = self.bot.logger.getChild(self.qualified_name)

    async def cog_load(self) -> None:
        await self.bot.execute("CREATE TABLE IF NOT EXISTS reminder(guild BIGINT NOT NULL, member BIGINT NOT NULL, creationtime TIMESTAMP WITH TIME ZONE NOT NULL, expiretime TIMESTAMP WITH TIME ZONE NOT NULL,message TEXT NOT NULL, jumplink TEXT NOT NULL)")
        self.logger.info(f"{self.qualified_name} cog loaded")

    async def cog_unload(self) -> None:
        self.ReminderTask.stop()
        self.logger.info(f"{self.qualified_name} cog unloaded")

    @app_commands.command(name = "remindme", description = "Set a DM reminder for all your important things (all fields are optional)")
    async def ReminderCreate(self, interaction: discord.Interaction, year: Range[int, dt.now().year, 2030] = None, month: Range[int, 1, 12] = None, day: Range[int, 1, 31] = None, hour: Range[int, 0, 60] = 0, minute: Range[int, 0, 60] = 0, second: Range[int, 0, 60] = 0, message: str = "..."):
        """Create a reminder

        :param interaction:
        :param year: YYYY
        :param month: MM
        :param day: DD
        :param hour: HH
        :param minute: MM
        :param second: SS
        :param message: Reminder content
        :return:
        """
        try:
            expiretime = dt(year or dt.now().year, month or dt.now().month, day or dt.now().day, hour, minute, second)
        except ValueError:
            await interaction.response.send_message("that isnt how days work")
            return
        await interaction.response.send_message(f"""Reminding you about "{message}" at {str(expiretime).split("+")[0]} """, ephemeral = True)
        response = await interaction.original_response()
        await self.bot.execute("INSERT INTO reminder(guild, member, creationtime, expiretime,message, jumplink) VALUES($1, $2, $3, $4, $5, $6)", interaction.guild.id, interaction.user.id, interaction.created_at, expiretime, message, response.jump_url)
        if self.ReminderTask.is_running():
            self.ReminderTask.restart()
        else:
            self.ReminderTask.start()

    @tasks.loop(seconds = 30, reconnect = True)
    async def ReminderTask(self):
        reminder = await self.bot.fetchrow("SELECT * FROM reminder WHERE expiretime = (SELECT MIN(expiretime) FROM reminder)")

        if not reminder:
            return

        if (reminder["expiretime"] - dt.now(timezone.utc)).days > 7:
            return

        await discord.utils.sleep_until(reminder["expiretime"])
        user = await self.bot.maybe_fetch_user(reminder["member"])
        embed = FullEmbed(title = "**Reminder**",
                          fields = [EmbedField(name = "**original message:**", value = reminder["jumplink"])],
                          description = f"""You asked to be reminded of: "{reminder["message"]}" """)
        await user.send(embed = embed)
        await self.bot.execute("DELETE FROM reminder WHERE jumplink=$1", reminder["jumplink"])

    @ReminderTask.before_loop
    async def BeforeReminder(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(Reminder(bot))
