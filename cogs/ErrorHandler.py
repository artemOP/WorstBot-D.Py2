import discord
from discord import Interaction, app_commands
from discord.app_commands import AppCommandError
from discord.ext import commands
from discord.utils import MISSING
from discord.abc import Messageable
from WorstBot import WorstBot
from modules import EmbedGen, Paginators, Converters, Errors
import traceback
import sys
from typing import Optional

class DebugView(Paginators.BaseView):
    def __init__(self, short_text: discord.Embed, verbose_text: Converters.CodeBlock, verbose: bool, timeout=30):
        super().__init__(timeout=timeout)
        self.short_text = short_text
        self.verbose_text = verbose_text
        self.VERBOSE = verbose
        self.Traceback.label = "View Simplified Message" if verbose else "View Traceback"

    @discord.ui.button(style=discord.ButtonStyle.red)
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
        self.owner: Optional[discord.User] = None

    async def cog_load(self) -> None:
        self.owner = await self.bot.maybe_fetch_user(self.bot.owner_id)
        self.bot.tree.on_error = self.on_app_command_error
        self.bot.on_error = self.on_error

    async def cog_unload(self) -> None:
        self.bot.tree.on_error = self.bot.tree.__class__.on_error
        self.bot.on_error = self.bot.__class__.on_error

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.logger.info("Error handling cog online")

    @staticmethod
    async def format_traceback(exception_type: type[BaseException], exception: Exception, exception_traceback: Exception.__traceback__) -> str:
        traceback_lines = traceback.format_exception(exception_type, exception, exception_traceback)
        return "".join(traceback_lines)

    @staticmethod
    async def send(messageable: Messageable, **kwargs) -> discord.Message:
        try:
            return await messageable.send(**kwargs)
        except discord.Forbidden:
            raise Errors.SendMessages

    async def send_view(self, interaction: Interaction = None, messageable: Messageable = None, error = MISSING, verbose = False):
        if interaction and messageable:
            raise NotImplemented
        short_text = EmbedGen.SimpleEmbed(title="Oops, this interaction threw an error.", text=getattr(error, "text", str(error)))
        traceback_text = await self.format_traceback(type(error), error, error.__traceback__)
        verbose_text = Converters.CodeBlock("py", traceback_text)
        view = DebugView(short_text, verbose_text, verbose)
        if interaction:
            if not interaction.response.is_done():
                await interaction.response.send_message(content = verbose_text if verbose else None, embed = short_text if not verbose else None, view=view, ephemeral=True)
            else:
                await interaction.followup.send(content = verbose_text if verbose else None, embed = short_text if not verbose else None, view=view, ephemeral=True)
            view.response = await interaction.original_response()
        else:
            view.response = await self.send(messageable = messageable, content = verbose_text if verbose else None, embed = short_text if not verbose else None, view = view)

    async def on_app_command_error(self, interaction: Interaction, error: AppCommandError):
        if isinstance(error, app_commands.CommandInvokeError):
            error: Exception = error.original

        match error:
            case discord.errors.Forbidden():
                error: discord.Forbidden
                await self.send_view(interaction, error = error)
            case app_commands.errors.CheckFailure():
                error: app_commands.CheckFailure
                await self.send_view(interaction, error = error)
            case _:
                error: discord.HTTPException
                if self.owner:
                    await self.send_view(messageable = self.owner, error = error, verbose = True)
                self.bot.logger.error(await self.format_traceback(type(error), error, error.__traceback__))

    async def on_error(self, event: str, *args, **kwargs):
        exception_type, exception, exception_traceback = sys.exc_info()
        traceback_text = await self.format_traceback(exception_type, exception, exception_traceback)
        if isinstance(exception, Errors.ManageRoles):
            exception: Errors.ManageRoles
            await self.send_view(messageable = exception.guild.system_channel, error = exception)
        elif isinstance(exception, Errors.SendMessages):
            try:
                await self.send_view(messageable = exception.guild.owner, error = exception)
            except:
                pass
        else:
            self.bot.logger.error(f"event: {event}\n{args}\n{kwargs}\n{traceback_text}")

async def setup(bot):
    await bot.add_cog(ErrorHandler(bot))
