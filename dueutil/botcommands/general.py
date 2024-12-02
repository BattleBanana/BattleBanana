import inspect
from functools import wraps

import discord

import generalconfig as gconf

from .. import commands, util
from ..game import customizations, weapons
from ..game.helpers.shopabstract import ShopBuySellItem
from . import player as player_cmds
from . import weapon as weap_cmds

### Fill in the blanks buy/sell functions
DEPARTMENT_NOT_FOUND = "Department not found"
ITEM_NOT_FOUND = "Item not found!"
DEFAULT_BANNER = "discord blue"


class BuySellTheme(ShopBuySellItem):
    """A class for buying and selling themes."""

    item_type = "theme"
    inventory_slot = "themes"

    def item_equipped_on_buy(self, player, item_name):
        if player.equipped["theme"] == "default":
            player.theme = item_name
            return True
        return False

    def get_item(self, item_name):
        return customizations.get_theme(item_name)


class BuySellBanner(ShopBuySellItem):
    """A class for buying and selling banners."""

    item_type = "banner"
    inventory_slot = "banners"
    default_item = DEFAULT_BANNER

    def item_equipped_on_buy(self, player, item_name):
        if player.equipped["banner"] == DEFAULT_BANNER:
            player.banner = item_name
            return True
        return False

    def get_item(self, item_name):
        return customizations.get_banner(item_name)


class BuySellBackground(BuySellTheme):
    """A class for buying and selling backgrounds."""

    item_type = "background"
    inventory_slot = "backgrounds"
    set_name = "bg"

    def item_equipped_on_buy(self, player, item_name):
        if player.equipped["background"] == "default":
            player.background = item_name
            return True
        return False

    def get_item(self, item_name):
        return customizations.get_background(item_name)


buy_sell_themes = BuySellTheme()
buy_sell_backgrounds = BuySellBackground()
buy_sell_banners = BuySellBanner()


def _shop_sort(item):
    return item["price"], item["name"]


def _should_show_in_shop(customization):
    return customization is not None and not (customization.id == "default" or customization.is_hidden())


def filter_customizations(customization_items):
    items_hidden_removed = [
        customization for customization in customization_items if _should_show_in_shop(customization)
    ]
    items_hidden_removed.sort(key=_shop_sort)
    return items_hidden_removed


def shop_weapons_list(page, **details):
    shop_weapons = list(weapons.get_weapons_for_server(details["server"]).values())
    shop_weapons.remove(weapons.NO_WEAPON)
    shop_weapons.sort(key=lambda weapon: weapon.price)
    shop_list = weap_cmds.weapons_page(
        shop_weapons,
        page,
        title="BattleBanana's Weapon Shop!",
        footer_more=f"But wait there's more! Do {details['cmd_key']}shop weapons {page + 2}",
        footer_end=(f"Want more? Ask an admin on {details['server_name']} to add some!"),
    )
    return shop_list


def shop_theme_list(page, **details):
    themes = list(customizations.get_themes().values())
    themes = filter_customizations(themes)
    shop_list = player_cmds.theme_page(
        themes,
        page,
        title="BattleBanana's Theme Shop!",
        footer_more=f"But wait there's more! Do {details['cmd_key']}shop themes {page + 2}",
        footer_end="More themes coming soon!",
    )
    return shop_list


def shop_background_list(page, **details):
    backgrounds = list(customizations.backgrounds.values())
    backgrounds = filter_customizations(backgrounds)
    # Allow for hidden backgrounds (only used for certain themes - probably won't need for other things)
    shop_list = player_cmds.background_page(
        backgrounds,
        page,
        title="BattleBanana's Background Shop!",
        footer_more="But wait there's more! Do " + details["cmd_key"] + "shop bgs " + str(page + 2),
        footer_end="More backgrounds coming soon!",
    )
    return shop_list


def shop_banner_list(page, **details):
    banners = list(customizations.banners.values())
    banners = [banner for banner in banners if banner.can_use_banner(details["author"]) and banner.id != DEFAULT_BANNER]
    banners.sort(key=_shop_sort)
    shop_list = player_cmds.banner_page(
        banners,
        page,
        title="BattleBanana's Banner Shop!",
        footer_more="But wait there's more! Do " + details["cmd_key"] + "shop banners " + str(page + 2),
        footer_end="More banners coming soon!",
    )
    return shop_list


