import discord
from discord import Interaction, app_commands, ui
from discord.ext import commands
from modules.EmbedGen import FullEmbed, EmbedField
from modules import Converters

async def EmbedGen(*, bot, poll):
    AnswerTable = {answerid: answer for answerid, answer in await bot.fetch("SELECT answerid, answer FROM answers WHERE voteid=$1", poll)}
    counters = {}
    for row in AnswerTable:
        counters[row] = await bot.fetchval("SELECT COUNT(*) FROM voters WHERE answerid=$1", row)
    return FullEmbed(title = "Poll results",
                     fields = [EmbedField(name = answer, value = count) for answer, count in zip(AnswerTable.values(), counters.values())])

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
        answers = str(self.answers).split("\n")[:25]
        if self.voteid:
            await self.bot.execute("UPDATE votes SET question=$1 WHERE voteid=$2", self.question.value, self.voteid)
        else:
            self.voteid = await self.bot.fetchval("INSERT INTO votes(guild, question, author) VALUES($1, $2, $3) RETURNING voteid", interaction.guild_id, self.question.value, interaction.user.id)

        for answer in answers:
            await self.bot.execute("INSERT INTO answers(voteid, answer) VALUES($1, $2) ON CONFLICT(voteid, answer) DO NOTHING", self.voteid, answer)

        rows = await self.bot.fetch("SELECT answerid, answer FROM answers WHERE voteid=$1", self.voteid)
        for row in rows:
            if row["answer"] not in answers:
                await self.bot.execute("DELETE FROM answers WHERE answerid=$1", row["answerid"])

    async def on_error(self, interaction: Interaction, error: Exception) -> None:
        raise

class Dropdown(ui.Select):
    def __init__(self, options, bot):
        self.bot = bot
        super().__init__(
            placeholder = "Select Poll:",
            options = options,
            row = 1,
            min_values=1,
            max_values = 1
        )

    async def callback(self, interaction: Interaction) -> None:
        embed = await EmbedGen(bot = self.bot, poll = int(self.values[0]))
        await interaction.response.edit_message(embed = embed)

class PollResultsView(ui.View):
    def __init__(self, timeout, bot: commands.Bot, options: list[discord.SelectOption]):
        super().__init__(timeout = timeout)
        self.bot = bot
        self.response = None
        self.add_item(Dropdown(options, bot))

    async def on_timeout(self) -> None:
        await self.response.edit(view = None)

    async def on_error(self, interaction: Interaction, error: Exception, item: ui.Select) -> None:
        raise


