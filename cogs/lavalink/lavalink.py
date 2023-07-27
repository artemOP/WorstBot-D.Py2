from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal
from datetime import timedelta
from enum import Enum

import discord
from discord import app_commands
from discord.ext import commands
from discord.app_commands import Transform, Transformer, Range
from discord.utils import MISSING, utcnow, format_dt

import wavelink
from wavelink import Playable
from wavelink.ext import spotify

from modules import EmbedGen, Paginators

if TYPE_CHECKING:
    from WorstBot import WorstBot
    from discord import Interaction
    from discord.app_commands import Choice
    from wavelink import Player, Playlist

class SearchType(Enum):
    Generic = wavelink.GenericTrack  # direct playback url
    YouTube = wavelink.YouTubeTrack
    YouTubeMusic = wavelink.YouTubeMusicTrack
    YouTubePlaylist = wavelink.YouTubePlaylist
    SoundCloud = wavelink.SoundCloudTrack
    Spotify = spotify.SpotifyTrack


class CustomSearch(Transformer):

    @staticmethod
    def get_platform(interaction: Interaction) -> SearchType:
        namespace_type = getattr(interaction.namespace, "search_type", SearchType.YouTube)
        return SearchType[namespace_type]

    @classmethod
    async def transform(cls, interaction: Interaction, value: str, /) -> Playable | Playlist:
        platform = cls.get_platform(interaction)
        if value.startswith("https://"):
            if platform is SearchType.YouTubePlaylist:
                return await wavelink.NodePool.get_playlist(value, cls = wavelink.YouTubePlaylist)
            else:
                tracks = await wavelink.NodePool.get_tracks(value, cls = platform.value)
        elif platform is any((SearchType.Spotify, SearchType.YouTubePlaylist, SearchType.Generic)) and not value.startswith("https://"):
            raise app_commands.TransformerError("A URL is required for this search type", discord.AppCommandOptionType.string, cls)
        else:
            tracks = await platform.value.search(value)
        return tracks[0]

    async def autocomplete(self, interaction: Interaction, value: str, /) -> list[Choice[str]]:
        platform = self.get_platform(interaction)
        search = await platform.value.search(value)
        return [app_commands.Choice(name = track.title, value = track.uri or track.title) for track in search[:25]]


