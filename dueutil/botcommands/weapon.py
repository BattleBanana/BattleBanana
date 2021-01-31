import discord

import generalconfig as gconf
from ..game import players
from ..permissions import Permission
from ..game import battles, weapons, stats, awards, translations
from ..game.helpers import imagehelper, misc
from .. import commands, util


@commands.command(args_pattern="M?", aliases=["mw"])
async def myweapons(ctx, *args, **details):
    """weapon:myweapons:HELP"""

    player = details["author"]
    server_key = details["cmd_key"]
    player_weapons = player.get_owned_weapons()
    page = 1
    if len(args) == 1:
        page = args[0]

    if type(page) is int:
        weapon_store = weapons_page(player_weapons, page-1,
                                    title=player.get_name_possession_clean() + " Weapons", price_divisor=4/3,
                                    empty_list="")
        if len(player_weapons) == 0:
            weapon_store.add_field(name=translations.translate(ctx, "weapon:myweapons:NoWepTitle"),
                                    value=translations.translate(ctx, "weapon:myweapons:NoWepDes"))
        weapon_store.description = translations.translate(ctx, "weapon:myweapons:EquiptedWeps") + str(player.weapon)
        weapon_store.set_footer(text=translations.translate(ctx, "weapon:myweapons:Footer"))
        await util.reply(ctx, embed=weapon_store)
    else:
        weapon_name = page
        if player.equipped["weapon"] != weapons.NO_WEAPON_ID:
            player_weapons.append(player.weapon)
        weapon = next((weapon for weapon in player_weapons if weapon.name.lower() == weapon_name.lower()), None)
        if weapon is not None:
            embed = discord.Embed(type="rich", color=gconf.DUE_COLOUR)
            info = weapon_info(**details, weapon=weapon, price_divisor=4 / 3, embed=embed)
            await util.reply(ctx, embed=info)
        else:
            raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "weapon:myweapons:NoWepName"))


@commands.command(args_pattern="S?", aliases=["uq", "uneq"])
async def unequip(ctx, _=None, **details):
    """weapon:unequip:Help"""

    player = details["author"]
    weapon = player.weapon
    if weapon.w_id == weapons.NO_WEAPON_ID:
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "weapon:unequip:NothingEquip"))
    if len(player.inventory["weapons"]) >= 6:
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "weapon:unequip:NoRoom"))
    if player.owns_weapon(weapon.name):
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "weapon:unequip:AlreadyStored"))

    player.store_weapon(weapon)
    player.weapon = weapons.NO_WEAPON_ID
    player.save()
    await util.reply(ctx, ":white_check_mark: **" + weapon.name_clean + "**"+translations.translate(ctx, "weapon:unequip:UnEquip"))


@commands.command(args_pattern='S', aliases=["eq"])
async def equip(ctx, weapon_name, **details):
    """weapon:equip:Help"""

    player = details["author"]
    current_weapon = player.weapon
    weapon_name = weapon_name.lower()

    weapon = player.get_weapon(weapon_name)
    if weapon is None:
        if weapon_name != current_weapon.name.lower():
            raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "weapon:equip:NotStored"))
        await util.reply(ctx, translations.translate(ctx, "weapon:equip:AlreadyEquip"))
        return

    player.discard_stored_weapon(weapon)
    if player.owns_weapon(current_weapon.name):
        player.store_weapon(weapon)
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "weapon:equip:SameName"))

    if current_weapon.w_id != weapons.NO_WEAPON_ID:
        player.store_weapon(current_weapon)

    player.weapon = weapon
    player.save()

    await util.reply(ctx, ":white_check_mark: **" + weapon.name_clean + "** "+translations.translate(ctx, "weapon:equip:Equipped"))


@misc.paginator
def weapons_page(weapons_embed, weapon, **extras):
    price_divisor = extras.get('price_divisor', 1)
    weapons_embed.add_field(name=str(weapon),
                            value='``' + util.format_number(weapon.price // price_divisor, full_precision=True,
                                                            money=True) + '``')


