from enum import StrEnum, auto

__all__ = ("events_",)


class events_(StrEnum):
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
