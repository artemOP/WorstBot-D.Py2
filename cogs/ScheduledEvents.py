import discord
from discord.ext import commands, tasks
from WorstBot import WorstBot
from datetime import datetime as dt, timezone, timedelta
from asyncpg import Record


class Events(commands.Cog):

    def __init__(self, bot: WorstBot):
        self.bot = bot
        self.logger = self.bot.logger.getChild(self.qualified_name)

    async def cog_load(self) -> None:
        await self.bot.execute(
            "CREATE TABLE IF NOT EXISTS scheduled_events(event BIGINT PRIMARY KEY, guild BIGINT, expiretime timestamptz)"
        )
        self.Channel_Create.start()
        self.logger.info(f"{self.qualified_name} cog loaded")

    async def cog_unload(self) -> None:
        self.Channel_Create.stop()
        self.logger.info(f"{self.qualified_name} cog unloaded")

    @commands.Cog.listener()
    async def on_scheduled_event_create(self, event: discord.ScheduledEvent):
        if await self.bot.events(event.guild.id, self.bot._events.autoevent) is False:
            return
        if not event.channel:
            return
        if event.channel.id != await self.bot.fetchval(
            "SELECT channel FROM personalcall WHERE guild = $1", event.guild_id
        ):
            return
        await self.bot.execute(
            "INSERT INTO scheduled_events(event, guild, expiretime) VALUES($1, $2, $3)",
            event.id,
            event.guild_id,
            event.start_time,
        )

    @commands.Cog.listener()
    async def on_scheduled_event_delete(self, event: discord.ScheduledEvent):
        await self.bot.execute("DELETE FROM scheduled_events WHERE event = $1", event.id)

    @commands.Cog.listener()
    async def on_scheduled_event_update(self, before: discord.ScheduledEvent, after: discord.ScheduledEvent):
        if after.status is discord.EventStatus.active and after.start_time != discord.utils.utcnow():
            return await self.bot.execute("DELETE FROM scheduled_events WHERE event = $1", after.id)
        await self.bot.execute(
            "UPDATE scheduled_events SET expiretime = $1 WHERE event = $2", after.start_time, before.id
        )

    @tasks.loop(seconds=1)
    async def Channel_Create(self):
        events: list[Record] = await self.bot.fetch(
            "SELECT * FROM scheduled_events WHERE expiretime = (SELECT MIN(expiretime) FROM scheduled_events)"
        )
        if not events:
            return

        for row in events:  # type: Record
            if await self.bot.events(row["guild"], self.bot._events.autoevent) is False:
                continue
            if (row["expiretime"] - dt.now(timezone.utc)).days > 7:
                continue

            await discord.utils.sleep_until((row["expiretime"] - timedelta(minutes=10)))

            guild: discord.Guild = self.bot.get_guild(row["guild"])
            event: discord.ScheduledEvent = await self.bot.maybe_fetch_event(guild, row["event"])
            base_call_id = await self.bot.fetchval("SELECT channel FROM personalcall WHERE guild=$1", event.guild_id)
            base_call: discord.VoiceChannel = await self.bot.maybe_fetch_channel(base_call_id)  # type: ignore
            if not base_call:
                return await self.bot.execute("DELETE FROM scheduled_events WHERE event = $1", event.id)
            category: discord.CategoryChannel = base_call.category

            overwrites = {member: discord.PermissionOverwrite(view_channel=True) for member in guild.members} | {
                guild.self_role: discord.PermissionOverwrite(view_channel=True),
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
            }
            channel = await category.create_voice_channel(
                name=event.name,
                user_limit=99,
                bitrate=event.guild.bitrate_limit,
                overwrites=overwrites,
            )

            await event.edit(channel=channel, reason="WorstBot AutoEvent Startup")

            await self.bot.execute("DELETE FROM scheduled_events WHERE event = $1", event.id)

    @Channel_Create.before_loop
    async def BeforeReminder(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(Events(bot))