@commands.command(args_pattern='PP?', aliases=["bt"])
@commands.imagecommand()
async def battle(ctx, *args, **details):
    """weapon:battle:Help"""
    # TODO: Handle draws
    player = details["author"]
    if len(args) == 2 and args[0] == args[1] or len(args) == 1 and player == args[0]:
        # TODO Check if args are the author or random player
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "weapon:battle:BattleAuthor"))
    if len(args) == 2:
        player_one = args[0]
        player_two = args[1]
    else:
        player_one = player
        player_two = args[0]

    battle_log = battles.get_battle_log(ctx, player_one=player_one, player_two=player_two)

    await imagehelper.battle_screen(ctx, player_one, player_two)
    await util.say(ctx.channel, embed=battle_log.embed)
    if battle_log.winner is None:
        # Both players get the draw battle award
        awards.give_award(ctx.channel, player_one, "InconceivableBattle")
        awards.give_award(ctx.channel, player_two, "InconceivableBattle")
    await battles.give_awards_for_battle(ctx.channel, battle_log)


@commands.command(args_pattern='PC', aliases=("wager", "wb"))
async def wagerbattle(ctx, receiver, money, **details):
    """weapon:wagerbattle:Help"""
    sender = details["author"]

    if sender == receiver:
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "weapon:wagerbattle:AgainstAuthor"))

    if sender.money - money < 0:
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "weapon:wagerbattle:CantAfford"))

    if len(receiver.received_wagers) >= gconf.THING_AMOUNT_CAP:
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "weapon:wagerbattle:CantAfford", receiver.get_name_possession_clean()))

    battles.BattleRequest(sender, receiver, money)

    await util.reply(ctx, ("**" + sender.name_clean + "** wagers **" + receiver.name_clean + "** ``"
                                 + util.format_number(money, full_precision=True,
                                                      money=True) + "``"+translations.translate(ctx, "weapon:wagerbattle:Message")))


@commands.command(args_pattern='C?', aliases=["vw"])
async def mywagers(ctx, page=1, **details):
    """weapon:mywagers:Help"""

    @misc.paginator
    def wager_page(wagers_embed, current_wager, **extras):
        sender = players.find_player(current_wager.sender_id)
        if not sender: 
            return
        wagers_embed.add_field(name="%d. Request from %s" % (extras["index"]+1, sender.name_clean),
                               value="<@%s> ``%s``" % (sender.id, util.format_money(current_wager.wager_amount)))

    player = details["author"]
    wager_list_embed = wager_page(player.received_wagers, page-1,
                                  title=player.get_name_possession_clean() + " Received Wagers",
                                  footer_more="But wait there's more! Do %smywagers %d" % (details["cmd_key"], page+1),
                                  empty_list="")

    if len(player.received_wagers) != 0:
        wager_list_embed.add_field(name="Actions",
                                   value=("Do ``{0}acceptwager (number)`` to accept a wager \nor ``"
                                          + "{0}declinewager (number)`` to decline").format(details["cmd_key"]),
                                   inline=False)
    else:
        wager_list_embed.add_field(name="No wagers received!",
                                   value="Wager requests you get from other players will appear here.")

    await util.reply(ctx, embed=wager_list_embed)


