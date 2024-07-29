from __future__ import annotations

from math import sqrt
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

    from discord import Member, User


class Chatter:
    XP_STEP: int = 5

    def __init__(self, user: User | Member, xp: int, last_message: datetime) -> None:
        self._user: User | Member = user
        self._xp: int = xp
        self._last_message: datetime = last_message

    @property
    def user(self) -> User | Member:
        return self._user

    @property
    def xp(self) -> int:
        return self._xp

    @property
    def level(self) -> int:
        return self.xp_to_level(self.xp)

    @property
    def last_message(self) -> datetime:
        return self._last_message

    def __repr__(self) -> str:
        return f"<Chatter user={self.user} xp={self.xp} level={self.level} last_message={self.last_message}>"

    def __str__(self) -> str:
        return f"{self.user} has {self.xp} xp and is level {self.level}"

    def __hash__(self) -> int:
        return hash(self.user)

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, Chatter):
            return False
        return self.user == o.user

    @classmethod
    def xp_to_level(cls, xp: int) -> int:
        return int((sqrt(1 + 8 * xp / cls.XP_STEP) - 1) / 2)

    @classmethod
    def level_to_xp(cls, level: int) -> int:
        return int((cls.XP_STEP * level * (level + 1)) / 2)

    def add_xp(self, xp: int) -> bool:
        old_level = self.level
        self._xp += xp

        return old_level != self.level

    def can_xp(self, sent_at: datetime) -> bool:
        return (sent_at - self._last_message).total_seconds() >= 60
