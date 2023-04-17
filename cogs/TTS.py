from __future__ import annotations

import logging
from asyncio import sleep
from enum import Enum
from io import BufferedIOBase, BytesIO
from typing import TYPE_CHECKING

import discord
from aiogtts import aiogTTS
from discord import Interaction, app_commands
from discord.app_commands import Range
from discord.ext import commands

if TYPE_CHECKING:
    from WorstBot import WorstBot


class Accents(Enum):
    Australia = "com.au",
    United_Kingdom = "co.uk",
    United_States = "com",
    Canada = "ca",
    India = "co.in",


class FFmpegPCMAudio(discord.FFmpegPCMAudio):
    _log = logging.getLogger("discord.player")
    _log.setLevel(logging.ERROR)

    def __init__(self, source, *, executable: str = None, pipe: bool = False, stderr: bool = None, before_options: str = None, options: str = None, **kwargs):
        super().__init__(source, executable = executable, pipe = pipe, stderr = stderr, before_options = before_options, options = options, **kwargs)

    def _pipe_writer(self, source: BufferedIOBase) -> None:
        while self._process:
            # arbitrarily large read size
            data = source.read(8192)
            if not data:
                self._stdin.close()
                self._process.wait(timeout = 10)
                return
            try:
                if self._stdin is not None:
                    self._stdin.write(data)
            except Exception:
                self._log.debug('Write error for %s, this is probably not a problem', self, exc_info = True)
                # at this point the source data is either exhausted or the process is fubar
                self._process.terminate()
                return


class TTS(commands.GroupCog, name = "tts"):
    def __init__(self, bot: WorstBot):
        self.bot = bot

    async def cog_load(self) -> None:
        self.bot.logger.info("TTS cog Loaded")

    async def cog_unload(self) -> None:
        self.bot.logger.info("TTS cog Unloaded")

    async def get_voice_client(self, channel: discord.VoiceChannel) -> discord.VoiceClient:
        if vc := channel.guild.voice_client:
            if vc.channel == channel:
                return vc
            await vc.disconnect(force = True)
        return await channel.connect(self_deaf = True, timeout = 2)

    @staticmethod
    def is_user_connected():
        def predicate(interaction: Interaction):
            return bool(interaction.user.voice)

        return app_commands.check(predicate)

    @app_commands.command(name = "connect")
    @is_user_connected()
    async def connect(self, interaction: Interaction):
        """Allows WorstBot to connect to your voice channel

        :param interaction:
        :return:
        """
        await interaction.response.defer(ephemeral = True)

        vc = await self.get_voice_client(interaction.user.voice.channel)
        await interaction.followup.send(f"Connected to {vc.channel.mention}", ephemeral = True)

    @app_commands.command(name = "disconnect")
    async def disconnect(self, interaction: Interaction):
        """Disconnects WorstBot from the voice channel

        :param interaction:
        :return:
        """
        if not (interaction.user.voice and interaction.guild.voice_client):
            return await interaction.response.send_message("WorstBot cannot be disconnected currently", ephemeral = True)

        if interaction.user.voice.channel == interaction.guild.voice_client.channel:
            await interaction.guild.voice_client.disconnect(force = True)
            return await interaction.response.send_message("Disconnected", ephemeral = True)

    @app_commands.command(name = "send")
    @is_user_connected()
    async def send(self, interaction: Interaction, message: Range[
        str, 1, 100], accent: Accents = Accents.United_States):
        """Send a TTS message to your voice channel


        :param interaction:
        :param message: The message to send
        :param accent: The accent to use
        :return:
        """
        await interaction.response.defer(ephemeral = True)
        vc = await self.get_voice_client(interaction.user.voice.channel)

        if vc.is_playing():
            return await interaction.followup.send("WorstBot is already playing a message, please try again later", ephemeral = True)

        tts = BytesIO()
        await aiogTTS().write_to_fp(message, tts, tld = accent.value[0])
        tts.seek(0)
        vc.play(FFmpegPCMAudio(tts, executable = self.bot.dotenv.get("ffmpeg"), pipe = True, options = "-vn -loglevel quiet"))
        while vc.is_playing():
            await sleep(0.1)

        await interaction.followup.send("Finished playing message", ephemeral = True)

    @connect.error
    @send.error
    async def connect_error(self, interaction: Interaction, error):
        if isinstance(error, app_commands.CheckFailure):
            return await interaction.response.send_message("You are not connected to a voice channel", ephemeral = True)


async def setup(bot):
    await bot.add_cog(TTS(bot))

# todo: support language codes and wider tld choices
