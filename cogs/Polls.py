import discord
from discord import Interaction, app_commands, ui
from discord.ext import commands
from WorstBot import WorstBot
from modules import EmbedGen, Graphs, Paginators, Converters

class Responses(ui.Select):
    def __init__(self, vote_id: int, options: list[discord.SelectOption], accepted_responses: int):
        super().__init__(
            placeholder = f"Respond to the poll! Select up to {accepted_responses} answers",
            options = options,
            min_values = 1,
            max_values = accepted_responses,
            custom_id = f"poll{vote_id}"
        )
        self.vote_id = vote_id

    async def callback(self, interaction: Interaction) -> None:
        await interaction.client.execute("DELETE FROM voters WHERE vote_id = $1 AND member = $2", self.vote_id, interaction.user.id)
        for answer in self.values:
            await interaction.client.execute("INSERT INTO voters(vote_id, answer_id, member) VALUES($1, $2, $3)", self.vote_id, int(answer), interaction.user.id)
        return await interaction.response.send_message(f"Vote registered", ephemeral = True)


class RespondPollView(ui.View):
    def __init__(self, vote_id: int, options: list[discord.SelectOption], accepted_responses: int):
        super().__init__(timeout = None)
        self.add_item(Responses(vote_id, options, accepted_responses))


class StartPollModal(ui.Modal, title = "Poll"):
    def __init__(self, *, vote_id: int = None, question: str = None, answers: str = None, accepted_responses: int = None):
        super().__init__()
        self.vote_id = vote_id
        self.question = ui.TextInput(
            label = "question",
            placeholder = "enter your question here.",
            default = question,
            required = True
        )
        self.answers = ui.TextInput(
            label = "answers",
            placeholder = "Enter the response options here:\nPut each answer on a new line",
            required = True,
            max_length = 1000,
            style = discord.TextStyle.long,
            default = answers
        )
        self.accepted_responses = ui.TextInput(
            label = "number of accepted responses",
            placeholder = "How many options should users be able to select?",
            required = True,
            max_length = 2,
            style = discord.TextStyle.short,
            default = accepted_responses or 1
        )
        self.add_item(self.question)
        self.add_item(self.answers)
        self.add_item(self.accepted_responses)

    async def on_submit(self, interaction: Interaction) -> None:
        await interaction.response.defer(ephemeral = True)
        answers = [answer for answer in self.answers.value.split("\n")[:25] if answer != ""]
        options = []
        try:
            accepted_responses = min(int(self.accepted_responses.value), len(answers))
        except ValueError:
            accepted_responses = 1

        if self.vote_id:
            await interaction.client.execute("UPDATE votes SET question=$1 WHERE vote_id=$2", self.question.value, self.vote_id)
            await interaction.client.execute("DELETE FROM answers WHERE vote_id=$1", self.vote_id)
        else:
            self.vote_id = await interaction.client.fetchval("INSERT INTO votes(guild, question, author, accepted_responses) VALUES($1, $2, $3, $4) ON CONFLICT DO NOTHING RETURNING vote_id", interaction.guild_id, self.question.value, interaction.user.id, accepted_responses)

        for answer in answers:
            answer_id = await interaction.client.execute("INSERT INTO answers(vote_id, answer) VALUES($1, $2) ON CONFLICT(vote_id, answer) DO NOTHING RETURNING answer_id", self.vote_id, answer)
            if not answer_id:
                continue
            options.append(discord.SelectOption(label = answer, value = answer_id))

        embed = EmbedGen.FullEmbed(
            author = {"name": interaction.user.name, "icon_url": interaction.user.display_avatar.url},
            title = self.question.value,
            fields = [EmbedGen.EmbedField(name = "\u200b", value = answer) for answer in answers]
        )
        message: discord.Message = await interaction.followup.send(view = RespondPollView(vote_id = self.vote_id, options = options, accepted_responses = accepted_responses), embed = embed)
        await interaction.client.execute("UPDATE votes set channel=$1, message_id=$2 WHERE vote_id=$3", message.channel.id, message.id, self.vote_id)

    async def on_error(self, interaction: Interaction, error: Exception) -> None:
        raise

class PollResultsView(Paginators.ThemedGraphView):
    def __init__(self, graphs, responses: dict[str, list[discord.Member]]):
        super().__init__(graphs, timeout = 600)
        self.responses = responses
        self.detailed_poll_response.options = [discord.SelectOption(label = answer) for answer in responses]

    @ui.select(placeholder = "Select an answer to see who voted for it")
    async def detailed_poll_response(self, interaction: Interaction, select: ui.Select):
        await interaction.response.send_message(embeds = EmbedGen.SimpleEmbedList(descriptions = "\n".join(member.mention for member in self.responses[select.values[0]])), ephemeral = True)

