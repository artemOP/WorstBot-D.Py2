from __future__ import annotations

from typing import TYPE_CHECKING

from discord import Colour, Embed

from ...core import constants

if TYPE_CHECKING:
    from ...core.utils import embeds
    from . import Wealth


class Leaderboard(Embed):
    def __init__(self, wealths: list[Wealth], offset: int):
        super().__init__(title="Leaderboard", colour=Colour.random())
        self._fields: list[embeds.Fields] = [
            {
                "name": f"{offset + i + 1}: {wealth.member.display_name}",
                "value": f"W${wealth.wallet}",
                "inline": False,
            }
            for i, wealth in enumerate(wealths)
        ]

class Balance(Embed): 
    def __init__(self, wealth: Wealth):
        super().__init__(title="Balance", colour=Colour.random())
        self.set_author(name=wealth.member.display_name, icon_url=wealth.member.display_avatar.url)
        self._fields: list[embeds.Fields] = [
            {"name": "Wallet", "value": str(wealth.wallet), "inline": True},
            {"name": "Bank", "value": str(wealth.bank), "inline": True},
            {"name": "Tokens", "value": str(wealth.tokens), "inline": True},
            {"name": constants.BLANK, "value": constants.BLANK, "inline": True},
            {"name": "Multiplier", "value": str(wealth.multiplier), "inline": True},
            {"name": constants.BLANK, "value": constants.BLANK, "inline": True},
        ]


class KeypadTask(Embed):
    def __init__(self, code: list[str]):
        super().__init__(
            title="Keypad Task",
            description=f"Please enter the following code in the correct order:\n {",".join(code)}",
            colour=Colour.random(),
        )


class CountingTask(Embed):
    def __init__(self):
        super().__init__(title="Learning 2 count", description="Show off your counting skills", colour=Colour.random())


class TickTask(Embed):
    def __init__(self):
        super().__init__(title="Tick Task", description="Click the tick to complete the task", colour=Colour.random())