class Votes(commands.GroupCog, name = "poll"):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.execute("CREATE TABLE IF NOT EXISTS votes(voteid SERIAL PRIMARY KEY, guild BIGINT, question TEXT NOT NULL, author BIGINT UNIQUE)")
        await self.bot.execute("CREATE TABLE IF NOT EXISTS answers(voteid INT REFERENCES votes(voteid) ON UPDATE CASCADE ON DELETE CASCADE, answerid SERIAL PRIMARY KEY, answer TEXT NOT NULL, UNIQUE(voteid, answer))")
        await self.bot.execute("CREATE TABLE IF NOT EXISTS voters(voteid INT REFERENCES votes(voteid) ON UPDATE CASCADE ON DELETE CASCADE, answerid INT REFERENCES answers(answerid) ON UPDATE CASCADE ON DELETE CASCADE, member BIGINT NOT NULL, UNIQUE(voteid, member))")
        print("Votes cog online")

    @app_commands.command(name = "start", description = "Start a serverwide poll (max of 20 answers)")
    async def VoteStart(self, interaction: Interaction):
        if interaction.user.guild_permissions.administrator is False:
            if await self.bot.fetchval("SELECT EXISTS(SELECT 1 FROM votes WHERE author = $1)", interaction.user.id):
                await interaction.response.send_message("Poll belonging to this user already exists, please end the previous poll first", ephemeral=True)
                return
        await interaction.response.send_modal(StartPollModal(bot = self.bot))

    @app_commands.command(name = "response", description = "respond to a poll")
    async def VoteResponse(self, interaction: Interaction, poll: str, answer: str):
        poll, answer = Converters.to_int(poll), Converters.to_int(answer)
        await self.bot.execute("INSERT INTO voters(voteid, answerid, member) VALUES($1, $2, $3) ON CONFLICT (voteid, member) DO UPDATE SET answerid=$2", poll, answer, interaction.user.id)
        await interaction.response.send_message("vote recorded", ephemeral = True)

    @app_commands.command(name = "edit", description = "Edit a currently active poll")
    async def VoteEdit(self, interaction: Interaction, poll: str):
        poll = Converters.to_int(poll)
        if not await self.bot.fetchval("SELECT EXISTS(SELECT 1 FROM votes WHERE author=$1 AND voteid=$2)", interaction.user.id, poll):
            await interaction.response.send_message("This poll does not belong to you", ephemeral=True)
            return
        question = await self.bot.fetchval("SELECT question FROM votes WHERE voteid=$1", poll)
        answers = await self.bot.fetch("SELECT answer FROM answers WHERE voteid=$1", poll)
        answers = "\n".join([answer["answer"] for answer in answers])
        await interaction.response.send_modal(StartPollModal(bot = self.bot, question = question, answers = answers, voteid = poll))

    async def Results(self, interaction: Interaction, poll: int):
        QuestionTable = [discord.SelectOption(label = item["question"], value = item["voteid"]) for item in await self.bot.fetch("SELECT voteid, question FROM votes WHERE guild=$1", interaction.guild_id)]
        view = PollResultsView(timeout = 15, bot = self.bot, options = QuestionTable)
        await interaction.response.send_message(view = view, embed = await EmbedGen(bot = self.bot, poll = poll), ephemeral = True)
        view.response = await interaction.original_message()
        return view

    @app_commands.command(name = "results", description = "Show the current results of a poll")
    async def VoteResults(self, interaction: Interaction, poll: str):
        poll = Converters.to_int(poll)
        await self.Results(interaction, poll)

    @app_commands.command(name = "end", description = "End a poll")
    async def VoteEnd(self, interaction: Interaction, poll: str):
        poll = Converters.to_int(poll)
        if interaction.user.guild_permissions.administrator is False:
            if not await self.bot.fetchval("SELECT EXISTS(SELECT 1 FROM votes WHERE author=$1 AND voteid=$2)", interaction.user.id, poll):
                await interaction.response.send_message("This poll does not belong to you", ephemeral=True)
                return
        view = await self.Results(interaction, poll)
        await view.wait()
        await self.bot.execute("DELETE FROM votes WHERE voteid=$1", poll)

    @VoteResponse.autocomplete("poll")
    @VoteEdit.autocomplete("poll")
    @VoteResults.autocomplete("poll")
    @VoteEnd.autocomplete("poll")
    async def ResponsePollAutocomplete(self, interaction: Interaction, current):
        current = self.bot.current(current)
        responses = await self.bot.fetch("SELECT voteid, question FROM votes WHERE guild=$1 AND question LIKE $2", interaction.guild_id, current)
        return [app_commands.Choice(name = question, value = str(voteid)) for voteid, question in responses]

    @VoteResponse.autocomplete("answer")
    async def ResponseAnswerAutocomplete(self, interaction: Interaction, current):
        poll = Converters.to_int(interaction.namespace.poll)
        current = self.bot.current(current)
        responses = await self.bot.fetch("SELECT answerid, answer FROM answers WHERE voteid=$1 AND answer LIKE $2", poll, current)
        return [app_commands.Choice(name = answer, value = str(answerid)) for answerid, answer in responses]


async def setup(bot):
    await bot.add_cog(Votes(bot))