class Poll(commands.GroupCog, name = "poll"):

    def __init__(self, bot: WorstBot):
        self.bot = bot
        self.views = []

    async def cog_load(self) -> None:
        await self.bot.execute("CREATE TABLE IF NOT EXISTS votes(vote_id SERIAL PRIMARY KEY, guild BIGINT, channel BIGINT DEFAULT NULL, message_id BIGINT DEFAULT NULL , question TEXT NOT NULL, author BIGINT, accepted_responses INT)")
        await self.bot.execute("CREATE TABLE IF NOT EXISTS answers(vote_id INT REFERENCES votes(vote_id) ON UPDATE CASCADE ON DELETE CASCADE, answer_id SERIAL PRIMARY KEY, answer TEXT NOT NULL, UNIQUE(vote_id, answer))")
        await self.bot.execute("CREATE TABLE IF NOT EXISTS voters(vote_id INT REFERENCES votes(vote_id) ON UPDATE CASCADE ON DELETE CASCADE, answer_id INT REFERENCES answers(answer_id) ON UPDATE CASCADE ON DELETE CASCADE, member BIGINT NOT NULL)")

        polls = await self.bot.fetch("SELECT * FROM votes")
        for poll in polls:
            answers = await self.bot.fetch("SELECT * FROM answers WHERE vote_id=$1", poll["vote_id"])
            self.views.append(
                RespondPollView(
                    vote_id = poll["vote_id"],
                    options = [discord.SelectOption(label = answer["answer"], value = answer["answer_id"]) for answer in answers],
                    accepted_responses = poll["accepted_responses"])
            )
            self.bot.add_view(view = self.views[-1], message_id = poll["message_id"])

    async def cog_unload(self) -> None:
        for view in self.views:  # type: ui.View
            view.stop()

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.logger.info("Polls cog online")

    @app_commands.command(name = "start", description = "Start a serverwide poll (max of 20 answers)")
    async def VoteStart(self, interaction: Interaction):
        await interaction.response.send_modal(StartPollModal())

    @app_commands.command(name = "edit", description = "Edit a currently active poll. WARNING, this will clear previous responses")
    async def VoteEdit(self, interaction: Interaction, poll_id: int):
        if not await self.bot.fetchval("SELECT EXISTS(SELECT 1 FROM votes WHERE author=$1 AND vote_id=$2)", interaction.user.id, poll_id):
            await interaction.response.send_message("This poll does not belong to you", ephemeral = True)
            return
        poll = await self.bot.fetchrow("SELECT question, channel, message_id, accepted_responses from votes WHERE vote_id=$1", poll_id)
        channel: discord.PartialMessageable = self.bot.get_partial_messageable(poll["channel"])
        message = channel.get_partial_message(poll["message_id"])
        answers = await self.bot.fetch("SELECT answer FROM answers WHERE vote_id=$1", poll_id)
        answers = "\n".join([answer["answer"] for answer in answers])
        await interaction.response.send_modal(StartPollModal(question = poll["question"], answers = answers, vote_id = poll_id, accepted_responses = poll["accepted_responses"]))
        await message.delete()

    async def results(self, interaction: Interaction, poll_id: int, ephemeral: bool):
        await interaction.response.defer(ephemeral = ephemeral)
        poll = await self.bot.fetchrow("SELECT vote_id, message_id, channel, question, author FROM votes WHERE vote_id = $1", poll_id)
        answer_table = {answer_id: answer for answer_id, answer in await self.bot.fetch("SELECT answer_id, answer FROM answers WHERE vote_id=$1", poll_id)}

        counts, responses = {}, {}
        for answer_id, answer in answer_table.items():
            user_list = await self.bot.fetchval("SELECT ARRAY_AGG(member) FROM voters WHERE answer_id=$1", answer_id)
            responses[answer] = [await self.bot.maybe_fetch_member(interaction.guild, member) for member in user_list]
            counts[answer] = len(user_list)

        chartIO = await Graphs.graph("bar", self.bot.loop, counts)

        author = await self.bot.maybe_fetch_member(interaction.guild, poll["author"])
        channel = self.bot.get_partial_messageable(poll["channel"], guild_id = interaction.guild_id)
        message = channel.get_partial_message(poll["message_id"])
        view = PollResultsView({"Light": chartIO[0], "Dark": chartIO[1]}, responses)
        embed = EmbedGen.FullEmbed(
            author = {"name": author or "poll", "url": message.jump_url, "icon_url": None if not author else author.display_avatar.url},
            title = poll["question"],
            fields = [EmbedGen.EmbedField(name = name, value = value) for name, value in counts.items()],
            image = "attachment://image.png",
            footer = {"text": f"{sum(counts.values())} Total responses"}
        )
        await interaction.followup.send(
            view = view,
            embed = embed,
            file = discord.File(fp = chartIO[1], filename = "image.png")
        )
        chartIO[1].seek(0)
        view.response = await interaction.original_response()

    @app_commands.command(name = "results", description = "Show the current results of a poll")
    async def VoteResults(self, interaction: Interaction, poll_id: int):
        return await self.results(interaction, poll_id, ephemeral = True)

    @app_commands.command(name = "end", description = "End a poll and show the results")
    async def VoteEnd(self, interaction: Interaction, poll_id: int):
        owner = await self.bot.fetchval("SELECT author FROM votes WHERE vote_id=$1", poll_id)
        if interaction.user.id != owner:
            return await interaction.response.send_message(f"This is not your poll to end, please use {Converters.to_command_mention(self.VoteResults, interaction.guild)}", ephemeral = True)
        await self.results(interaction, poll_id, ephemeral = False)
        channel, message = await self.bot.fetchrow("DELETE FROM votes WHERE vote_id = $1 RETURNING channel, message_id", poll_id)  # type: int, int
        channel: discord.PartialMessageable = self.bot.get_partial_messageable(channel)
        message: discord.PartialMessage = channel.get_partial_message(message)
        await message.delete()

    @VoteEdit.autocomplete("poll_id")
    @VoteResults.autocomplete("poll_id")
    @VoteEnd.autocomplete("poll_id")
    async def ResponsePollAutocomplete(self, interaction: Interaction, current):
        current = self.bot.current(current)
        responses = await self.bot.fetch("SELECT vote_id, question FROM votes WHERE guild=$1 AND question LIKE $2", interaction.guild_id, current)
        return [app_commands.Choice(name = question, value = voteid) for voteid, question in responses]


async def setup(bot):
    await bot.add_cog(Poll(bot))
