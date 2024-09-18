from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, cast

import discord

from ....core.utils import paginators
from .. import Transactions, payout
from ._games import Blackjack, Roulette, embeds
from ._enums import Games, GameState, PlayerState
from ._player import Player

if TYPE_CHECKING:
    from discord import Interaction

    from WorstBot import Bot

    from .. import Wealth
    from ._games import BlackJackData, RouletteData


class GameManager:

    __slots__ = ("_mode", "state", "players", "data")

    def __init__(self, mode: Games, owner: Player, **kwargs: BlackJackData | RouletteData) -> None:
        self._mode = mode
        self.state = GameState.waiting
        self.players: list[Player] = [owner]
        self.data: BlackJackData | RouletteData = kwargs  # type: ignore

    @property
    def mode(self) -> Games:
        return self._mode

    async def add_player(self, wealth: Wealth, bet: float | int) -> Player:
        player = Player(wealth, bet)
        self.players.append(player)
        await self.update_player_count()
        return player

    async def remove_player(self, wealth: Wealth) -> None:
        for player in self.players:
            if player.wealth is not wealth:
                continue

            self.players.remove(player)
            break
        await self.update_player_count()
        return

    async def update_player_count(self) -> None:
        player_count = len(self.players)
        for player in self.players:
            if not player.view:
                continue

            embed = player.view.response.embeds[0].to_dict()
            embed["fields"][0]["value"] = f"{player_count}"  # type: ignore
            await player.view.response.edit(embed=discord.Embed.from_dict(embed))

    async def start(self, interaction: Interaction[Bot]) -> None:
        self.state = GameState.playing

        match self.mode:
            case Games.blackjack:
                self.data = cast(BlackJackData, self.data)

                for player in self.players:
                    if not player.view:
                        continue

                    cards = [self.data["cards"].pop(), self.data["cards"].pop()]
                    view = Blackjack(self, player, cards)
                    embed = embeds.Blackjack(cards, view.score, [self.data["dealer_cards"][0], self.data["card_back"]])

                    response = await player.view.response.edit(embed=embed, view=view)
                    view.response = response

                    player.view = view
                    player.state = PlayerState.playing

                while self.state is GameState.playing:
                    await asyncio.sleep(0.1)

                winners = self.data.get("winners", [])
                for winner in winners:
                    await payout(interaction.client, winner.wealth, Transactions.gamble, winner.bet * 2)

                assert isinstance(self.players[0].view, Blackjack)
                embed_list = await embeds.paginate_blackjack(
                    self.data["dealer_cards"],
                    self.players[0].view.calculate_score(self.data["dealer_cards"]),
                    winners,
                )
                view = paginators.ButtonPaginatedEmbeds(embed_list)
                for player in self.players:
                    if not player.view:
                        continue
                    response = await player.view.response.edit(view=view, embed=embed_list[0])
                    player.view.response = response

            case Games.roulette:
                self.data = cast(RouletteData, self.data)

            case _:
                raise NotImplementedError(f"Invalid game mode: {self.mode.name}")

    async def cancel(self, interaction: Interaction[Bot]) -> None:
        self.state = GameState.cancelled
        for player in self.players:
            if not player.view:
                continue

            await player.view.response.edit(
                view=None,
                embed=None,
                content="The game has been cancelled by the host",
                delete_after=30,
            )
        await interaction.response.send_message("The game has been cancelled", ephemeral=True)
