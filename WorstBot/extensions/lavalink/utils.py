from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal

import wavelink

if TYPE_CHECKING:
    from discord import Interaction

    from WorstBot import Bot

    from . import Segments


def get_player(guild_id: int) -> wavelink.Player | None | Literal[False]:
    try:
        node = wavelink.Pool.get_node()
    except wavelink.InvalidNodeException as e:
        logging.getLogger("wavelink.node").exception(e)
        return False
    return node.get_player(guild_id)


def humanize_ms(time: float | int) -> str:
    """Convert milliseconds to human readable time.

    Args:
        time (float | int): ms to convert.

    Returns:
        str: HH:MM:SS or MM:SS format.
    """
    time /= 1000

    hours = time // 3600
    minutes = (time % 3600) // 60
    seconds = round(time % 60)

    if hours == 0:
        return f"{minutes:n}:{seconds:n}"
    else:
        return f"{hours:n}:{minutes:n}:{seconds:n}"


async def fetch_segments(interaction: Interaction[Bot]) -> Segments | None:
    segments: Segments = await interaction.client.pool.fetchrow(
        "SELECT * FROM sponsor_block WHERE guild_id = $1", interaction.guild_id
    )
    return None if not segments else dict(segments)  # type: ignore


async def set_segments(interaction: Interaction[Bot], segments: Segments) -> None:
    await interaction.client.pool.execute(
        "INSERT INTO sponsor_block VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9) ON CONFLICT (guild_id) DO UPDATE SET sponsor=EXCLUDED.sponsor, selfpromo=EXCLUDED.selfpromo, interaction=EXCLUDED.interaction, intro=EXCLUDED.intro, outro=EXCLUDED.outro, preview=EXCLUDED.preview, music_offtopic=EXCLUDED.music_offtopic, filler=EXCLUDED.filler",
        *segments.values(),
    )
