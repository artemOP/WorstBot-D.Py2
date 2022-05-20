import discord
from discord import app_commands, ui, Interaction
from discord.ext import commands


class Vote(ui.Modal, title = "Poll"):
    def __init__(self, bot: commands.Bot, question = None, answers = None, ):
        super().__init__()
        self.bot = bot
        self.question = ui.TextInput(
            label = "question",
            placeholder = "enter your question here.",
            default = question,
            required = True
        )
        self.add_item(self.question)
        self.answers = ui.TextInput(
            label = "answers",
            placeholder = "Enter the response options here:\nPut each answer on a new line",
            required = True,
            max_length = 1000,
            style = discord.TextStyle.long,
            default = answers
        )
        self.add_item(self.answers)

    async def on_submit(self, interaction: Interaction) -> None:
        await interaction.response.send_message(f'"{self.question.value}"\nSend your votes in now!')
        answers = str(self.answers).split("\n")
        guild = await self.bot.fetchval("INSERT INTO votes(guild, question, creationtime) VALUES($1, $2, $3) RETURNING guild", interaction.guild_id, self.question.value, interaction.created_at)
        for answer in answers:
            await self.bot.execute("INSERT INTO answers(guild, answer) VALUES($1, $2)", guild, answer)

    async def on_error(self, interaction: Interaction, error: Exception) -> None:
        raise


class Votes(commands.GroupCog, name = "poll"):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.execute("CREATE TABLE IF NOT EXISTS votes(guild BIGINT PRIMARY KEY, question TEXT, creationtime timestamptz)")
        await self.bot.execute("CREATE TABLE IF NOT EXISTS answers(guild BIGINT REFERENCES votes(guild) ON UPDATE CASCADE ON DELETE CASCADE, answerid SERIAL PRIMARY KEY, answer TEXT NOT NULL)")
        await self.bot.execute("CREATE TABLE IF NOT EXISTS voters(answerid INT REFERENCES answers(answerid) ON UPDATE CASCADE ON DELETE CASCADE, member BIGINT NOT NULL)")
        print("Votes cog online")

    async def isVote(self, guild: int):
        await self.bot.fetchval("SELECT EXISTS(SELECT 1 FROM votes WHERE guild=$1)", [guild])


    @app_commands.command(name = "start", description = "Start a serverwide Poll")
    async def VoteStart(self, interaction: Interaction):
        if await self.isVote(interaction.guild_id):
            await interaction.response.send_message("Please end the previous Poll before starting a new one")
            return
        modal = await interaction.response.send_modal(Vote(bot = self.bot))


async def setup(bot):
    await bot.add_cog(Votes(bot))
