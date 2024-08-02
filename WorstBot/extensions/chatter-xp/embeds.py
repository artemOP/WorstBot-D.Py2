from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

import discord
from discord import Colour, Embed

if TYPE_CHECKING:
    from . import Chatter


class Fields(TypedDict):
    name: str
    value: str
    inline: bool


class LevelUp(Embed):
    def __init__(self, chatter: Chatter):
        super().__init__(title="Level Up!", colour=Colour.random())
        self.set_author(name=chatter.user.display_name, icon_url=chatter.user.display_avatar.url)
        self._fields: list[Fields] = [
            {"name": "Level", "value": str(chatter.level), "inline": True},
            {"name": "XP", "value": str(chatter.xp), "inline": True},
        ]


class CurrentXP(Embed):
    def __init__(self, chatter: Chatter):
        super().__init__(title="Current XP", colour=Colour.random())
        self.set_author(name=chatter.user.display_name, icon_url=chatter.user.display_avatar.url)
        self._fields: list[Fields] = [
            {"name": "Level", "value": str(chatter.level), "inline": True},
            {"name": "XP", "value": str(chatter.xp), "inline": True},
            {"name": "Next Level", "value": f"{chatter.xp/chatter.level_to_xp(chatter.level + 1):.1%}", "inline": True},
        ]


class Leaderboard(Embed):
    def __init__(self, chatters: list[Chatter], offset: int):
        super().__init__(title="Leaderboard", colour=Colour.random())
        self._fields: list[Fields] = [
            {
                "name": f"{offset + i + 1}: {chatter.user.display_name}",
                "value": f"Level: {chatter.level} ({chatter.xp} xp)",
                "inline": False,
            }
            for i, chatter in enumerate(chatters)
        ]