@commands.command(args_pattern='C', aliases=["aw"])
@commands.imagecommand()
async def acceptwager(ctx, wager_index, **details):
    """weapon:acceptwager:Help"""
    # TODO: Handle draws
    player = details["author"]
    wager_index -= 1
    if wager_index >= len(player.received_wagers):
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "weapon:acceptwager:ReqNotFound"))
    if player.money - player.received_wagers[wager_index].wager_amount < 0:
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "weapon:acceptwager:CantAfford"))

    wager = player.received_wagers.pop(wager_index)
    sender = players.find_player(wager.sender_id)
    if not sender:
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "weapon:acceptwager:NoLongerPlayer"))
    battle_log = battles.get_battle_log(ctx, player_one=player, player_two=sender)
    battle_embed = battle_log.embed
    winner = battle_log.winner
    loser = battle_log.loser
    wager_amount_str = util.format_number(wager.wager_amount, full_precision=True, money=True)
    total_transferred = wager.wager_amount
    if winner == sender:
        wager_results = translations.translate(ctx, "weapon:acceptwager:Lose", player.name_clean,sender.name_clean, wager_amount_str)
        player.money -= wager.wager_amount
        sender.money += wager.wager_amount
        sender.wagers_won += 1
    elif winner == player:
        player.wagers_won += 1
        if sender.money - wager.wager_amount >= 0:
            payback = ("**" + sender.name_clean + "**"+translations.translate(ctx, "other:singleword:Paid")+"**" + player.name_clean + "** ``"
                       + wager_amount_str + "``")
            player.money += wager.wager_amount
            sender.money -= wager.wager_amount
        else:
            weapons_sold = 0
            if sender.equipped["weapon"] != weapons.NO_WEAPON_ID:
                weapons_sold += 1
                sender.money += sender.weapon.get_summary().price // (4 / 3)
                sender.weapon = weapons.NO_WEAPON_ID
            if sender.money - wager.wager_amount < 0:
                for weapon in sender.get_owned_weapons():
                    weapon_price = weapon.get_summary().price
                    sender.discard_stored_weapon(weapon)
                    sender.money += weapon_price // (4 / 3)
                    weapons_sold += 1
                    if sender.money - wager.wager_amount >= 0:
                        break
            amount_not_paid = max(0, wager.wager_amount - sender.money)
            amount_paid = wager.wager_amount - amount_not_paid
            amount_paid_str = util.format_number(amount_paid, full_precision=True, money=True)

            if weapons_sold == 0:
                payback = translations.translate(ctx, "weapon:acceptwager:CantAffordNoWep", sender.name_clean, amount_paid_str)
            else:
                payback = translations.translate(ctx, "weapon:acceptwager:CantAffordWep",sender.name_clean, str(weapons_sold))
                if amount_paid != wager.wager_amount:
                    payback += translations.translate(ctx, "weapon:acceptwager:CantAfford3")
                else:
                    payback += translations.translate(ctx, "weapon:acceptwager:CantAfford4")
            sender.money -= amount_paid
            player.money += amount_paid
            total_transferred = amount_paid
        wager_results = translations.translate(ctx,"weapon:acceptwager:Win", player.name_clean, sender.name_clean, payback)
    else:
        wager_results = translations.translate(ctx, "weapon:acceptwager:Draw")
    stats.increment_stat(stats.Stat.MONEY_TRANSFERRED, total_transferred)
    battle_embed.add_field(name="Wager results", value=wager_results, inline=False)
    await imagehelper.battle_screen(ctx, player, sender)
    await util.reply(ctx, embed=battle_embed)
    if winner is not None:
        await awards.give_award(ctx.channel, winner, "YouWin", "Win a wager")
        await awards.give_award(ctx.channel, loser, "YouLose", "Lose a wager!")
        if winner.wagers_won == 2500:
            await awards.give_award(ctx.channel, winner, "2500Wagers")
    else:
        await  awards.give_award(ctx.channel, player, "InconceivableWager")
        await  awards.give_award(ctx.channel, sender, "InconceivableWager")
    await battles.give_awards_for_battle(ctx.channel, battle_log)
    sender.save()
    player.save()


@commands.command(args_pattern='C', aliases=["dw"])
async def declinewager(ctx, wager_index, **details):
    """weapon:declinewager:Help"""

    player = details["author"]
    wager_index -= 1
    if wager_index < len(player.received_wagers):
        wager = player.received_wagers[wager_index]
        del player.received_wagers[wager_index]
        player.save()
        sender = players.find_player(wager.sender_id)
        await translations.say(ctx, "weapon:declinewager:Success", player.name_clean, sender.name_clean)

    else:
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "weapon:declinewager:NotFound"))