@app_commands.guild_only()
class Lavalink(commands.GroupCog, name = "music"):

    def __init__(self, bot: WorstBot):
        self.bot = bot
        self.logger = self.bot.logger.getChild(self.qualified_name)

    async def cog_load(self) -> None:
        self.logger.info(f"{self.qualified_name} cog loaded")

    async def cog_unload(self) -> None:
        self.logger.info(f"{self.qualified_name} cog unloaded")

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: wavelink.TrackEventPayload):
        self.logger.debug(f"Track started: {payload.track.title}")

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEventPayload):
        if payload.player.autoplay:
            return
        track = await payload.player.queue.get_wait()
        if isinstance(track, wavelink.YouTubeTrack) or isinstance(track, spotify.SpotifyTrack):
            await payload.player.play(track, populate = True)
        else:
            await payload.player.play(track)

    @staticmethod
    def get_player(guild_id: int) -> wavelink.Player | MISSING:
        return wavelink.NodePool.get_node().get_player(guild_id) or MISSING

    async def voice_check(self, interaction: Interaction) -> wavelink.Player | bool:
        if not interaction.user.voice:
            return False

        player = self.get_player(interaction.guild_id)

        if player is MISSING:
            player = await interaction.user.voice.channel.connect(cls = wavelink.Player, self_deaf = True)
            return player
        elif interaction.user.voice.channel == player.channel:
            return player
        else:
            return True

    @app_commands.command(name = "join")
    async def join_vc(self, interaction: Interaction):
        """Tell WorstBot to connect to the current voice channel

        :param interaction:
        :return:
        """
        await interaction.response.defer(ephemeral = True)
        player: wavelink.Player | bool = await self.voice_check(interaction)
        if player is False:
            return await interaction.followup.send("Please connect to a voice channel before using music commands", ephemeral = True)
        elif player is True:
            return await interaction.followup.send("The bot is currently in use, please hold.")

    @app_commands.command(name = "disconnect")
    async def leave_vc(self, interaction: Interaction):
        """Tell WorstBot to leave the current voice channel

        :param interaction:
        :return:
        """
        await interaction.response.defer(ephemeral = True)
        player: wavelink.Player | bool = await self.voice_check(interaction)
        if isinstance(player, wavelink.Player):
            await player.disconnect(force = True)
            return await interaction.followup.send("Disconnected from voice channel", ephemeral = True)
        else:
            return await interaction.followup.send("The bot cannot be disconnected at this time", ephemeral = True)

    @app_commands.command(name = "play")
    async def play(self, interaction: Interaction, search_type: SearchType, search: Transform[Playable, CustomSearch]):
        """Play a song from a given platform

        :param interaction:
        :param search_type: The platform to search on (Spotify, Generic and Playlists are URL only)
        :param search: A title or URL to search for
        :return:
        """
        await interaction.response.defer(ephemeral = True)
        player: wavelink.Player | bool = await self.voice_check(interaction)
        if not isinstance(player, wavelink.Player):
            print(player)
            return await interaction.followup.send("Cannot play the song at this time", ephemeral = True)

        try:
            thumbnail = await search.fetch_thumbnail()
        except:
            thumbnail = None

        title = f"{getattr(search, 'title', None) or getattr(search, 'name', 'Title Missing')} - {getattr(search, 'author', 'Author Unknown')}"
        uri = getattr(search, 'uri', None)

        if player.current:
            player.queue.put(search)
            queue_length = sum(track.duration for track in player.queue)

            self.logger.debug(f"Added {title} to the queue")
            await interaction.followup.send(f"Added {title} to the queue", ephemeral = True)
            return await player.channel.send(
                embed = EmbedGen.FullEmbed(
                    author = {"name": "Added to queue:", "url": uri},
                    title = title,
                    thumbnail = thumbnail,
                    fields = [
                        EmbedGen.EmbedField(name = "Duration", value = timedelta(milliseconds = getattr(search, 'duration', 0))),
                        EmbedGen.EmbedField(name = "Position", value = len(player.queue) + 1),
                        EmbedGen.EmbedField(name = "Estimated time until playing", value = format_dt(utcnow() + timedelta(milliseconds = queue_length)))
                    ],
                    footer = {"text": f"Requested by: {interaction.user.mention}"}
                ),
                allowed_mentions = discord.AllowedMentions.none(),
                delete_after = queue_length / 1000
            )
        else:
            await player.play(search, volume = 500)
            self.logger.debug(f"Now playing {title}")
            await interaction.followup.send(f"Now playing {title}", ephemeral = True)
            return await player.channel.send(
                embed = EmbedGen.SimpleEmbed(
                    author = {"name": "Now playing:", "url": uri},
                    title = title,
                    thumbnail = thumbnail,
                    footer = {"text": f"Requested by: {interaction.user.mention}"}
                ),
                allowed_mentions = discord.AllowedMentions.none(),
                delete_after = search.duration / 1000
            )

    @app_commands.command(name = "pause")
    async def pause(self, interaction: Interaction):
        """Pause the current song

        :param interaction:
        :return:
        """
        await interaction.response.defer(ephemeral = True)
        player: wavelink.Player | bool = await self.voice_check(interaction)
        if not isinstance(player, wavelink.Player):
            return await interaction.followup.send("Cannot pause the player at this time", ephemeral = True)
        elif player.is_paused:
            return await interaction.followup.send("The player is already paused", ephemeral = True)
        else:
            await player.pause()
            return await interaction.followup.send("Paused the player", ephemeral = True)

    @app_commands.command(name = "resume")
    async def resume(self, interaction: Interaction):
        """Resume the current song

        :param interaction:
        :return:
        """
        await interaction.response.defer(ephemeral = True)
        player: wavelink.Player | bool = await self.voice_check(interaction)
        if not isinstance(player, wavelink.Player):
            return await interaction.followup.send("Cannot resume the player at this time", ephemeral = True)
        elif player.is_paused:
            await player.resume()
            return await interaction.followup.send("Resumed the player", ephemeral = True)
        else:
            return await interaction.followup.send("The player is already paused", ephemeral = True)

    @app_commands.command(name = "stop")
    async def stop(self, interaction: Interaction):
        """Stop playback AND clear the current queue

        :param interaction:
        :return:
        """
        await interaction.response.defer(ephemeral = True)
        player: wavelink.Player | bool = await self.voice_check(interaction)
        if not isinstance(player, wavelink.Player):
            return await interaction.followup.send("Cannot stop the player at this time", ephemeral = True)

        player.queue.clear()
        player.auto_queue.clear()
        await player.set_filter(wavelink.Filter())
        player.queue.loop = False
        player.queue.loop_all = False
        await player.stop()

        return await interaction.followup.send("Stopped the player", ephemeral = True)

    @app_commands.command(name = "skip")
    async def skip(self, interaction: Interaction, amount: int = 1):
        """Skip `amount` songs in the queue (defaults to 1)

        :param interaction:
        :param amount:
        :return:
        """
        await interaction.response.defer(ephemeral = True)
        player: wavelink.Player | bool = await self.voice_check(interaction)
        if not isinstance(player, wavelink.Player):
            return await interaction.followup.send("Unable to skip", ephemeral = True)
        count = 1
        if amount > 1:
            async for _ in player.queue:
                count += 1
                amount -= 1
                if amount <= 1:
                    break
        await player.stop(force = True)
        return await interaction.followup.send(f"Skipped {count} song", ephemeral = True)

    @app_commands.command(name = "move_to")
    async def move_to(self, interaction: Interaction, channel: discord.VoiceChannel = None):
        """Move the bot to a different voice channel (defaults to the user's channel)

        :param interaction:
        :param channel: The OPTIONAL channel to move into
        :return:
        """
        await interaction.response.defer(ephemeral = True)
        player: wavelink.Player | bool = await self.voice_check(interaction)
        if player is True:
            return await interaction.followup.send("The bot is currently in use, please hold.", ephemeral = True)
        elif player is False:
            player = self.get_player(interaction.guild_id)
            if len(player.channel.members) == 1:
                await player.move_to(interaction.user.voice.channel)
                return player
            return await interaction.followup.send("The bot is currently in use, please hold.", ephemeral = True)
        else:
            await player.move_to(channel or interaction.user.voice.channel)

    @app_commands.command(name = "seek")
    async def seek(self, interaction: Interaction, direction: Literal["forward", "backward"], position: int):
        """Seek to a specific position in the current song

        :param interaction:
        :param direction: The direction to seek in
        :param position: The number of second to jump by
        :return:
        """
        await interaction.response.defer(ephemeral = True)
        player: wavelink.Player | bool = await self.voice_check(interaction)
        if not isinstance(player, wavelink.Player):
            return await interaction.followup.send("Unable to seek", ephemeral = True)
        if direction == "forward":
            await player.seek(int(player.position + (position * 1000)))
        elif direction == "backward":
            await player.seek(int(player.position - (position * 1000)))
        else:
            return await interaction.followup.send("Invalid direction", ephemeral = True)

        return await interaction.followup.send(f"Seeked to {player.position}", ephemeral = True)

    @app_commands.command(name = "volume")
    async def volume(self, interaction: Interaction, volume: Range[int, 0, 100]):
        """Set a new volume for the current player (as a %)

        :param interaction:
        :param volume:
        :return:
        """
        await interaction.response.defer(ephemeral = True)
        player: wavelink.Player | bool = await self.voice_check(interaction)
        if not isinstance(player, wavelink.Player):
            return await interaction.followup.send("Unable to change the volume", ephemeral = True)
        await player.set_volume(volume * 10)

    @app_commands.command(name = "shuffle")
    async def shuffle(self, interaction: Interaction):
        """Shuffle the current queue

        :param interaction:
        :return:
        """
        await interaction.response.defer(ephemeral = True)
        player: wavelink.Player | bool = await self.voice_check(interaction)
        if not isinstance(player, wavelink.Player):
            return await interaction.followup.send("Unable to shuffle", ephemeral = True)
        player.queue.shuffle()
        return await interaction.followup.send("Shuffled the queue", ephemeral = True)

    @app_commands.command(name = "loop")
    async def loop(self, interaction: Interaction, mode: Literal["track", "queue", "off"]):
        """Loop the current track or queue

        :param interaction:
        :param mode: Loop type
        :return:
        """
        await interaction.response.defer(ephemeral = True)
        player: wavelink.Player | bool = await self.voice_check(interaction)
        if not isinstance(player, wavelink.Player):
            return await interaction.followup.send("Unable to loop", ephemeral = True)
        if mode == "track":
            player.queue.loop = True
            player.queue.loop_all = False
            return await interaction.followup.send("Looping the current track", ephemeral = True)
        elif mode == "queue":
            player.queue.loop = False
            player.queue.loop_all = True
            return await interaction.followup.send("Looping the queue", ephemeral = True)
        elif mode == "off":
            player.queue.loop = False
            player.queue.loop_all = False
            return await interaction.followup.send("Disabled looping", ephemeral = True)
        else:
            return await interaction.followup.send("Invalid loop type", ephemeral = True)

    @app_commands.command(name = "current")
    async def current_song(self, interaction: Interaction):
        """Get the current song

        :param interaction:
        :return:
        """
        await interaction.response.defer(ephemeral = True)
        player: wavelink.Player | bool = await self.voice_check(interaction)
        if not isinstance(player, wavelink.Player) or not player.current:
            return await interaction.followup.send("No song is currently playing", ephemeral = True)
        return await interaction.followup.send(getattr(player.current, "uri", player.current.title), ephemeral = True)

    @app_commands.command(name = "queue")
    async def queue(self, interaction: Interaction):
        """View the current queue

        :param interaction:
        :return:
        """
        await interaction.response.defer(ephemeral = True)
        player: wavelink.Player | bool = await self.voice_check(interaction)
        if not isinstance(player, wavelink.Player):
            return await interaction.followup.send("No songs in queue", ephemeral = True)

        embed_list = EmbedGen.EmbedFieldList(
            title = "Queue",
            fields = [EmbedGen.EmbedField(name = getattr(song, "title", "Unknown title"), value = getattr(song, "author", "Unknown author"), inline = False) for song in player.queue],
            max_fields = 5
        )
        view = Paginators.ButtonPaginatedEmbeds(embed_list)
        await interaction.followup.send(view = view, embed = embed_list[0], ephemeral = True)
        view.response = await interaction.original_response()

    @app_commands.command(name = "autoplay")
    async def autoplay(self, interaction: Interaction, enabled: bool):
        """Automatically add suggested songs to the queue (manual queue prioritized)

        :param interaction:
        :param enabled: True | False
        :return:
        """
        await interaction.response.defer(ephemeral = True)
        player: wavelink.Player | bool = await self.voice_check(interaction)
        if not isinstance(player, wavelink.Player):
            return await interaction.followup.send("Unable to change autoplay", ephemeral = True)
        player.queue.autoplay = enabled
        return await interaction.followup.send(f"Autoplay is now {enabled}", ephemeral = True)

    @app_commands.command(name = "history")
    async def history(self, interaction: Interaction):
        """Returns the playback history for the current player

        :param interaction:
        :return:
        """
        await interaction.response.defer(ephemeral = True)
        player: wavelink.Player | bool = await self.voice_check(interaction)
        if not isinstance(player, wavelink.Player):
            return await interaction.followup.send("No songs in history", ephemeral = True)

        embed_list = EmbedGen.EmbedFieldList(
            title = "Queue",
            fields = [EmbedGen.EmbedField(name = getattr(song, "title", "Unknown title"), value = getattr(song, "uri", song.source), inline = False) for song in player.queue.history],
            max_fields = 5
        )
        view = Paginators.ButtonPaginatedEmbeds(embed_list)
        await interaction.followup.send(view = view, embed = embed_list[0], ephemeral = True)
        view.response = await interaction.original_response()

    @play.error
    async def play_error(self, interaction: Interaction, error: Exception):
        if isinstance(error, app_commands.TransformerError):
            if interaction.is_expired():
                return
            elif interaction.response.is_done():
                return await interaction.followup.send("Unable to find that song", ephemeral = True)
            else:
                return await interaction.response.send_message("Unable to find that song", ephemeral = True)

async def setup(bot):
    await bot.add_cog(Lavalink(bot))


# todo filter impl
