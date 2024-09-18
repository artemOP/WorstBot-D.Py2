from __future__ import annotations

from typing import TYPE_CHECKING

from discord import Colour, Embed

from .....core.utils.paginators import prepare_pages
from ...constants import PAGE_SIZE

if TYPE_CHECKING:
    from discord import Emoji

    from .....core.utils.embeds import Fields
    from .._player import Player


class Blackjack(Embed):
    def __init__(self, hand: list[Emoji], score: int, dealer: list[Emoji | str]):
        super().__init__(title="Blackjack", colour=Colour.random())
        self._fields: list[Fields] = [
            {"name": "Your hand", "value": "".join(str(card) for card in hand), "inline": True},
            {"name": "Your score", "value": str(score), "inline": True},
            {"name": "Dealer's hand", "value": "".join(str(card) for card in dealer), "inline": True},
        ]


class Roulette(Embed):
    def __init__(self):
        super().__init__()  # todo: fill out


class BlackJackWinners(Embed):
    def __init__(self, fields: list[Fields]):
        super().__init__(title="Blackjack winners", colour=Colour.random())
        self._fields = fields


async def paginate_blackjack(dealer_cards: list[Emoji], dealer_score: int, winners: list[Player]) -> list[Embed]:
    pages = prepare_pages(winners, PAGE_SIZE)
    embeds = []

    for page, players in enumerate(pages):
        fields: list[Fields] = [
            {"name": "Dealer's hand", "value": f"{dealer_score} | {"".join(str(card) for card in dealer_cards)}", "inline": True}
        ]
        for i, player in enumerate(players):
            fields.append(
                {
                    "name": f"{(page * PAGE_SIZE)+i}{player.wealth.member.display_name}",
                    "value": f"{player.view.score} | {player.view.cards}",  # type: ignore (view is blackjack)
                    "inline": False,
                }
            )
        embeds.append(BlackJackWinners(fields))
    return embeds
