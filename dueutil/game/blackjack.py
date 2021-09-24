import discord
from discord import ui, ButtonStyle
from pydealer.deck import Deck

DEFAULT_TIMEOUT = 120

EQUIVALENTS = {
    "Jack": 10,
    "Queen": 10,
    "King": 10,
    "Ace": 11
}

class Interactions(ui.View):
    def __init__(self, author = None, timeout = DEFAULT_TIMEOUT):
        self._author = author
        super().__init__(timeout=timeout)

    def _check(self, interaction_author):
        return interaction_author.id == self._author.id
    
    @ui.button(label='Hit', style=ButtonStyle.primary)
    async def hit(self, button: ui.Button, interaction: discord.Interaction):
        if self._check(interaction.user):
            self.value = "hit"
            self.stop()
        else:
            await interaction.response.send_message('This is not your game!', ephemeral=True)

    @ui.button(label='Stand', style=ButtonStyle.primary)
    async def stand(self, button: ui.Button, interaction: discord.Interaction):
        if self._check(interaction.user):
            self.value = "stand"
            self.stop()
        else:
            await interaction.response.send_message('This is not your game!', ephemeral=True)


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
    deck1Value = get_deck_value(deck1)
    deck2Value = get_deck_value(deck2)

    return deck1Value, deck2Value
