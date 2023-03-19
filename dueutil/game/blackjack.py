import discord
from discord import ButtonStyle, ui
from pydealer.deck import Deck

DEFAULT_TIMEOUT = 120

EQUIVALENTS = {"Jack": 10, "Queen": 10, "King": 10, "Ace": 11}


class BlackjackInteraction(ui.View):
    """
    Interaction for blackjack game

    Args:
        author (discord.User): The author of the interaction
        timeout (int, optional): The timeout of the interaction. Defaults to 120.
    """

    def __init__(self, author: discord.User, timeout=DEFAULT_TIMEOUT):
        self._author = author
        self.value = "stand"
        super().__init__(timeout=timeout)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self._author.id:
            return True

        await interaction.response.send_message("This is not your game!", ephemeral=True)

        return False

    async def start(self):
        await self.wait()
        return self.value

    @ui.button(label="Hit", style=ButtonStyle.primary)
    async def hit(self, interaction: discord.Interaction, _: ui.Button):
        await interaction.response.defer()
        self.value = "hit"
        self.stop()

    @ui.button(label="Stand", style=ButtonStyle.primary)
    async def stand(self, interaction: discord.Interaction, _: ui.Button):
        await interaction.response.defer()
        self.value = "stand"
        self.stop()


def get_deck_value(deck: Deck):
    value = 0
    aces = 0

    for card in deck:
        if card.value not in EQUIVALENTS:
            value += int(card.value)
        else:
            value += EQUIVALENTS[card.value]

        if card.value == "Ace":
            aces += 1

    for _ in range(aces):
        if value > 21:
            value -= 10
        else:
            break

    return value


def compare_decks(deck1: Deck, deck2: Deck):
    """
    return deck's value
    """
    deck1_value = get_deck_value(deck1)
    deck2_value = get_deck_value(deck2)

    return deck1_value, deck2_value
