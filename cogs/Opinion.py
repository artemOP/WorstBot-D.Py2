import discord
from discord import app_commands
from discord.ext import commands, tasks
from WorstBot import WorstBot
from re import sub
from asyncio import sleep

class Opinion(commands.Cog):
    def __init__(self, bot: WorstBot):
        self.bot = bot

    async def cog_load(self) -> None:
        await self.bot.execute("CREATE TABLE IF NOT EXISTS Opinion(guild BIGINT NOT NULL, timestamp TIMESTAMP WITH TIME ZONE NOT NULL, content TEXT DEFAULT NULL)")
        await self.bot.execute("CREATE TABLE IF NOT EXISTS PrefixBlacklist(guild BIGINT NOT NULL, prefix TEXT NOT NULL)")
        self.DeleteOld.start()

    async def cog_unload(self) -> None:
        self.DeleteOld.stop()

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.logger.info("Opinion cog online")

    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.channel.guild:
            return
        if any((message.author.bot, message.channel.is_nsfw(), message.attachments)):
            return
        if await self.bot.events(message.guild.id, self.bot._events.opinion) is False:
            return
        prefixes = await self.bot.fetch("SELECT prefix FROM PrefixBlacklist WHERE guild = $1", message.guild.id)
        if any(message.content.startswith(prefix["prefix"]) for prefix in prefixes):
            return

        content = sub(r"http\S+", "", message.clean_content)
        content = sub(r"<(?P<animated>a?):(?P<name>\w{2,32}):(?P<id>\d{18,22})>", "", content)
        await self.bot.execute("INSERT INTO opinion(guild, timestamp, content) VALUES ($1, $2, $3)", message.guild.id, message.created_at, content)

    @app_commands.command(name="opinion", description="Ask worst bot for its opinion on your super important questions")
    async def opinion(self, interaction: discord.Interaction, opinion: str = None):
        content = await self.bot.fetchval("SELECT content FROM Opinion WHERE GUILD=$1 ORDER BY random() LIMIT 1", interaction.guild.id)
        await interaction.response.send_message(content=f"what is my opinion on `{opinion}`?\n\n{content or 'I have no opinions'}")

    @app_commands.command(name = "prefix-blacklist", description = "blacklist prefixes used by other bots in opinion forming")
    @app_commands.default_permissions()
    async def PrefixBlacklist(self, interaction: discord.Interaction, prefix: str):
        await self.bot.execute("INSERT INTO prefixblacklist(guild, prefix) VALUES ($1, $2)", interaction.guild_id, prefix)
        await interaction.response.send_message(f"messages starting with {prefix} will be ignored", ephemeral = True)

    @tasks.loop(hours=24, reconnect=True)
    async def DeleteOld(self):
        await self.bot.execute("DELETE FROM opinion WHERE timestamp < CURRENT_TIMESTAMP - INTERVAL '2 weeks'")

    @DeleteOld.before_loop
    async def BeforeDeleteOld(self):
        await self.bot.wait_until_ready()
        await sleep(3)



async def setup(bot):
    await bot.add_cog(Opinion(bot))