def get_department_from_name(name):
    return next(
        (department_info for department_info in departments.values() if name.lower() in department_info["alias"]), None
    )


async def guess_department_from_item_name(item_name, **details):
    exists_check = details.get("exists_check", "item_exists")
    message = details.get("error", "An item with that name exists in multiple departments!")
    possible_departments = [
        department_info for department_info in departments.values() if department_info[exists_check](details, item_name)
    ]
    if len(possible_departments) > 1:
        error = ":confounded: " + message + "\n" + "Please be more specific!\n"
        if " " in item_name:
            item_name = f'"{item_name}"'
        for department_info in possible_departments:
            error += (
                "``"
                + details["cmd_key"]
                + details["command_name"]
                + " "
                + department_info["alias"][0]
                + " "
                + item_name
                + "``\n"
            )
        await util.say(details["channel"], error)
        return None  # Too many possible departments
    elif len(possible_departments) == 0:
        raise util.BattleBananaException(details["channel"], ITEM_NOT_FOUND)
    return possible_departments[0]


async def item_action(item_name, action, department=None, **details):
    # Does not support list action page. Since I have no case where I need that.
    exists_check = details.get("exists_check", "item_exists")
    if department is None:
        # We have to find where it could be
        department = await guess_department_from_item_name(item_name, **details)

        if department is None:
            return

    # We should know have a department if we get this far
    # First condition we found it so must exist. 2nd We were given the department.
    if "possible_departments" in locals() or department[exists_check](details, item_name):
        action = department["actions"][action]
        if inspect.iscoroutinefunction(action):
            action_result = await action(item_name, **details)
        else:
            action_result = action(item_name, **details)
        if isinstance(action_result, discord.Embed):
            await util.say(details["channel"], embed=action_result)
    else:
        raise util.BattleBananaException(details["channel"], ITEM_NOT_FOUND)


def _placeholder(_, **details):
    embed = details["embed"]
    embed.title = "Department closed"
    return embed


departments = {
    "weapons": {
        "alias": ["weapons", "weaps", "weap", "weapon"],
        "actions": {
            "info_action": weap_cmds.weapon_info,
            "list_action": shop_weapons_list,
            "buy_action": weap_cmds.buy_weapon,
            "sell_action": weap_cmds.sell_weapon,
        },
        "item_exists": lambda details, name: name.lower() != "none"
        and weapons.does_weapon_exist(details["server_id"], name),
        "item_exists_sell": lambda details, name: (
            name != "none" and details["author"].weapon.name.lower() == name or details["author"].owns_weapon(name)
        ),
    },
    "themes": {
        "alias": ["themes", "skins", "theme", "skin"],
        "actions": {
            "info_action": player_cmds.theme_info,
            "list_action": shop_theme_list,
            "buy_action": buy_sell_themes.buy_item,
            "sell_action": buy_sell_themes.sell_item,
        },
        "item_exists": lambda _, name: (
            name.lower() != "default" and _should_show_in_shop(customizations.get_theme(name))
        ),
        "item_exists_sell": lambda details, name: name.lower() in details["author"].inventory["themes"],
    },
    "backgrounds": {
        "alias": ["backgrounds", "bgs", "bg", "background"],
        "actions": {
            "info_action": player_cmds.background_info,
            "list_action": shop_background_list,
            "buy_action": buy_sell_backgrounds.buy_item,
            "sell_action": buy_sell_backgrounds.sell_item,
        },
        "item_exists": lambda _, name: (name.lower() != "default" and name.lower() in customizations.backgrounds),
        "item_exists_sell": lambda details, name: name.lower() in details["author"].inventory["backgrounds"],
    },
    "banners": {
        "alias": ["banners", "banner"],
        "actions": {
            "info_action": player_cmds.banner_info,
            "list_action": shop_banner_list,
            "buy_action": buy_sell_banners.buy_item,
            "sell_action": buy_sell_banners.sell_item,
        },
        "item_exists": lambda details, name: (
            name.lower() != DEFAULT_BANNER
            and name.lower() in customizations.banners
            and customizations.get_banner(name).can_use_banner(details["author"])
        ),
        "item_exists_sell": lambda details, name: name.lower() in details["author"].inventory["banners"],
    },
    # "shields": {
    #     "alias": ["shields", "shield", "armors", "armor"],
    #     "actions": {
    #         "info_action": player_cmds.banner_info,
    #         "list_action": shop_banner_list,
    #         "buy_action": buy_sell_banners.buy_item,
    #         "sell_action": buy_sell_banners.sell_item,
    #     },
    #     "item_exists": lambda details, name: (
    #         name.lower() != DEFAULT_BANNER
    #         and name.lower() in customizations.banners
    #         and customizations.get_banner(name).can_use_banner(details["author"])
    #     ),
    #     "item_exists_sell": lambda details, name: name.lower() in details["author"].inventory["banners"],
    # },
}


