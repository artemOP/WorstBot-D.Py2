import discord
from discord import app_commands
from discord.ext import commands


class Votes(commands.GroupCog, name = "poll"):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        await self.execute("CREATE TABLE IF NOT EXISTS votes(guild BIGINT PRIMARY KEY, question TEXT, creationtime timestamptz)", [])
        await self.execute("CREATE TABLE IF NOT EXISTS answers(guild BIGINT REFERENCES votes(guild) ON UPDATE CASCADE ON DELETE CASCADE, answerid SERIAL PRIMARY KEY, answer TEXT NOT NULL)", [])
        await self.execute("CREATE TABLE IF NOT EXISTS voters(answerid INT REFERENCES answers(answerid) ON UPDATE CASCADE ON DELETE CASCADE, member BIGINT NOT NULL)", [])
        print("Votes cog online")

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

    async def isVote(self, guild: int):
        await self.fetchval("SELECT EXISTS(SELECT 1 FROM votes WHERE guild=$1)", [guild])

    @app_commands.command(name = "start", description = "Start a serverwide Poll")
    @app_commands.describe(question = "ask your question", answers = "give your answers as a comma separated list eg. one, two, three")
    async def VoteStart(self, interaction: discord.Interaction, question: str, answers: str):
        if await self.isVote(interaction.guild_id):
            await interaction.response.send_message("Please end the previous Poll before starting a new one")
            return
        answers = answers.replace(", ", ",").split(",")
        guild = await self.fetchval("INSERT INTO votes(guild, question, creationtime) VALUES($1, $2, $3) RETURNING guild", [interaction.guild_id, question, interaction.created_at])
        for answer in answers:
            await self.execute("INSERT INTO answers(guild, answer) VALUES($1, $2)", [guild, answer])
        await interaction.response.send_message("Poll Started")

async def setup(bot):
    await bot.add_cog(Votes(bot))
