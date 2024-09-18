from enum import IntEnum, StrEnum


class Games(StrEnum):
    blackjack = "blackjack"
    roulette = "roulette"


class GameState(IntEnum):
    cancelled = -1
    waiting = 0
    playing = 1
    finished = 2


class PlayerState(IntEnum):
    unready = 0
    ready = 1
    playing = 2
    sticking = 3
    bust = 4


class RouletteColours(StrEnum):
    red = "red"
    black = "black"
    green = "green"


class RouletteBets(StrEnum):
    red = "red 1:1"
    black = "black 1:1"
    odd = "odd 1:1"
    even = "even 1:1"
    low = "low 1:1 (1-18)"
    high = "high 1:1 (19-36)"
    column_1 = f"column 1 2:1 ({', '.join(str(i) for i in range(1, 37, 3))})"
    column_2 = f"column 2 2:1 ({', '.join(str(i) for i in range(2, 37, 3))})"
    column_3 = f"column 3 2:1 ({', '.join(str(i) for i in range(3, 37, 3))})"
    dozen_1 = "1st dozen 2:1 (1-12)"
    dozen_2 = "2nd dozen 2:1 (13-24)"
    dozen_3 = "3rd dozen 2:1 (25-36)"
    lower_straight_up = "straight up 35:1 (0-18)"
    upper_straight_up = "straight up 35:1 (19-36)"
    street = "street 11:1"
    basket = "basket 6:1"