def try_again(general_command):
    # Try again wrapper. If the department/item not found error is thrown.
    # This could be because they forgot the quotes. This is a simple
    # fix to that very common mistake.
    @wraps(general_command)
    async def wrapped_command(ctx, *args, **details):
        try:
            await general_command(ctx, *args, **details)
        except util.BattleBananaException as command_error:
            if command_error.message == DEPARTMENT_NOT_FOUND:
                # Try with just one arg (i.e the args being an item name)
                probable_item_name = " ".join((str(arg) for arg in args))
                await general_command(ctx, probable_item_name, **details)
            elif command_error.message == ITEM_NOT_FOUND and args[0].count(" ") >= 2:
                # A fix for a less common mistake. Missing quotes around
                # item name with spaces in it while setting a department too.
                args = args[0].split(" ", 1)
                await general_command(ctx, *args, **details)
            else:
                raise command_error

    return wrapped_command


@commands.command(args_pattern="S?M?")
@try_again
async def shop(ctx, *args, **details):
    """
    [CMD_KEY]shop department (page or name)

    A place to see all the backgrounds, banners, themes
    and weapons on sale.

    e.g. [CMD_KEY]shop weapons
    will show all weapons currenly in store.
    [CMD_KEY]shop item
    will show extra details about that item.
    If you want anything from the shop use the
    [CMD_KEY]buy command!
    """

    shop_embed = discord.Embed(type="rich", color=gconf.DUE_COLOUR)
    details["embed"] = shop_embed

    if len(args) == 0:
        # Greet
        greet = ":wave: **Welcome to the BattleBanana general store!**\n"
        department_available = "Please have a look in some of our splendiferous departments!\n"
        for department_info in departments.values():
            department_available += "``" + details["cmd_key"] + "shop " + department_info["alias"][0] + "``\n"
        shop_help = "For more info on the new shop do ``" + details["cmd_key"] + "help shop``"
        await util.reply(ctx, greet + department_available + shop_help)
        return

    # If 1 args could be department or name.
    # If two. Department then name.
    department = get_department_from_name(args[0])
    if department is not None:
        list_action = department["actions"]["list_action"]
        if len(args) == 1:
            await util.reply(ctx, embed=list_action(0, **details))
        else:
            if isinstance(args[1], int):
                await util.reply(ctx, embed=list_action(args[1] - 1, **details))
            else:
                # Use item_action since it will do the check if item exists
                await item_action(args[1], "info_action", department=department, **details)
    elif len(args) == 1:
        await item_action(args[0].lower(), "info_action", **details)
    else:
        raise util.BattleBananaException(ctx.channel, DEPARTMENT_NOT_FOUND)


@commands.command(args_pattern="SS?")
@try_again
async def buy(ctx, *args, **details):
    """
    [CMD_KEY]buy item name
    """

    if len(args) == 1:
        await item_action(args[0].lower(), "buy_action", **details)
    else:
        department = get_department_from_name(args[0])
        if department is not None:
            await department["actions"]["buy_action"](args[1].lower(), **details)
        else:
            raise util.BattleBananaException(ctx.channel, DEPARTMENT_NOT_FOUND)


@commands.command(args_pattern="SS?")
@try_again
async def sell(ctx, *args, **details):
    """
    [CMD_KEY]sell item name
    """
    error = "You own multiple items with the same name!"

    if len(args) == 1:
        await item_action(args[0].lower(), "sell_action", **details, exists_check="item_exists_sell", error=error)
    else:
        department = get_department_from_name(args[0])
        if department is not None:
            await department["actions"]["sell_action"](args[1].lower(), **details)
        else:
            raise util.BattleBananaException(ctx.channel, DEPARTMENT_NOT_FOUND)
