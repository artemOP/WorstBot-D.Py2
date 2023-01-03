import discord
from discord import app_commands, Interaction
from discord.ext import commands
from WorstBot import WorstBot
from datetime import datetime
from os import remove
from modules import EmbedGen

@app_commands.default_permissions(manage_channels = True, ban_members=True)
class PersonalCalls(commands.GroupCog, name = "personal-call"):

    def __init__(self, bot: WorstBot):
        super().__init__()
        self.bot = bot

    async def cog_load(self) -> None:
        await self.bot.execute("CREATE TABLE IF NOT EXISTS personalcall(guild BIGINT UNIQUE, channel BIGINT UNIQUE)")
        await self.bot.execute("CREATE TABLE IF NOT EXISTS callblacklist(guild BIGINT NOT NULL, channel BIGINT UNIQUE)")
        await self.bot.execute("CREATE TABLE IF NOT EXISTS userblacklist(guild BIGINT NOT NULL, member BIGINT NOT NULL)")

    async def cog_unload(self) -> None:
        ...

    @commands.Cog.listener()
    async def on_ready(self):
        print("Personal call cog online")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if await self.bot.events(member.guild.id, self.bot._events.calls) is False:
            return
        PersonalChannel = self.bot.get_channel(await self.bot.fetchval("SELECT channel FROM PersonalCall WHERE guild=$1", member.guild.id))
        if PersonalChannel is None:
            return
        if await self.bot.fetchval("SELECT EXISTS(SELECT 1 FROM UserBlacklist WHERE guild = $1 AND member = $2)", member.guild.id, member.id) is True and after.channel is not None:
            # if after.channel.id == PersonalChannel.id:
            await member.edit(voice_channel = None)
            return
        if before.channel is None and after.channel is not None:
            if after.channel.id == PersonalChannel.id:
                channel = await after.channel.category.create_voice_channel(name = member.name, user_limit = 99, bitrate = member.guild.bitrate_limit)
                await member.move_to(channel)
        elif before.channel is not None and before.channel != PersonalChannel:
            if await self.bot.fetchval("SELECT EXISTS(SELECT 1 FROM CallBlacklist WHERE channel=$1)", before.channel.id) is True or before.channel.members:
                return
            if await self.bot.events(member.guild.id, self.bot._events.textarchive) is False:
                return await before.channel.delete()
            if not [message async for message in before.channel.history(limit=1)]:
                return await before.channel.delete()
            file = f"{member.name}-{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt"
            with open(file, "w+") as f:
                f.writelines([f"{message.created_at.strftime('%Y-%m-%d %H:%M:%S')} | {message.author} : {message.content}\n" async for message in before.channel.history(limit = None)])
            await PersonalChannel.send(file = discord.File(filename = file, description = "Text archive for Personal Calls", fp = file))
            remove(file)
            await before.channel.delete()

        if after.channel is not None and after.channel.id == PersonalChannel.id:
            await member.edit(voice_channel = None)

    @app_commands.command(name = "setup")
    async def PersonalCallSetup(self, interaction: Interaction, channel: discord.VoiceChannel = None):
        if not channel:
            await self.bot.execute("DELETE FROM personalcall WHERE channel = $1", channel.id)
        await self.bot.execute("INSERT INTO PersonalCall(guild, channel) VALUES($1, $2) ON CONFLICT (guild) DO UPDATE SET channel = EXCLUDED.channel", interaction.guild.id, channel.id)
        await interaction.response.send_message(f"the new base voice call is {channel}", ephemeral = True)

    @app_commands.command(name = "protect", description = "toggles if channel will be deleted when empty")
    async def CallBlacklistToggle(self, interaction: Interaction, channel: discord.VoiceChannel):
        if not await self.bot.fetchval("SELECT EXISTS(SELECT 1 FROM callblacklist WHERE guild = $1 AND channel = $2)", interaction.guild_id, channel.id):
            await self.bot.execute("INSERT INTO CallBlacklist(guild, channel) VALUES($1, $2)", interaction.guild_id, channel.id)
            await interaction.response.send_message(f"{channel} is now protected", ephemeral = True)
        else:
            await self.bot.execute("DELETE FROM CallBlacklist WHERE channel=$1", channel.id)
            await interaction.response.send_message(f"{channel} is no longer protected", ephemeral = True)

    @app_commands.command(name="protection-list", description = "Lists out channels blocked from deletion")
    async def CallBlacklistList(self, interaction: Interaction):
        channels = await self.bot.fetch("SELECT channel FROM CallBlacklist WHERE guild=$1 LIMIT 25", interaction.guild.id)
        embed = EmbedGen.FullEmbed(
            title = "Protected channels",
            fields = [EmbedGen.EmbedField(name = interaction.guild.get_channel(channel["channel"]).name, value = "\u200b") for channel in channels]
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name = "blacklist", description = "toggle a user ban on voice calls")
    async def UserBlacklist(self, interaction: Interaction, member: discord.Member):
        if not await self.bot.fetchval("SELECT EXISTS(SELECT 1 FROM UserBlacklist WHERE guild = $1 AND member = $2)", interaction.guild_id, member.id):
            await self.bot.execute("INSERT INTO UserBlacklist(guild, member) VALUES($1, $2) ON CONFLICT DO NOTHING", interaction.guild_id, member.id)
            await interaction.response.send_message(f"{str(member)} has been added to the blacklist", ephemeral = True)
        else:
            await self.bot.execute("DELETE FROM UserBlacklist WHERE guild = $1 AND member = $2", interaction.guild_id, member.id)
            await interaction.response.send_message(f"{str(member)} has been removed from the blacklist", ephemeral = True)


async def setup(bot):
    await bot.add_cog(PersonalCalls(bot))
