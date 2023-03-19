"""
Helper classes to make sell/buy actions faster
"""

from abc import ABC, abstractmethod

from dueutil import util


class ShopBuySellItem(ABC):
    """
    This class is designed to make creating sell/buy
    commands faster. Given that the items work like themes/backgrounds/banners

    They must use player.equipped & player.inventory
    & have some properties with setters.

    It also assumes the use of !my<thing> and !set<thing>
    commands

    """

    # Set these values
    item_type = ""
    inventory_slot = ""
    default_item = "default"

    async def sell_item(self, item_name, **details):
        player = details["author"]
        channel = details["channel"]
        price_divisor = 4 / 3

        if item_name not in player.inventory[self.inventory_slot]:
            raise util.BattleBananaException(channel, self.item_type.title() + " not found!")
        if item_name == self.default_item:
            raise util.BattleBananaException(channel, "You can't sell that " + self.item_type + "!")

        item = self.get_item(item_name)
        sell_price = item.price // price_divisor
        setattr(player, self.item_type, self.default_item)
        player.inventory[self.inventory_slot].remove(item_name)
        player.money += sell_price
        await util.say(
            channel,
            (
                "**"
                + player.name_clean
                + "** sold the "
                + self.item_type
                + " **"
                + item.name_clean
                + "** for ``"
                + util.format_number(sell_price, money=True, full_precision=True)
                + "``"
            ),
        )
        player.save()

    async def buy_item(self, item_name, **details):
        customer = details["author"]
        channel = details["channel"]
        if item_name in customer.inventory[self.inventory_slot]:
            raise util.BattleBananaException(channel, "You already own that " + self.item_type)
        item = self.get_item(item_name)
        if item is None:
            raise util.BattleBananaException(channel, self.item_type.title() + " not found!")
        if not self.can_buy(customer, item):
            return True
        if customer.money - item.price >= 0:
            customer.money -= item.price
            customer.inventory[self.inventory_slot].append(item_name)
            message = (
                f"**{customer.name_clean}** bought the {self.item_type} **{item.name_clean}** "
                + f"for {util.format_number(item.price, money=True, ull_precision=True)}"
            )
            if self.item_equipped_on_buy(customer, item_name):
                await util.say(channel, message)
            else:
                await util.say(
                    channel,
                    (
                        message
                        + f"\n:warning: You have not yet set this {self.item_type}! Do **{details['cmd_key']}"
                        + (self.set_name if hasattr(self, "set_name") else self.item_type)
                        + f" {item_name}** to use this {self.item_type}"
                    ),
                )
            customer.save()
        else:
            await util.say(channel, ":anger: You can't afford that " + self.item_type + ".")

    def can_buy(self, customer, item):
        return True

    @abstractmethod
    def item_equipped_on_buy(self, player, item_name):
        """
        Equips the item if possible
        Returns true/false
        """
        pass

    @abstractmethod
    def get_item(self, item_name):
        pass
