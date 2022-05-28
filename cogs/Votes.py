import discord
from discord import Interaction, app_commands, ui
from discord.ext import commands


class StartPollModal(ui.Modal, title = "Poll"):
    def __init__(self, *, bot: commands.Bot, voteid = None, question = None, answers = None, ):
        super().__init__()
        self.bot = bot
        self.voteid = voteid
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
        await interaction.response.send_message(f'"{self.question.value}"\nVote started', ephemeral = True)
        answers = str(self.answers).split("\n")
        if self.voteid:
            await self.bot.execute("UPDATE votes SET question=$1 WHERE voteid=$2", self.question.value, self.voteid)
        else:
            self.voteid = await self.bot.fetchval("INSERT INTO votes(guild, question, creationtime) VALUES($1, $2, $3) RETURNING voteid", interaction.guild_id, self.question.value, interaction.created_at)

        for answer in answers:
            await self.bot.execute("INSERT INTO answers(voteid, answer) VALUES($1, $2) ON CONFLICT(voteid, answer) DO NOTHING", self.voteid, answer)

        rows = await self.bot.fetch("SELECT answerid, answer FROM answers WHERE voteid=$1", self.voteid)
        for row in rows:
            if row["answer"] not in answers:
                await self.bot.execute("DELETE FROM answers WHERE answerid=$1", row["answerid"])

    async def on_error(self, interaction: Interaction, error: Exception) -> None:
        raise


class Votes(commands.GroupCog, name = "poll"):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.execute("CREATE TABLE IF NOT EXISTS votes(voteid SERIAL PRIMARY KEY, guild BIGINT, question TEXT NOT NULL, creationtime timestamptz)")
        await self.bot.execute("CREATE TABLE IF NOT EXISTS answers(voteid INT REFERENCES votes(voteid) ON UPDATE CASCADE ON DELETE CASCADE, answerid SERIAL PRIMARY KEY, answer TEXT NOT NULL, UNIQUE(voteid, answer))")
        await self.bot.execute("CREATE TABLE IF NOT EXISTS voters(voteid INT REFERENCES votes(voteid) ON UPDATE CASCADE ON DELETE CASCADE, answerid INT REFERENCES answers(answerid) ON UPDATE CASCADE ON DELETE CASCADE, member BIGINT NOT NULL, UNIQUE(voteid, member))")
        print("Votes cog online")

    @app_commands.command(name = "start", description = "Start a serverwide poll (max of 20 answers)")
    async def VoteStart(self, interaction: Interaction):
        await interaction.response.send_modal(StartPollModal(bot = self.bot))

    @app_commands.command(name = "end", description = "End a serverwide poll")  # todo:output result on end
    async def VoteEnd(self, interaction: Interaction, poll: int):
        await self.bot.execute("DELETE FROM votes WHERE voteid=$1", poll)
        await interaction.response.send_message("poll ended", ephemeral = True)

    @app_commands.command(name = "response", description = "respond to a poll")
    async def VoteResponse(self, interaction: Interaction, poll: int, answer: int):
        await self.bot.execute("INSERT INTO voters(voteid, answerid, member) VALUES($1, $2, $3) ON CONFLICT (voteid, member) DO UPDATE SET answerid=$2", poll, answer, interaction.user.id)
        await interaction.response.send_message("vote recorded", ephemeral = True)

    @app_commands.command(name = "edit", description = "Edit a currently active poll")
    async def VoteEdit(self, interaction: Interaction, poll: int):
        question = await self.bot.fetchval("SELECT question FROM votes WHERE voteid=$1", poll)
        answers = await self.bot.fetch("SELECT answer FROM answers WHERE voteid=$1", poll)
        answers = "\n".join([answer["answer"] for answer in answers])
        await interaction.response.send_modal(StartPollModal(bot = self.bot, question = question, answers = answers, voteid = poll))

    @staticmethod
    def current(current: str):
        return "%" if not current else current

    @VoteResponse.autocomplete("poll")
    @VoteEnd.autocomplete("poll")
    @VoteEdit.autocomplete("poll")
    async def ResponsePollAutocomplete(self, interaction: Interaction, current):
        current = self.current(current)
        responses = await self.bot.fetch("SELECT voteid, question FROM votes WHERE guild=$1 AND question LIKE $2", interaction.guild_id, current)
        return [app_commands.Choice(name = question, value = voteid) for voteid, question in responses]

    @VoteResponse.autocomplete("answer")
    async def ResponseAnswerAutocomplete(self, interaction: Interaction, current):
        current = self.current(current)
        responses = await self.bot.fetch("SELECT answerid, answer FROM answers WHERE voteid=$1 AND answer LIKE $2", interaction.namespace.poll, current)
        return [app_commands.Choice(name = answer, value = answerid) for answerid, answer in responses]


async def setup(bot):
    await bot.add_cog(Votes(bot))

# todo: voteEnd
# todo: voteResults
