from enum import StrEnum, auto

__all__ = ("_events",)


class _events(StrEnum):
    autorole = auto()
    autoevent = auto()
    birthdays = auto()
    roles = auto()
    opinion = auto()
    calls = auto()
    textarchive = auto()
    twitch = auto()
    usage = auto()
    chatter_xp = auto()
