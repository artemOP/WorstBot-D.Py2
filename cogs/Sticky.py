import discord
from discord import app_commands
from discord.ext import commands
from WorstBot import WorstBot


@app_commands.default_permissions()
@app_commands.guild_only()
class StickyMessage(commands.GroupCog, name = "sticky"):
    def __init__(self, bot: WorstBot):
        self.bot = bot
        self.logger = self.bot.logger.getChild(self.qualified_name)

    async def cog_load(self) -> None:
        await self.bot.execute("CREATE TABLE IF NOT EXISTS sticky(channel BIGINT UNIQUE NOT NULL,messageid BIGINT, message TEXT NOT NULL )")
        self.logger.info(f"{self.qualified_name} cog loaded")

    async def cog_unload(self) -> None:
        self.logger.info(f"{self.qualified_name} cog unloaded")

    @app_commands.command(name = "add", description = "Pin a message to the bottom of a channel")
    async def StickyAdd(self, interaction: discord.Interaction, message: str):
        await self.bot.execute("INSERT INTO sticky(channel, messageid, message) VALUES($1, $2, $3) ON CONFLICT (channel) DO UPDATE SET messageid=NULL , message=excluded.message", interaction.channel_id, None, message)
        await interaction.response.send_message(f'"{message}" \n\nhas been added as a sticky.')

    @app_commands.command(name = "remove", description = "Remove pinned message")
    async def StickyRemove(self, interaction: discord.Interaction):
        await self.bot.execute("DELETE FROM sticky WHERE channel=$1", interaction.channel_id)
        await interaction.response.send_message('Sticky has been removed from this channel.', ephemeral = True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        sticky = await self.bot.fetchrow("SELECT * FROM sticky WHERE channel=$1", message.channel.id)
        if message.author.bot or not sticky:
            return
        if sticky["messageid"]:
            try:
                oldmessage = message.channel.get_partial_message(sticky["messageid"])
            except:
                oldmessage = message.channel.get_partial_message(message.channel.last_message_id)
            await oldmessage.delete()
        sticky = await message.channel.send(sticky["message"])
        await self.bot.execute("UPDATE sticky SET messageid=$1 WHERE channel=$2", sticky.id, message.channel.id)


async def setup(bot):
    await bot.add_cog(StickyMessage(bot))
