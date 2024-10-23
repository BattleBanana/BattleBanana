import discord
from discord import ButtonStyle, ui

DEFAULT_TIMEOUT = 120

class ValidationInteraction(ui.View):
    """
    Interaction for global weapon validation

    Args:
        author (discord.User): The author of the interaction
        timeout (int, optional): The timeout of the interaction. Defaults to 120.
    """

    def __init__(self, author: discord.User, timeout=DEFAULT_TIMEOUT):
        self._author = author
        self.value = "stop"
        super().__init__(timeout=timeout)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self._author.id:
            return True

        await interaction.response.send_message("This is not your validation!", ephemeral=True)

        return False

    async def start(self):
        await self.wait()
        return self.value

    @ui.button(label="Accept", style=ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, _: ui.Button):
        await interaction.response.defer()
        self.value = "accept"
        self.stop()

    @ui.button(label="Refuse", style=ButtonStyle.danger)
    async def refuse(self, interaction: discord.Interaction, _: ui.Button):
        await interaction.response.defer()
        self.value = "refuse"
        self.stop()

    @ui.button(label="Stop", style=ButtonStyle.secondary)
    async def stop(self, interaction: discord.Interaction, _: ui.Button):
        await interaction.response.defer()
        self.value = "stop"
        self.stop()
