import discord
from discord import app_commands, Interaction
from discord.ext import commands
from discord.app_commands import Range, Choice
from os import environ, remove
from aiogtts import aiogTTS
from asyncio import sleep


class TTS(commands.GroupCog, name = "tts"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.exe = environ.get("ffmpeg")

    @commands.Cog.listener()
    async def on_ready(self):
        print("TTS cog online")

    @staticmethod
    def Choices() -> list[Choice[str]]:
        accents = {
            "Australia": "com.au",
            "United Kingdom": "co.uk",
            "United States": "com",
            "Canada": "ca",
            "India": "co.in",
        }
        return [Choice(name = accent[0], value = accent[1]) for accent in accents.items()]

    @staticmethod
    async def ChannelConnect(interaction: Interaction, channel: discord.VoiceChannel) -> discord.VoiceClient:
        vc = await channel.connect(self_deaf = True)
        await interaction.response.send_message(f"Connected to {channel.mention}", ephemeral = True)
        return vc

    async def VoiceCheck(self, guild):
        return discord.utils.get(self.bot.voice_clients, guild = guild)

    @app_commands.command(name = "connect", description = "Join/Leave Voice call")
    async def Voice(self, interaction: Interaction, channel: discord.VoiceChannel = None) -> None:
        if vc := await self.VoiceCheck(interaction.guild):
            await vc.disconnect(force = True)
            if not channel:
                return await interaction.response.send_message("Disconnected", ephemeral = True)

        if channel:
            if interaction.user in channel.members:
                await self.ChannelConnect(interaction, channel)
                return
            return await interaction.response.send_message(f"Please connect to {channel.mention} before running this command", ephemeral = True)

        if interaction.user.voice:
            await self.ChannelConnect(interaction, interaction.user.voice.channel)
            return

        await interaction.response.send_message("Please connect to a voice channel before running this command", ephemeral = True)

    @app_commands.command(name = "send", description = "Play tts message to the call")
    @app_commands.choices(accent = Choices())
    async def Send(self, interaction: Interaction, message: Range[str, 1, 250], accent: Choice[str] = None) -> None:
        if not (vc := await self.VoiceCheck(interaction.guild)):
            if channel := interaction.user.voice.channel:
                vc = await self.ChannelConnect(interaction, channel)
            else:
                return await interaction.response.send_message("Please connect to a voice channel before running this command", ephemeral = True)
        if vc.channel != interaction.user.voice.channel:
            return await interaction.response.send_message(f"Please connect to {vc.channel.mention} before running this command", ephemeral = True)
        if accent:
            accent = accent.value
        else:
            accent = "com"
        if vc.is_playing():
            return
        await aiogTTS().save(text = message, filename = str(interaction.id), tld = accent)
        vc.play(discord.FFmpegPCMAudio(source = str(interaction.id), executable = self.exe))
        await interaction.response.send_message(f'"{message}" is playing', ephemeral = True)
        while vc.is_playing():
            await sleep(1)
        remove(str(interaction.id))


async def setup(bot):
    await bot.add_cog(TTS(bot))
# todo: move off file saving, on to file like objects (custom ffmpeg class)