@commands.command(permission=Permission.SERVER_ADMIN, args_pattern='SSC%B?S?S?')
async def createweapon(ctx, name, hit_message, damage, accy, ranged=False, icon='🔫', image_url=None, **_):
    """weapon:createweapon:Help"""

    if len(weapons.get_weapons_for_server(ctx.guild)) >= gconf.THING_AMOUNT_CAP:
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "weapon:createweapon:Capped", gconf.THING_AMOUNT_CAP))

    extras = {"melee": not ranged, "icon": icon}
    if image_url is not None:
        extras["image_url"] = image_url

    weapon = weapons.Weapon(name, hit_message, damage, accy, **extras, ctx=ctx)
    await translations.say(ctx, "weapon:createweapon:Success", weapon.icon, weapon.name_clean, util.format_number(weapon.price, money=True))
    if "image_url" in extras:
        await imagehelper.warn_on_invalid_image(ctx.channel, url=extras["image_url"])


@commands.command(permission=Permission.SERVER_ADMIN, args_pattern="SS*")
@commands.extras.dict_command(optional={"message/hit/hit_message": "S", "ranged": "B",
                                        "icon": "S", "image": "S"})
async def editweapon(ctx, weapon_name, updates, **_):
    """weapon:editweapon:Help"""

    weapon = weapons.get_weapon_for_server(ctx.guild.id, weapon_name)
    if weapon is None:
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "other:common:WepNotFound"))
    if weapon.is_stock():
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "weapon:editweapon:Stock"))

    new_image_url = None
    for weapon_property, value in updates.items():
        if weapon_property == "icon":
            if util.is_discord_emoji(ctx.guild, value):
                weapon.icon = value
            else:
                updates[weapon_property] = translations.translate(ctx, "weapon:editweapon:NotEmoji")
        elif weapon_property == "ranged":
            weapon.melee = not value
            updates[weapon_property] = str(value).lower()
        else:
            updates[weapon_property] = util.ultra_escape_string(value)
            if weapon_property == "image":
                new_image_url = weapon.image_url = value
            else:
                if weapon.acceptable_string(value, 32):
                    weapon.hit_message = value
                    updates[weapon_property] = '"%s"' % updates[weapon_property]
                else:
                    updates[weapon_property] = translations.translate(ctx, "weapon:editweapon:Over32")

    if len(updates) == 0:
        await translations.say(ctx, "weapon:editweapon:NoChanges")
    else:
        weapon.save()
        result = weapon.icon+" **"+weapon.name_clean+"** "+translations.translate(ctx, "other:singleword:Updates")+"!\n"
        for weapon_property, update_result in updates.items():
            result += "``%s`` → %s\n" % (weapon_property, update_result)
        await util.reply(ctx, result)
        if new_image_url is not None:
            await imagehelper.warn_on_invalid_image(ctx.channel, new_image_url)


@commands.command(permission=Permission.SERVER_ADMIN, args_pattern='S')
async def removeweapon(ctx, weapon_name, **_):
    """weapon:removeweapon:Help"""

    weapon_name = weapon_name.lower()
    weapon = weapons.get_weapon_for_server(ctx.guild.id, weapon_name)
    if weapon is None or weapon.id == weapons.NO_WEAPON_ID:
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "other:common:WepNotFound"))
    if weapon.id != weapons.NO_WEAPON_ID and weapons.stock_weapon(weapon_name) != weapons.NO_WEAPON_ID:
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "weapon:removeweapon:Stock"))
    weapons.remove_weapon_from_shop(ctx.guild, weapon_name)
    await translations.say(ctx, "weapon:removeweapon:Success", weapon_name)


@commands.command(permission=Permission.REAL_SERVER_ADMIN, args_pattern="S?")
@commands.require_cnf(warning="weapon:resetweapons:CNF")
async def resetweapons(ctx, **_):
    """weapon:resetweapons:Help"""

    weapons_deleted = weapons.remove_all_weapons(ctx.guild)
    if weapons_deleted > 0:
        await translations.say(ctx, "weapon:resetweapons:Success", (weapons_deleted, util.s_suffix("weapon", weapons_deleted)))
    else:
        await translations.say(ctx, "weapon:resetweapons:NoWeapons")


