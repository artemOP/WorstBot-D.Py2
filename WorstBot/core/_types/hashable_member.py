from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from discord import Member


class HashableMember:
    _member: Member

    def __hash__(self) -> int:
        return hash((self._member, self._member.guild)) << 22

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, self.__class__):
            return False
        return self._member == o._member
