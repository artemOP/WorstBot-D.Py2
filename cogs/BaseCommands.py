import discord
from discord import app_commands, Interaction, utils
from discord.ext import commands
from WorstBot import WorstBot
from dateutil.relativedelta import relativedelta
import random
import re
from rapidfuzz import process
from modules import Converters, Constants

class BaseCommands(commands.Cog):
    def __init__(self, bot: WorstBot):
        self.bot = bot
        self.logger = self.bot.logger.getChild(self.qualified_name)

    async def cog_load(self) -> None:
        self.logger.info(f"{self.qualified_name} cog loaded")

    async def cog_unload(self) -> None:
        self.logger.info(f"{self.qualified_name} cog unloaded")

    @app_commands.command(name = "ping")
    async def ping(self, interaction: Interaction):
        await interaction.response.send_message(f"Pong!{round(self.bot.latency * 1000)}ms", ephemeral = True)

    @app_commands.command(name = "say")
    @app_commands.default_permissions(manage_messages = True)
    async def say(self, interaction: Interaction, *, arg: str = "what?"):
        await interaction.response.send_message(ephemeral = True, content = Constants.BLANK)
        await interaction.channel.send(content = arg)

    def is_me(self, message: discord.Message) -> bool:
        return not message.author == self.bot.user or message.created_at < discord.utils.utcnow() - relativedelta(seconds = 10)

    @app_commands.command(name = "purge")
    @app_commands.default_permissions(manage_messages = True)
    async def purge(self, interaction: Interaction, amount: app_commands.Range[int, 1, 100] = 1):
        await interaction.response.defer(ephemeral = True)
        deleted = await interaction.channel.purge(limit = amount, check = self.is_me, bulk = True if amount > 1 else False, after = interaction.created_at - relativedelta(weeks = 2), oldest_first = False)
        await interaction.followup.send(content = f"deleted {len(deleted)} messages")

    @app_commands.command(name = "rtd", description = "role some dice")
    @app_commands.describe(dice="number of dice to roll", sides="Number of faces on die, set either this or min+max+step", minimum="lowest number on die", maximum="highest number on die", step="increase on each face", ephemeral="Set to false to be visible by all")
    async def roll_the_dice(self, interaction: Interaction, dice: int = 1, sides: int = 6, minimum: int = None, maximum: int = None, step: int = 1, ephemeral: bool = True):
        if not (minimum or maximum):
            minimum, maximum = 1, sides
        rolls = [str(random.randrange(minimum, maximum+1, step)) for _ in range(dice)]
        await interaction.response.send_message(f"You rolled {dice} d{int(maximum/step)}\n\n You rolled: {', '.join(rolls)}", ephemeral=ephemeral)

    @app_commands.command(name = "emoji")
    @app_commands.default_permissions(manage_emojis = True)
    async def emoji_stealer(self, interaction: Interaction, emoji: str):
        """Get emoji from other servers and add it to your own

        :param interaction: discord model
        :param emoji: Custom Emoji you want to add to your server
        """
        await interaction.response.defer(ephemeral = True)
        emoji_strings: list[str] = re.findall("<(?P<animated>a?):(?P<name>[a-zA-Z0-9_]{2,32}):(?P<id>[0-9]{18,22})>", emoji)
        if not emoji_strings:
            return await interaction.followup.send("Please enter a custom emoji into the emoji parameter")
        for animated, name, _id in emoji_strings:
            partial_emoji = discord.PartialEmoji.with_state(state = self.bot._connection, name = name, animated = animated, id = _id)
            if not partial_emoji.is_custom_emoji():
                interaction.followup.send("Please enter a custom emoji into into the emoji parameter")
                continue
            try:
                emoji = await interaction.guild.create_custom_emoji(image = await partial_emoji.read(), name = name, reason = "Emoji stolen by worstbot")
                await interaction.followup.send(f"{emoji} has been added to the server", ephemeral = True)
            except discord.Forbidden as e:
                await interaction.followup.send(f"{name} could not be addded due to: {e.text}", ephemeral = True)

    @app_commands.command(name = "self-mute")
    async def self_mute(self, interaction: Interaction, length: app_commands.Range[int, 1, 2_419_200] = None):
        """Mute yourself for a set time period

        :param interaction: discord Interaction
        :param length: Length of mute in seconds
        """
        if not length:
            length = random.gammavariate(3.1, 99_000)
        until = utils.utcnow() + relativedelta(seconds = length)
        await interaction.user.timeout(until, reason = "WorstBot self_mute commands")
        await interaction.response.send_message(f"{interaction.user.mention} has timed themself out until {utils.format_dt(until)}")

    @app_commands.command(name = "mention-command")
    @app_commands.default_permissions()
    async def mention_command(self, interaction: Interaction, command: str):
        await interaction.response.send_message(command)

    @mention_command.autocomplete(name = "command")
    async def mention_command_autocomplete(self, interaction: Interaction, current: str) -> list[app_commands.Choice[str]]:
        commands_and_groups = self.bot.tree.get_commands(guild = interaction.guild, type = discord.AppCommandType.chat_input)
        command_list = self.bot.tree.flatten_commands(commands_and_groups)
        if not current:
            return [
                       app_commands.Choice(
                           name = command.qualified_name,
                           value = Converters.to_command_mention(command, interaction.guild)
                       )
                       for command in command_list
                   ][:25]

        fuzzy_commands = process.extract(current, [command.qualified_name for command in command_list], limit = 25, score_cutoff = 60)
        fuzzy_commands = [command_name for command_name, _, _ in fuzzy_commands]
        return [
            app_commands.Choice(
                name = command.qualified_name,
                value = Converters.to_command_mention(command, interaction.guild)
            )
            for command in command_list if command.qualified_name in fuzzy_commands
        ]

async def setup(bot):
    await bot.add_cog(BaseCommands(bot))
