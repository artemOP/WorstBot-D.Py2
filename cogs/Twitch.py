import discord
from discord import Interaction, app_commands
from discord.ext import commands, tasks
from WorstBot import WorstBot
from asyncio import sleep
from modules import Converters, EmbedGen

@app_commands.default_permissions()
class Twitch(commands.GroupCog, name = "twitch"):
    def __init__(self, bot: WorstBot):
        self.bot = bot
        self.TwitchClientId = self.bot.dotenv.get("twitch_client")
        self.TwitchSecret = self.bot.dotenv.get("twitch_secret")
        self.token = None
        self.streamersTable = None
        self.logger = self.bot.logger.getChild(self.qualified_name)

    async def cog_load(self) -> None:
        await self.bot.execute("CREATE TABLE IF NOT EXISTS twitch(guild BIGINT NOT NULL, channel BIGINT NOT NULL, userid BIGINT NOT NULL, role BIGINT, live BOOLEAN NOT NULL DEFAULT FALSE, UNIQUE(guild, userid))")
        await self.TokenGen()
        await self.streamers()
        self.request.start()
        self.logger.info(f"{self.qualified_name} cog loaded")

    async def cog_unload(self) -> None:
        self.request.stop()
        self.logger.info(f"{self.qualified_name} cog unloaded")

    async def streamers(self):
        self.streamersTable = await self.bot.fetch("SELECT * FROM twitch")

    async def validate(self, token: int):
        validity = await self.bot.get(url = "https://id.twitch.tv/oauth2/validate", headers = {"Authorization": f"Bearer {token}"})
        if validity["status"] == 200:
            return True
        await self.TokenGen()

    async def TokenGen(self):
        token = await self.bot.post(url = "https://id.twitch.tv/oauth2/token",
                                    params = {
                                        "client_id": self.TwitchClientId,
                                        "client_secret": self.TwitchSecret,
                                        "grant_type": "client_credentials"
                                    }
                                    )
        self.token = token.get("access_token")

    @app_commands.command(name = "add", description = "Get live alerts for your selected twitch channel")
    async def LiveTrackingAdd(self, interaction: Interaction, channel: discord.TextChannel, twitch_user: str, alert_role: discord.Role = None):
        twitch_user = Converters.to_int(twitch_user)
        if alert_role == interaction.guild.default_role:
            alert_role_id = 0
        elif alert_role is None:
            alert_role_id = None
        else:
            alert_role_id = alert_role.id
        await self.bot.execute("INSERT INTO twitch(guild, channel, userid, role) VALUES($1, $2, $3, $4) ON CONFLICT (guild, userid) DO UPDATE SET channel = excluded.channel, role = excluded.role", interaction.guild_id, channel.id, twitch_user, alert_role_id)
        await self.streamers()
        await interaction.response.send_message("Streamer has been added to the Tracking list", ephemeral = True)

    @app_commands.command(name = "remove", description = "Remove live alerts from your selected channel")
    async def LiveTrackingRemove(self, interaction: Interaction, twitch_user: str):
        twitch_user = Converters.to_int(twitch_user)
        await self.bot.execute("DELETE FROM twitch WHERE userid=$1", twitch_user)
        await self.streamers()
        await interaction.response.send_message("Streamer has been removed from the Tracking list", ephemeral = True)

    @LiveTrackingAdd.autocomplete("twitch_user")
    async def LiveTrackingAddAutocomplete(self, interaction: Interaction, current):
        if not await self.validate(self.token):
            return []
        if len(current) < 3:
            return []
        responses = await self.bot.get(url = "https://api.twitch.tv/helix/search/channels", params = {"query": current, "first": 25}, headers = {"client-id": self.TwitchClientId, "Authorization": "Bearer " + self.token})
        return [app_commands.Choice(name = response["display_name"], value = response["id"]) for response in responses["data"]]

    @LiveTrackingRemove.autocomplete("twitch_user")
    async def LiveTrackingRemoveAutocomplete(self, interaction: Interaction, current):
        if not await self.validate(self.token):
            return []
        streamIDs = await self.bot.fetch("SELECT userid FROM twitch WHERE guild=$1 LIMIT 25", interaction.guild_id)
        if not streamIDs:
            return []
        streamers = await self.bot.get(url = "https://api.twitch.tv/helix/channels", params = {"broadcaster_id": [streamID["userid"] for streamID in streamIDs]}, headers = {"client-id": self.TwitchClientId, "Authorization": "Bearer " + self.token})
        return [app_commands.Choice(name = streamer["broadcaster_name"], value = streamer["broadcaster_id"]) for streamer in streamers["data"]]

    @tasks.loop(minutes = 1, reconnect = True)
    async def request(self):
        if not await self.validate(self.token):
            return
        streams = await self.bot.get(url = "https://api.twitch.tv/helix/streams", params = {"user_id": [user["userid"] for user in self.streamersTable]}, headers = {"client-id": self.TwitchClientId, "Authorization": "Bearer " + self.token})

        for user in self.streamersTable:
            if await self.bot.events(user["guild"], self.bot._events.twitch) is False:
                return
            if not any(int(stream["user_id"]) == user["userid"] for stream in streams["data"]):
                await self.bot.execute("UPDATE twitch SET live = FALSE WHERE userid = $1", user["userid"])
                continue
            if await self.bot.fetchval("SELECT live FROM twitch WHERE userid=$1", user["userid"]) is True:
                continue

            await self.bot.execute("UPDATE twitch SET live = TRUE WHERE userid=$1", user["userid"])
            stream = [dictionary for dictionary in streams["data"] if int(dictionary["user_id"]) == user["userid"]][0]
            guild: discord.Guild = await self.bot.maybe_fetch_guild(user["guild"])
            channel: discord.PartialMessageable = self.bot.get_partial_messageable(user["channel"])

            print(user["role"])

            if user["role"] == 0:
                role_mention = "@everyone"
            elif user["role"] is None:
                role_mention = None
            else:
                role = guild.get_role(user["role"])
                role_mention = role.mention

            embed = EmbedGen.SimpleEmbed(
                author = {
                    "name": stream["user_name"],
                    "url": f"https://www.twitch.tv/{stream['user_name']}"
                },
                title = stream["user_name"],
                text = f"{stream['user_name']} just went live on twitch!\n{stream['title']}\nfind them at https://www.twitch.tv/{stream['user_name']}",
                footer = {"text": stream["started_at"].split("T")[1].split("Z")[0]},
                image = stream["thumbnail_url"].replace("-{width}x{height}", "")
            )
            await channel.send(embed=embed, content = role_mention)

    @request.before_loop
    async def before_my_task(self):
        await self.bot.wait_until_ready()
        await sleep(3)

async def setup(bot):
    await bot.add_cog(Twitch(bot))

