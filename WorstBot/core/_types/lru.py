from __future__ import annotations

from collections import UserDict
from collections.abc import Hashable
from datetime import datetime
from typing import TYPE_CHECKING, NamedTuple, TypeVar

if TYPE_CHECKING:
    from typing import Any

T = TypeVar("T", bound=Hashable)


class _Stats(NamedTuple):
    hits: int
    misses: int
    inserts: int
    pops: int
    len: int
    max_size: int


class LRU(UserDict[T, datetime]):
    def __init__(self, dict_: dict[T, datetime] = {}, max_size: int = 0):
        self._max_size = max_size
        self.hits = 0
        self.misses = 0
        self.inserts = 0
        self.pops = 0
        super().__init__(dict_)

    def __setitem__(self, key: T, value: datetime) -> None:
        if self._max_size == 0:
            self.data[key] = value
            self.inserts += 1
            return
        if len(self) >= self._max_size:
            oldest_key = min(self.data, key=self.get)  # type: ignore
            del self.data[oldest_key]
            self.pops += 1

        self.data[key] = value
        self.inserts += 1

    def __getitem__(self, key: T) -> datetime:
        value = self.data[key]
        self.data[key] = datetime.now()
        self.hits += 1
        return value

    def get(self, value: Hashable, default: Any = None) -> T:
        for key in self.data.keys():
            if hash(key) == hash(value):
                return key

        return default

    def set(self, key: T, value: datetime | None = None) -> None:
        self[key] = value or datetime.now()

    def cache_info(self) -> _Stats:
        return _Stats(self.hits, self.misses, self.inserts, self.pops, len(self), self._max_size)
