import discord
from discord import app_commands, ui, Interaction
from discord.ext import commands


class StartPollModal(ui.Modal, title = "Poll"):
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
        await interaction.response.send_message(f'"{self.question.value}"\nVote started',ephemeral = True)
        answers = str(self.answers).split("\n")[0:20]
        voteid = await self.bot.fetchval("INSERT INTO votes(guild, question, creationtime) VALUES($1, $2, $3) RETURNING voteid", interaction.guild_id, self.question.value, interaction.created_at)
        for answer in answers:
            await self.bot.execute("INSERT INTO answers(voteid, answer) VALUES($1, $2)", voteid, answer)

    async def on_error(self, interaction: Interaction, error: Exception) -> None:
        raise

class Votes(commands.GroupCog, name = "poll"):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.execute("CREATE TABLE IF NOT EXISTS votes(voteid SERIAL PRIMARY KEY, guild BIGINT, question TEXT NOT NULL, creationtime timestamptz)")
        await self.bot.execute("CREATE TABLE IF NOT EXISTS answers(voteid INT REFERENCES votes(voteid) ON UPDATE CASCADE ON DELETE CASCADE, answerid SERIAL PRIMARY KEY, answer TEXT NOT NULL)")
        await self.bot.execute("CREATE TABLE IF NOT EXISTS voters(voteid INT REFERENCES votes(voteid) ON UPDATE CASCADE ON DELETE CASCADE, answerid INT REFERENCES answers(answerid) ON UPDATE CASCADE ON DELETE CASCADE, member BIGINT NOT NULL, UNIQUE(voteid, member))")
        print("Votes cog online")

    async def isVote(self, guild: int):
        return await self.bot.fetchval("SELECT EXISTS(SELECT 1 FROM votes WHERE guild=$1)", guild)

    @app_commands.command(name = "start", description = "Start a serverwide poll (max of 20 answers)")
    async def VoteStart(self, interaction: Interaction):
        await interaction.response.send_modal(StartPollModal(bot = self.bot))

    @app_commands.command(name = "end", description = "End a serverwide poll")  # todo:output result on end
    async def VoteEnd(self, interaction: Interaction, poll: int):
        if await self.isVote(interaction.guild_id):
            await self.bot.execute("DELETE FROM votes WHERE voteid=$1", poll)
            await interaction.response.send_message("poll ended", ephemeral = True)

    @app_commands.command(name = "response", description = "respond to a poll")
    async def Response(self, interaction: Interaction, poll: int, answer: int):
        await self.bot.execute("INSERT INTO voters(voteid, answerid, member) VALUES($1, $2, $3) ON CONFLICT (voteid, member) DO UPDATE SET answerid=$2",poll, answer, interaction.user.id)
        await interaction.response.send_message("vote recorded", ephemeral = True)


    @Response.autocomplete("poll")
    @VoteEnd.autocomplete("poll")
    async def ResponsePollAutocomplete(self, interaction: Interaction, current):
        if not current:
            current = "%"
        responses = await self.bot.fetch("SELECT voteid, question FROM votes WHERE guild=$1 AND question LIKE $2 LIMIT 25", interaction.guild_id, current)
        return [app_commands.Choice(name = question, value = voteid) for voteid, question in responses]

    @Response.autocomplete("answer")
    async def ResponseAnswerAutocomplete(self, interaction: Interaction, current):
        if not current:
            current = "%"
        responses = await self.bot.fetch("SELECT answerid, answer FROM answers WHERE voteid=$1 AND answer LIKE $2 LIMIT 25", interaction.namespace.poll, current)
        return [app_commands.Choice(name = answer, value = answerid) for answerid, answer in responses]


async def setup(bot):
    await bot.add_cog(Votes(bot))