# Part of the shop buy command
async def buy_weapon(ctx, weapon_name, **details):
    customer = details["author"]
    weapon = weapons.get_weapon_for_server(details["server_id"], weapon_name)
    channel = details["channel"]

    if weapon is None or weapon_name == "none":
        raise util.BattleBananaException(channel, "Weapon not found")
    if customer.money - weapon.price < 0:
        await util.say(channel, ":anger: You can't afford that weapon.")
    elif weapon.price > customer.item_value_limit:
        await util.say(channel, (":baby: Awwww. I can't sell you that.\n"
                                 + "You can use weapons with a value up to **"
                                 + util.format_number(customer.item_value_limit, money=True,
                                                      full_precision=True) + "**"))
    elif customer.equipped["weapon"] != weapons.NO_WEAPON_ID:
        if len(customer.inventory["weapons"]) < weapons.MAX_STORED_WEAPONS:
            if weapon.w_id not in customer.inventory["weapons"] and not(weapon.w_id == customer.equipped["weapon"]):
                customer.store_weapon(weapon)
                customer.money -= weapon.price
                await util.say(channel, ("**" + customer.name_clean + "** bought a **" + weapon.name_clean + "** for "
                                         + util.format_number(weapon.price, money=True, full_precision=True)
                                         + "\n:warning: You have not equipped this weapon! Do **"
                                         + details["cmd_key"] + "equip "
                                         + weapon.name_clean.lower() + "** to equip this weapon."))
            else:
                raise util.BattleBananaException(channel,
                                            "Cannot store new weapon! You already have a weapon with the same name!")
        else:
            raise util.BattleBananaException(channel, "No free weapon slots!")
    else:
        customer.weapon = weapon
        customer.money -= weapon.price
        await util.say(channel, ("**" + customer.name_clean + "** bought a **"
                                 + weapon.name_clean + "** for " + util.format_number(weapon.price, money=True,
                                                                                      full_precision=True)))
        await awards.give_award(channel, customer, "Spender", "Licence to kill!")
    customer.save()


async def sell_weapon(ctx, weapon_name, **details):
    player = details["author"]
    channel = details["channel"]

    price_divisor = 4 / 3
    player_weapon = player.weapon
    if player_weapon != weapons.NO_WEAPON and player_weapon.name.lower() == weapon_name:
        weapon_to_sell = player.weapon
        player.weapon = weapons.NO_WEAPON_ID
    else:
        weapon_to_sell = next((weapon for weapon in player.get_owned_weapons() if weapon.name.lower() == weapon_name),
                              None)
        if weapon_to_sell is None:
            raise util.BattleBananaException(channel, translations.translate(ctx, "other:misc:NotFound"))
        player.discard_stored_weapon(weapon_to_sell)

    sell_price = weapon_to_sell.price // price_divisor
    player.money += sell_price
    await util.say(channel, ("**" + player.name_clean + "**"+translations.translate(ctx, "other:misc:Sold")+"**" + weapon_to_sell.name_clean
                             + "**"+translations.translate(ctx, "other:singleword:For")+" ``" + util.format_number(sell_price, money=True, full_precision=True) + "``"))
    player.save()


def weapon_info(ctx, weapon_name=None, **details):
    embed = details["embed"]
    price_divisor = details.get('price_divisor', 1)
    weapon = details.get('weapon')
    if weapon is None:
        weapon = weapons.get_weapon_for_server(details["server_id"], weapon_name)
        if weapon is None:
            raise util.BattleBananaException(details["channel"], "Weapon not found")
    embed.title = weapon.icon + ' | ' + weapon.name_clean
    embed.set_thumbnail(url=weapon.image_url)
    embed.add_field(name='Damage', value=util.format_number(weapon.damage))
    embed.add_field(name='Accuracy', value=util.format_number(weapon.accy * 100) + '%')
    embed.add_field(name='Price',
                    value=util.format_number(weapon.price // price_divisor, money=True, full_precision=True))
    embed.add_field(name="Hit Message", value=weapon.hit_message)
    embed.set_footer(text='Image supplied by weapon creator.')
    return embed
