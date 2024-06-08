from typing import TypedDict


class Segments(TypedDict):
    guild: int
    sponsor: bool
    selfpromo: bool
    interaction: bool
    intro: bool
    outro: bool
    preview: bool
    music_offtopic: bool
    filler: bool
