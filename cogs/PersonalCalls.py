import discord
from discord import app_commands
from discord.ext import commands
import discord.utils


class PersonalCalls(commands.Cog, app_commands.Group):
    UserBlacklistGroup = app_commands.Group(name="blacklist", description="Add/Remove/Search users to voice blacklist", default_permissions = discord.Permissions(ban_members=True),guild_only = True)
    CallBlacklistGroup = app_commands.Group(name="protect", description="Add/Remove/List calls to stop them being handled by PersonalCalls", default_permissions = discord.Permissions(manage_channels=True), guild_only = True)

    def __init__(self, bot):
        super().__init__(name="personal-call")
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        async with self.bot.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    "CREATE TABLE IF NOT EXISTS PersonalCall(guild BIGINT UNIQUE, channel BIGINT UNIQUE)")
                await conn.execute("CREATE TABLE IF NOT EXISTS CallBlacklist(guild BIGINT, channel BIGINT)")
                await conn.execute("CREATE TABLE IF NOT EXISTS UserBlacklist(member BIGINT UNIQUE)")
        print("Personal call cog online")

    async def fetch(self, sql: str, args: list):
        async with self.bot.pool.acquire() as conn:
            async with conn.transaction():
                return await conn.fetch(sql, *args)

    async def fetchval(self, sql: str, args: list):
        async with self.bot.pool.acquire() as conn:
            async with conn.transaction():
                return await conn.fetchval(sql, *args)

    async def execute(self, sql: str, args: list):
        async with self.bot.pool.acquire() as conn:
            async with conn.transaction():
                return await conn.fetchval(sql, *args)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        PersonalChannel = self.bot.get_channel(
            await self.fetchval("SELECT channel FROM PersonalCall WHERE guild=$1", [member.guild.id]))
        if await self.fetchval("SELECT EXISTS(SELECT 1 FROM UserBlacklist WHERE member=$1)",
                               [member.id]) is True and after.channel is not None:
            # if after.channel.id == PersonalChannel.id:
            await member.edit(voice_channel=None)
            return
        if before.channel is None and after.channel is not None:
            if after.channel.id == PersonalChannel.id:
                channel = await after.channel.category.create_voice_channel(name=member.name, user_limit=99,
                                                                            bitrate=member.guild.bitrate_limit)
                await member.move_to(channel)
        elif before.channel is not None and before.channel.id != PersonalChannel.id:
            if await self.fetchval("SELECT EXISTS(SELECT 1 FROM CallBlacklist WHERE channel=$1)",
                                   [before.channel.id]) is False and before.channel.members == []:
                await before.channel.delete()
        if after.channel is not None and after.channel.id == PersonalChannel.id:
            await member.edit(voice_channel=None)

    @app_commands.command(name="setup")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def PersonalCallSetup(self, interaction: discord.Interaction, channel: discord.VoiceChannel):
        await self.execute(
            "INSERT INTO PersonalCall(guild, channel) VALUES($1, $2) ON CONFLICT (guild) DO UPDATE SET channel = EXCLUDED.channel",
            [interaction.guild.id, channel.id])
        await interaction.response.send_message(f"the new base voice call is {channel}", ephemeral=True)

    @CallBlacklistGroup.command(name="add")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def CallBlacklistAdd(self, interaction: discord.Interaction, channel: discord.VoiceChannel):
        await self.execute("INSERT INTO CallBlacklist(guild, channel) VALUES($1, $2)",
                           [interaction.guild.id, channel.id])
        await interaction.response.send_message(f"{channel} is now protected", ephemeral=True)

    @CallBlacklistGroup.command(name="remove")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def CallBlacklistRemove(self, interaction: discord.Interaction, channel: discord.VoiceChannel):
        await self.execute("DELETE FROM CallBlacklist WHERE channel=$1", [channel.id])
        await interaction.response.send_message(f"{channel} is no longer protected", ephemeral=True)

    @CallBlacklistGroup.command(name="list")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def CallBlacklistList(self, interaction: discord.Interaction):
        embed = discord.Embed(colour=discord.Colour.random(), title="Protected channels")
        channels = await self.fetch("SELECT channel FROM CallBlacklist WHERE guild=$1 LIMIT 25", [interaction.guild.id])
        for channel in channels:
            embed.add_field(name=self.bot.get_channel(channel["channel"]), value="\u200b")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @UserBlacklistGroup.command(name="add")
    @app_commands.checks.has_permissions(ban_members=True)
    async def UserBlacklistAdd(self, interaction: discord.Interaction, member: discord.Member):
        await self.execute("INSERT INTO UserBlacklist(member) VALUES($1) ON CONFLICT DO NOTHING", [member.id])
        await interaction.response.send_message(f"{member.name} has been blacklisted from calls", ephemeral=True)

    @UserBlacklistGroup.command(name="remove")
    @app_commands.checks.has_permissions(ban_members=True)
    async def UserBlacklistRemove(self, interaction: discord.Interaction, member: discord.Member):
        await self.execute("DELETE FROM UserBlacklist WHERE member=$1", [member.id])
        await interaction.response.send_message(f"{member.name} is no longer blacklisted from calls", ephemeral=True)

    @UserBlacklistGroup.command(name="search")
    @app_commands.checks.has_permissions(ban_members=True)
    async def UserBlacklistRemove(self, interaction: discord.Interaction, member: discord.Member):
        if await self.fetchval("SELECT EXISTS(SELECT 1 FROM UserBlacklist WHERE member=$1)", [member.id]) is True:
            await interaction.response.send_message(f"{member.name} is blacklisted from calls", ephemeral=True)
        else:
            await interaction.response.send_message(f"{member.name} is not blacklisted from calls", ephemeral=True)


async def setup(bot):
    await bot.add_cog(PersonalCalls(bot))
