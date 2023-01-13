import discord
from discord import Interaction, app_commands
from discord.app_commands import AppCommandError
from discord.ext import commands
from WorstBot import WorstBot
from modules import EmbedGen, Paginators, Converters
import traceback


class DebugView(Paginators.BaseView):
    def __init__(self, short_text: discord.Embed, verbose_text: Converters.CodeBlock, timeout=30):
        super().__init__(timeout=timeout)
        self.short_text = short_text
        self.verbose_text = verbose_text
        self.VERBOSE = False

    @discord.ui.button(label="View Traceback", style=discord.ButtonStyle.red)
    async def Traceback(self, interaction: Interaction, button: discord.ui.Button):
        if not self.VERBOSE:
            button.label = "View Simplified Message"
            await interaction.response.edit_message(content=self.verbose_text, embed=None, view=self)
        else:
            button.label = "View Traceback"
            await interaction.response.edit_message(content=None, embed=self.short_text, view=self)
        self.VERBOSE = not self.VERBOSE


class ErrorHandler(commands.Cog):
    def __init__(self, bot: WorstBot):
        self.bot = bot
        self.owner = None

    async def cog_load(self) -> None:
        self.owner = await self.bot.maybe_fetch_user(self.bot.owner_id)
        self.bot.tree.on_error = self.on_app_command_error

    async def cog_unload(self) -> None:
        self.bot.tree.on_error = self.bot.tree.__class__.on_error

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.logger.info("Error handling cog online")

    @staticmethod
    async def send(interaction: Interaction, short_text: str, verbose_text: Converters.CodeBlock):
        short_text = EmbedGen.SimpleEmbed(title="Oops, this interaction threw an error.", text=short_text)
        view = DebugView(short_text, verbose_text)
        if not interaction.response.is_done():
            await interaction.response.send_message(embed=short_text, view=view, ephemeral=True)
        else:
            await interaction.followup.send(embed=short_text, view=view, ephemeral=True)
        view.response = await interaction.original_response()

    async def on_app_command_error(self, interaction: Interaction, error: AppCommandError):
        if isinstance(error, app_commands.CommandInvokeError):
            error: Exception = error.original
        traceback_lines = traceback.format_exception(type(error), error, error.__traceback__)
        traceback_text = "".join(traceback_lines)
        codeblock = Converters.CodeBlock("py", traceback_text)

        match error:
            case discord.errors.Forbidden():
                error: discord.Forbidden
                await self.send(interaction, error.text, codeblock)
            case app_commands.errors.CheckFailure():
                error: app_commands.CheckFailure
                await self.send(interaction, str(error), codeblock)

            case _:
                await self.owner.send(codeblock)
                return self.bot.logger.error(traceback_text)


async def setup(bot):
    await bot.add_cog(ErrorHandler(bot))
