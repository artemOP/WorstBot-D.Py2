import discord
from discord import app_commands, Interaction
from discord.ext import commands
from WorstBot import WorstBot
from modules import EmbedGen, Constants
from io import BytesIO


@app_commands.default_permissions(manage_channels = True, ban_members=True)
@app_commands.guild_only()
class PersonalCalls(commands.GroupCog, name = "personal-call"):

    def __init__(self, bot: WorstBot):
        super().__init__()
        self.bot = bot
        self.logger = self.bot.logger.getChild(self.qualified_name)

    async def cog_load(self) -> None:
        await self.bot.execute("CREATE TABLE IF NOT EXISTS personalcall(guild BIGINT UNIQUE, channel BIGINT UNIQUE)")
        await self.bot.execute("CREATE TABLE IF NOT EXISTS callblacklist(guild BIGINT NOT NULL, channel BIGINT UNIQUE)")
        await self.bot.execute("CREATE TABLE IF NOT EXISTS userblacklist(guild BIGINT NOT NULL, member BIGINT NOT NULL)")
        self.logger.info(f"{self.qualified_name} cog loaded")

    async def cog_unload(self) -> None:
        self.logger.info(f"{self.qualified_name} cog unloaded")

    @staticmethod
    async def text_archive(base_call: discord.VoiceChannel, personal_channel: discord.VoiceChannel) -> None:
        bytesIO = BytesIO()
        bytesIO.writelines([f"{message.created_at.strftime('%Y-%m-%d %H:%M:%S')} | {message.author} : {message.content}\n" async for message in personal_channel.history(limit = None)])
        bytesIO.seek(0)
        await base_call.send(file = discord.File(filename = f"{personal_channel.name} archive.txt", fp = bytesIO))

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if await self.bot.events(member.guild.id, self.bot._events.calls) is False:
            self.logger.debug(f"{member.guild.id} does not have calls enabled")
            return

        channel_id = await self.bot.fetchval("SELECT channel FROM personalcall WHERE guild=$1", member.guild.id)
        base_call: discord.VoiceChannel = await self.bot.maybe_fetch_channel(channel_id)  # type: Ignore
        if base_call is None:
            self.logger.debug(f"{member.guild.id} does not have a base call set")
            return

        call_blacklist = await self.bot.fetch("SELECT channel FROM callblacklist WHERE guild=$1", member.guild.id)
        user_blacklist = await self.bot.fetch("SELECT member FROM userblacklist WHERE guild=$1", member.guild.id)
        if any(member.id == record["member"] for record in user_blacklist):
            self.logger.debug(f"{member} is blacklisted from personal calls")
            await member.edit(voice_channel = None)

        if after.channel == base_call:
            self.logger.debug(f"call created in {member.guild} for {member}")
            personal_call = await base_call.category.create_voice_channel(name = member.name, user_limit = 99, bitrate = member.guild.bitrate_limit)
            await member.move_to(personal_call, reason = "WorstBot Personal Calls")

        if before.channel not in (base_call, None):
            if any(before.channel.id == record["channel"] for record in call_blacklist) or before.channel.members:
                self.logger.debug(f"{before.channel} is protected or has members")
                return

            # if await self.bot.events(member.guild.id, self.bot._events.textarchive):  # Disabled until message intent re-enabled
            #     self.logger.debug(f"archiving {before.channel} messages")
            #     await self.text_archive(base_call, before.channel)
            self.logger.debug(f"deleting {before.channel}")
            await before.channel.delete()

    @app_commands.command(name = "setup")
    async def PersonalCallSetup(self, interaction: Interaction, channel: discord.VoiceChannel = None):
        """Set a base call to spawn temporary calls from

        :param interaction:
        :param channel: The voice channel to set as the base call, leave blank to disable
        :return:
        """
        if not channel:
            await self.bot.execute("DELETE FROM personalcall WHERE channel = $1", channel.id)
        await self.bot.execute("INSERT INTO PersonalCall(guild, channel) VALUES($1, $2) ON CONFLICT (guild) DO UPDATE SET channel = EXCLUDED.channel", interaction.guild.id, channel.id)
        await interaction.response.send_message(f"the new base voice call is {channel}", ephemeral = True)

    @app_commands.command(name = "protect")
    async def CallBlacklistToggle(self, interaction: Interaction, channel: discord.VoiceChannel):
        """Prevent WorstBot from deleting the specified channel

        :param interaction:
        :param channel: The channel to protect
        :return:
        """
        if not await self.bot.fetchval("SELECT EXISTS(SELECT 1 FROM callblacklist WHERE guild = $1 AND channel = $2)", interaction.guild_id, channel.id):
            await self.bot.execute("INSERT INTO CallBlacklist(guild, channel) VALUES($1, $2)", interaction.guild_id, channel.id)
            await interaction.response.send_message(f"{channel} is now protected", ephemeral = True)
        else:
            await self.bot.execute("DELETE FROM CallBlacklist WHERE channel=$1", channel.id)
            await interaction.response.send_message(f"{channel} is no longer protected", ephemeral = True)

    @app_commands.command(name="protection-list")
    async def CallBlacklistList(self, interaction: Interaction):
        """List out protected channels

        :param interaction:
        :return:
        """
        channels = await self.bot.fetch("SELECT channel FROM CallBlacklist WHERE guild=$1 LIMIT 25", interaction.guild.id)
        embed = EmbedGen.FullEmbed(
            title = "Protected channels",
            fields = [EmbedGen.EmbedField(name = str(await self.bot.maybe_fetch_channel(channel["channel"])), value = Constants.BLANK) for channel in channels]
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name = "blacklist")
    async def UserBlacklist(self, interaction: Interaction, member: discord.Member):
        """Prevents a user from creating a personal call

        :param interaction:
        :param member: The member to add/remove from the blacklist
        :return:
        """
        if not await self.bot.fetchval("SELECT EXISTS(SELECT 1 FROM UserBlacklist WHERE guild = $1 AND member = $2)", interaction.guild_id, member.id):
            await self.bot.execute("INSERT INTO UserBlacklist(guild, member) VALUES($1, $2) ON CONFLICT DO NOTHING", interaction.guild_id, member.id)
            await interaction.response.send_message(f"{str(member)} has been added to the blacklist", ephemeral = True)
        else:
            await self.bot.execute("DELETE FROM UserBlacklist WHERE guild = $1 AND member = $2", interaction.guild_id, member.id)
            await interaction.response.send_message(f"{str(member)} has been removed from the blacklist", ephemeral = True)


async def setup(bot):
    await bot.add_cog(PersonalCalls(bot))
