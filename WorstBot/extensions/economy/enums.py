from enum import Enum
from typing import Any


class CONVERSION_WEIGHTS(Enum):
    crash = 0.005
    decrease = 0.5
    increase = 0.5
    boom = 0.005

    @classmethod
    def keys(cls) -> list[str]:
        return [key for key in cls.__members__.keys()]

    @classmethod
    def values(cls) -> list[Any]:
        return [value for value in cls.__members__.values()]
