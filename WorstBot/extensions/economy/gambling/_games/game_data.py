from __future__ import annotations

from typing import TypedDict

from discord import Emoji

from .._player import Player


class _BlackJackData(TypedDict, total=True):
    cards: list[Emoji]
    card_back: Emoji | str
    dealer_cards: list[Emoji]


class BlackJackData(_BlackJackData, total=False):
    winners: list[Player]


class RouletteData(TypedDict): ...
