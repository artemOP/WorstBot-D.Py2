import discord
from discord import app_commands
from discord.ext import commands


class PersonalCalls(commands.GroupCog, name = "personal-call"):

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.execute("CREATE TABLE IF NOT EXISTS personalcall(guild BIGINT UNIQUE, channel BIGINT UNIQUE)")
        await self.bot.execute("CREATE TABLE IF NOT EXISTS callblacklist(guild BIGINT, channel BIGINT)")
        await self.bot.execute("CREATE TABLE IF NOT EXISTS userblacklist(member BIGINT UNIQUE)")
        print("Personal call cog online")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        PersonalChannel = self.bot.get_channel(await self.bot.fetchval("SELECT channel FROM PersonalCall WHERE guild=$1", member.guild.id))
        if PersonalChannel is None:
            return
        if await self.bot.fetchval("SELECT EXISTS(SELECT 1 FROM UserBlacklist WHERE member=$1)", member.id) is True and after.channel is not None:
            # if after.channel.id == PersonalChannel.id:
            await member.edit(voice_channel = None)
            return
        if before.channel is None and after.channel is not None:
            if after.channel.id == PersonalChannel.id:
                channel = await after.channel.category.create_voice_channel(name = member.name, user_limit = 99, bitrate = member.guild.bitrate_limit)
                await member.move_to(channel)
        elif before.channel is not None and before.channel.id != PersonalChannel.id:
            if await self.bot.fetchval("SELECT EXISTS(SELECT 1 FROM CallBlacklist WHERE channel=$1)", before.channel.id) is False and before.channel.members == []:
                await before.channel.delete()
        if after.channel is not None and after.channel.id == PersonalChannel.id:
            await member.edit(voice_channel = None)

    @app_commands.command(name = "setup")
    @app_commands.default_permissions(manage_channels = True)
    async def PersonalCallSetup(self, interaction: discord.Interaction, channel: discord.VoiceChannel):
        await self.bot.execute("INSERT INTO PersonalCall(guild, channel) VALUES($1, $2) ON CONFLICT (guild) DO UPDATE SET channel = EXCLUDED.channel", interaction.guild.id, channel.id)
        await interaction.response.send_message(f"the new base voice call is {channel}", ephemeral = True)

    @app_commands.command(name = "call-protect-add")
    @app_commands.default_permissions(manage_channels = True)
    async def CallBlacklistAdd(self, interaction: discord.Interaction, channel: discord.VoiceChannel):
        await self.bot.execute("INSERT INTO CallBlacklist(guild, channel) VALUES($1, $2)", interaction.guild.id, channel.id)
        await interaction.response.send_message(f"{channel} is now protected", ephemeral = True)

    @app_commands.command(name = "call-protect-remove")
    @app_commands.default_permissions(manage_channels = True)
    async def CallBlacklistRemove(self, interaction: discord.Interaction, channel: int):
        await self.bot.execute("DELETE FROM CallBlacklist WHERE channel=$1", channel)
        await interaction.response.send_message("channel is no longer protected", ephemeral = True)

    @CallBlacklistRemove.autocomplete("channel")
    async def CallBlacklistRemoveAutocomplete(self, interaction: discord.Interaction, current):
        channels = await self.bot.fetch("SELECT channel FROM CallBlacklist WHERE guild=$1 LIMIT 25", interaction.guild.id)
        return [app_commands.Choice(name = self.bot.get_channel(channel["channel"]), value = channel["channel"]) for channel in channels]

    @app_commands.command(name="call-protect-list")
    @app_commands.default_permissions(manage_channels=True)
    async def CallBlacklistList(self, interaction: discord.Interaction):
        embed = discord.Embed(colour=discord.Colour.random(), title="Protected channels")
        channels = await self.bot.fetch("SELECT channel FROM CallBlacklist WHERE guild=$1 LIMIT 25", interaction.guild.id)
        for channel in channels:
            embed.add_field(name=self.bot.get_channel(channel["channel"]), value="\u200b")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="user-blacklist-add")
    @app_commands.default_permissions(ban_members=True)
    async def UserBlacklistAdd(self, interaction: discord.Interaction, member: discord.Member):
        await self.bot.execute("INSERT INTO UserBlacklist(member) VALUES($1) ON CONFLICT DO NOTHING", member.id)
        await interaction.response.send_message(f"{member.name} has been blacklisted from calls", ephemeral=True)

    @app_commands.command(name="user-blacklist-remove")
    @app_commands.default_permissions(ban_members=True)
    async def UserBlacklistRemove(self, interaction: discord.Interaction, member: discord.Member):
        await self.bot.execute("DELETE FROM UserBlacklist WHERE member=$1", member.id)
        await interaction.response.send_message(f"{member.name} is no longer blacklisted from calls", ephemeral=True)

    @app_commands.command(name="user-blacklist-search")
    @app_commands.default_permissions(ban_members=True)
    async def UserBlacklistSearch(self, interaction: discord.Interaction, member: discord.Member):
        if await self.bot.fetchval("SELECT EXISTS(SELECT 1 FROM UserBlacklist WHERE member=$1)", member.id) is True:
            await interaction.response.send_message(f"{member.name} is blacklisted from calls", ephemeral=True)
        else:
            await interaction.response.send_message(f"{member.name} is not blacklisted from calls", ephemeral=True)


async def setup(bot):
    await bot.add_cog(PersonalCalls(bot))
