from __future__ import annotations

from typing import TYPE_CHECKING, cast

import discord
from discord import Interaction, ui
from discord.utils import MISSING

from ... import Transactions, payout
from .._types import CARDS
from .._enums import GameState, PlayerState
from .embeds import Blackjack as BlackjackEmbed
from .game import Game
from .game_data import BlackJackData

if TYPE_CHECKING:
    from discord import Emoji

    from WorstBot import Bot

    from .. import GameManager, Player


class Blackjack(Game):
    def __init__(self, game: GameManager, player: Player, cards: list[Emoji]):
        super().__init__(game, player)
        self.cards: list[Emoji] = cards
        self.score = self.calculate_score(cards)

    @staticmethod
    def calculate_score(cards: list[Emoji]) -> int:
        score = 0
        names = []
        for card in cards:
            name = card.name.split("_")[1]
            names.append(name)
            score += CARDS[name]

        while score > 21 and "ace" in names:
            score -= 10
            names.remove("ace")

        return score

    async def wait_for_others(
        self,
        interaction: Interaction[Bot],
        embed: BlackjackEmbed | None = MISSING,
        content: str | None = MISSING,
    ) -> None:
        for children in self.children:
            if hasattr(children, "disabled"):
                children.disabled = True  # type: ignore

        await interaction.response.edit_message(view=self, embed=embed, content=content)
        if not any(player for player in self.game.players if player.state is PlayerState.playing):
            await self.game_end(interaction)

        if not filter(lambda player: player.state is PlayerState.playing, self.game.players):
            await self.game_end(interaction)

    @ui.button(label="Hit", style=discord.ButtonStyle.green)
    async def hit(self, interaction: Interaction[Bot], button: ui.Button):
        self.game.data = cast(BlackJackData, self.game.data)

        card = self.game.data["cards"].pop()
        self.cards.append(card)
        self.score = self.calculate_score(self.cards)

        embed = BlackjackEmbed(self.cards, self.score, [self.game.data["dealer_cards"][0], self.game.data["card_back"]])

        if self.score <= 21:
            return await interaction.response.edit_message(embed=embed)

        self.player.state = PlayerState.bust

        await self.wait_for_others(interaction, embed, "You've gone bust!")

    @ui.button(label="Stand", style=discord.ButtonStyle.gray)
    async def stand(self, interaction: Interaction[Bot], button: ui.Button):
        self.player.state = PlayerState.sticking
        await self.wait_for_others(interaction, content="Waiting for other players")

    @ui.button(label="Double Down", style=discord.ButtonStyle.red)
    async def double_down(self, interaction: Interaction[Bot], button: ui.Button):
        if self.player.wealth.wallet < self.player.bet:
            return await interaction.response.send_message("You don't have enough money to double down!")
        self.player._bet *= 2

        self.player.state = PlayerState.sticking
        await self.hit.callback(interaction)

        await self.wait_for_others(interaction, content="Waiting for other players")

    @ui.button(label="Fold", style=discord.ButtonStyle.red)
    async def fold(self, interaction: Interaction[Bot], button: ui.Button):
        self.player.state = PlayerState.bust
        await payout(interaction.client, self.player.wealth, Transactions.gamble, -self.player.bet)

        await self.wait_for_others(interaction, content="You have folded!")

    async def game_end(self, interaction: Interaction[Bot]):
        self.game.data = cast(BlackJackData, self.game.data)
        self.game.state = GameState.finished

        dealer_cards = self.game.data["dealer_cards"]
        if self.calculate_score(dealer_cards) < 17:
            dealer_cards.append(self.game.data["cards"].pop())
        dealer_score = self.calculate_score(dealer_cards)
        if dealer_score > 21:
            dealer_score = 0

        winners: list[Player] = []
        for player in self.game.players:
            if player.state is PlayerState.bust:
                await payout(interaction.client, self.player.wealth, Transactions.gamble, -self.player.bet)
                continue

            assert isinstance(player.view, Blackjack)
            if player.view.score < dealer_score:
                await payout(interaction.client, player.wealth, Transactions.gamble, -player.bet)
                continue

            if not winners:
                winners = [player]
                continue

            assert isinstance(winners[0].view, Blackjack)
            if player.view.score > winners[0].view.score:

                for loser in winners:
                    await payout(interaction.client, loser.wealth, Transactions.gamble, -loser.bet)

                winners = [player]
                continue
            elif player.view.score < winners[0].view.score:
                await payout(interaction.client, self.player.wealth, Transactions.gamble, -self.player.bet)
                continue

            winners.append(player)
        self.game.data["winners"] = winners
