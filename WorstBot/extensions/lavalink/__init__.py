import logging
from typing import Literal
from .enums import Seek
import wavelink


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
    seconds = time % 60

    if hours == 0:
        return f"{minutes:02d}M:{seconds:02d}S"
    else:
        return f"{hours:02d}H:{minutes:02d}M:{seconds:02d}S"
