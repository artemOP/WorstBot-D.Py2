from types import MappingProxyType

from ._enums import RouletteColours

_cards: dict[str, int] = {
    "ace": 11,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "jack": 10,
    "queen": 10,
    "king": 10,
}

_roulette_number_colour_mapping: dict[int, RouletteColours] = {
    0: RouletteColours.green,
    1: RouletteColours.red,
    2: RouletteColours.black,
    3: RouletteColours.red,
    4: RouletteColours.black,
    5: RouletteColours.red,
    6: RouletteColours.black,
    7: RouletteColours.red,
    8: RouletteColours.black,
    9: RouletteColours.red,
    10: RouletteColours.black,
    11: RouletteColours.black,
    12: RouletteColours.red,
    13: RouletteColours.black,
    14: RouletteColours.red,
    15: RouletteColours.black,
    16: RouletteColours.red,
    17: RouletteColours.black,
    18: RouletteColours.red,
    19: RouletteColours.red,
    20: RouletteColours.black,
    21: RouletteColours.red,
    22: RouletteColours.black,
    23: RouletteColours.red,
    24: RouletteColours.black,
    25: RouletteColours.red,
    26: RouletteColours.black,
    27: RouletteColours.red,
    28: RouletteColours.black,
    29: RouletteColours.black,
    30: RouletteColours.red,
    31: RouletteColours.black,
    32: RouletteColours.red,
    33: RouletteColours.black,
    34: RouletteColours.red,
    35: RouletteColours.black,
    36: RouletteColours.red,
}

CARDS = MappingProxyType(_cards)
ROULETTE_NUMBERS = MappingProxyType(_roulette_number_colour_mapping)
