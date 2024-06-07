from __future__ import annotations

from typing import TYPE_CHECKING

from discord import Colour, Embed

from . import humanize_ms

if TYPE_CHECKING:
    from wavelink import Playable, Queue


async def generate_current_song(song: Playable) -> Embed:
    embed = Embed(
        title="Currently playing",
        colour=Colour.random(),
        url=song.uri,
        description=song.title,
    )
    embed.set_thumbnail(url=song.artwork)
    embed.add_field(name="Author", value=song.author)
    embed.add_field(name="Requested by", value=song.extras.requester)
    embed.add_field(name="Duration", value=humanize_ms(song.length))

    return embed


async def paginate_songs(queue: Queue) -> list[Embed]:
    embeds = []
    for i, song in enumerate(queue):
        embed = await generate_current_song(song)
        embed.set_footer(text=f"Song {i + 1}/{queue.count}")

    return embeds


async def generate_queue(queue: Queue) -> list[Embed]: ...
