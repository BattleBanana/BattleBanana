import discord
import random
import time

import dueutil.game.awards as game_awards
import generalconfig as gconf
from ..game import players, customizations
from ..game import stats, game, gamerules, quests, translations
from ..game.helpers import misc, playersabstract, imagehelper
from ..game.configs import dueserverconfig
from .. import commands, util, dbconn, permissions
from ..permissions import Permission
from ..game import emojis as e

DAILY_AMOUNT = 50
TRAIN_RANGE = (0.1, 0.3)

@commands.command(args_pattern=None)
@commands.ratelimit(cooldown=86400, error="You can't collect your daily reward again for **[COOLDOWN]**!", save=True)
async def daily(ctx, **details):
    """
    [CMD_KEY]daily

    ¤50 * your level! Your daily pocket money!

    You can use this command once every 24 hours!
    """
    player = details["author"]
    responses = game.getResponses()

    BALANCED_AMOUNT = DAILY_AMOUNT * player.level * player.prestige_multiplicator()
    
    player.money += BALANCED_AMOUNT
    player.save()
    await util.say(ctx.channel, e.BBT + f' {random.choice(responses).format(user=f"**{player}**", daily=f"¤{BALANCED_AMOUNT}")}')

@commands.command(args_pattern=None)
@commands.ratelimit(cooldown=21600, error="player:train:RATELIMIT", save=True)
#cooldown was 21600
#set to 0 for testing purposes
async def train(ctx, **details):
    """player:train:HELP"""

    player = details["author"]
    maxstats = 100 * player.prestige_multiplicator()

    attack_increase = random.uniform(*TRAIN_RANGE) * player.level * player.prestige_multiplicator()
    strg_increase = random.uniform(*TRAIN_RANGE) * player.level * player.prestige_multiplicator()
    accy_increase = random.uniform(*TRAIN_RANGE) * player.level * player.prestige_multiplicator()

    player.progress(attack_increase, strg_increase, accy_increase,
                    max_exp=maxstats, max_attr=maxstats)
    progress_message = players.STAT_GAIN_FORMAT % (attack_increase, strg_increase, accy_increase)

    train_embed = discord.Embed(title=translations.getLocale(ctx, player, "player:train:TITLE"), description=translations.getLocale(ctx, player, "player:train:DESCRIPTION"), type="rich", color=gconf.DUE_COLOUR)
    train_embed.add_field(name=translations.getLocale(ctx, player, "player:train:FIELDNAME"), value=progress_message, inline=True)
    train_embed.set_footer(text=translations.getLocale(ctx, player, "player:train:FOOTER"))

    await game.check_for_level_up(ctx, player)
    player.save()
    await translations.say(ctx, "player:train:COMPLETE", player, embed=train_embed)

@commands.command(args_pattern=None)
@commands.ratelimit(cooldown=604800, error="player:weekly:RATELIMIT", save=True)
async def weekly(ctx, **details):
    """player:weekly:HELP"""
    player = details["author"]
    channel = ctx.channel

    if quests.has_quests(channel):
        player.last_quest = time.time()
        quest = quests.get_random_quest_in_channel(channel)
        new_quest = await quests.ActiveQuest.create(quest.q_id, player)
        stats.increment_stat(stats.Stat.QUESTS_GIVEN)
        if dueserverconfig.mute_level(ctx.channel) < 0:
            await imagehelper.new_quest_screen(channel, new_quest, player)
        else:
            util.logger.info("Won't send new quest image - channel blocked.")

@commands.command(args_pattern=None)
async def mylimit(ctx, **details):
    """player:mylimit:HELP"""

    player = details["author"]
    await translations.say(ctx, "player:mylimit:RESPONSE", util.format_number(player.item_value_limit, money=True, full_precision=True))


@commands.command(args_pattern="S?")
async def battlename(ctx, name="", **details):
    """player:battlename:HELP"""

    player = details["author"]
    if name != "":
        name_len_range = players.Player.NAME_LENGTH_RANGE
        if len(name) not in name_len_range:
            raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "player:battlename:ERROR", min(name_len_range), max(name_len_range)))
        player.name = util.filter_string(name)
    else:
        player.name = details["author_name"]
    player.save()
    await translations.say(ctx, "player:battlename:RESPONSE", player.name_clean)


@commands.command(args_pattern=None, aliases=["mi"])
@commands.imagecommand()
async def myinfo(ctx, **details):
    """player:myinfo:HELP"""

    await imagehelper.stats_screen(ctx.channel, details["author"])


def player_profile_url(player_id):
    private_record = dbconn.conn()["public_profiles"].find_one({"_id": player_id})

    if private_record is None or private_record["private"]:
        return None
    return "https://battlebanana.xyz/player/id/%s" % player_id


@commands.command(args_pattern=None)
async def myprofile(ctx, **details):
    """player:myprofile:HELP"""

    profile_url = player_profile_url(details["author"].id)

    if profile_url is None:
        await translations.say(ctx, "player:myprofile:LOCKED")
    else:
        await translations.say(ctx, "player:myprofile:SUCCESS", profile_url)


@commands.command(args_pattern='P')
async def profile(ctx, player, **_):
    """player:profile:HELP"""

    profile_url = player_profile_url(player.id)

    if profile_url is None:
        await translations.say(ctx, "player:profile:LOCKED", player.get_name_possession_clean())
    else:
        await translations.say(ctx, "player:profile:SUCCESS", player.get_name_possession_clean(), profile_url)


@commands.command(args_pattern='P', aliases=["in"])
@commands.imagecommand()
async def info(ctx, player, **_):
    """player:info:HELP"""

    await imagehelper.stats_screen(ctx.channel, player)


async def show_awards(ctx, player, page=0):
    # Always show page 1 (0)
    if page != 0 and page * 5 >= len(player.awards):
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "player:info:ERROR"))

    await imagehelper.awards_screen(ctx.channel, player, page,
                                    is_player_sender=ctx.author.id == player.id)


@commands.command(args_pattern=None, aliases=["hmw"])
async def hidemyweapon(ctx, **details):
    """
    
    """
    player = details["author"]

    player.weapon_hidden = not player.weapon_hidden
    player.save()

    await translations.say(ctx, "player:hidemyweapon:NOWHIDDEN" if player.weapon_hidden else "player:hidemyweapon:NOTHIDDEN")


@commands.command(args_pattern='C?')
@commands.imagecommand()
async def myawards(ctx, page=1, **details):
    """player:myawards:HELP"""

    await show_awards(ctx, details["author"], page - 1)


@commands.command(args_pattern='PC?')
@commands.imagecommand()
async def awards(ctx, player, page=1, **_):
    """player:awards:HELP"""

    await show_awards(ctx, player, page - 1)

@commands.command(args_pattern="S?")
@commands.require_cnf(warning="This will **__permanently__** reset your user!")
async def resetme(ctx, cnf="", **details):
   """
   
   """

   player = details["author"]
   player.reset(ctx.author)
   await translations.say(ctx, "player:resetme:SUCCESS")


@commands.command(permission=Permission.DISCORD_USER, args_pattern=None, aliases=["start"])
async def createaccount(ctx, **details):
    """player:createaccount:HELP"""

    player = details["author"]

    if player:
        return await translations.say(ctx, "player:createaccount:ALREADYPLAYER")

    players.Player(ctx.author)
    stats.increment_stat(stats.Stat.NEW_PLAYERS_JOINED)
    await translations.say(ctx, "player:createaccount:NEWPLAYER")


@commands.command(args_pattern="S?")
@commands.require_cnf(warning="This will **__permanently__** delete your account!")
async def deleteme(ctx, cnf="", **details):
    """player:deleteme:HELP"""
    
    player = details["author"]

    dbconn.delete_player(player)
    players.players.pop(ctx.author.id)
    
    await translations.say(ctx, "player:deleteme:SUCCESS")

@commands.command(args_pattern='PCS?', aliases=["sq"])
async def sendquest(ctx, receiver, quest_index, message="", **details):
    """player:sendquest:HELP"""

    plr = details["author"]
    quest_index -= 1

    if receiver.id == plr.id:
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "player:sendquest:SAMEUSER"))
    if quest_index >= len(plr.quests):
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "player:sendquest:QUESTNOTFOUND"))
    plr_quest = plr.quests[quest_index]
    if plr_quest.level > (receiver.level + 10):
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "player:sendquest:TOOSTRONG", str(receiver.level + 10)))

    quest_name = plr_quest.name
    quest_level = str(plr_quest.level)

    receiver.quests.append(plr_quest)
    del plr.quests[quest_index]

    rec_quest = receiver.quests[-1]
    rec_quest.quester_id = receiver.id
    rec_quest.quester = receiver

    receiver.save()
    plr.save()
    
    transaction_log = discord.Embed(title=e.QUESTER + translations.translate(ctx, "player:sendquest:EMBEDTITLE"), type="rich",
                                    color=gconf.DUE_COLOUR)
    transaction_log.add_field(name=translations.translate(ctx, "player:sendquest:EMBEDSENDER"), value=plr.name_clean)
    transaction_log.add_field(name=translations.translate(ctx, "player:sendquest:EMBEDRECIPIENT"), value=receiver.name_clean)
    transaction_log.add_field(name=translations.translate(ctx, "player:sendquest:EMBEDTRANS"), value=quest_name + ", level " + quest_level, inline=False)
    if message != "":
        transaction_log.add_field(name=translations.translate(ctx, "player:sendquest:EMEDNOTE"), value=message, inline=False)
    transaction_log.set_footer(text=translations.translate(ctx, "player:sendquest:EMBEDRECEIPT"))
    util.logger.info("%s (%s) sent %s to %s (%s)", plr.name, plr.id, quest_name + ", level " + quest_level, receiver.name, receiver.id)

    await util.say(ctx.channel, embed=transaction_log)


@commands.command(args_pattern='PP?')
async def compare(ctx, player1, player2=None, **details):
    """player:compare:HELP"""
    
    plr = details["author"]
    if player2 is None and player1 == plr:
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "player:compare:COMPAREYOU"))
    if player1 == player2:
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "player:compare:SAMEPLAYER"))
    
    compare_Embed = discord.Embed()

    prestige = translations.translate(ctx, "player:compare:PRESTIGE")
    level = translations.translate(ctx, "player:compare:LEVEL")
    health = translations.translate(ctx, "player:compare:HEALTH")
    attack = translations.translate(ctx, "player:compare:ATTACK")
    strength = translations.translate(ctx, "player:compare:STRENGTH")
    accuracy = translations.translate(ctx, "player:compare:ACCURACY")

    if player2 is None:
        player2 = player1
        player1 = plr
    compare_Embed.title = "Comparing **%s** with **%s**!" % (player1.name_clean, player2.name_clean)
    compare_Embed.add_field(
        name=player1.name_clean,
        value=(prestige+": %s\n"+level+": %s\n"+health+": %.2f\n"+attack+": %.2f\n"+strength+": %.2f\n"+accuracy+": %.2f" % (player1.prestige_level, player1.level, player1.hp * player1.strg, player1.attack, player1.strg, player1.accy)), 
        inline=True
    )
    compare_Embed.add_field(
        name=player2.name_clean,
        value=(prestige+": %s\n"+level+": %s\n"+health+": %.2f\n"+attack+": %.2f\n"+strength+": %.2f\n"+accuracy+": %.2f" % (player2.prestige_level, player2.level, player2.hp * player2.strg, player2.attack, player2.strg, player2.accy)), 
        inline=True
    )

    await util.say(ctx.channel, embed=compare_Embed)

@commands.command(args_pattern='PCS?', aliases=["sc"])
async def sendcash(ctx, receiver, transaction_amount, message="", **details):
    """player:sendcash:HELP"""

    sender = details["author"]
    amount_string = util.format_number(transaction_amount, money=True, full_precision=True)

    if receiver.id == sender.id:
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "player:sendcash:SAMEPLAYER"))

    if sender.money - transaction_amount < 0:
        if sender.money > 0:
            await translations.say(ctx, sender, "player:sendcash:HIGHER", amount_string, util.format_number(sender.money, money=True, full_precision=True))
        else:
            await translations.say(ctx, sender, "player:sendcash:BROKE")
        return

    max_receive = int(receiver.item_value_limit * 10)
    if transaction_amount > max_receive:
        await translations.say(ctx, sender, "player:sendcash:CANTAFFORD", amount_string, receiver.name_clean, receiver.name_clean, util.format_number(max_receive, money=True, full_precision=True))
        return

    sender.money -= transaction_amount
    receiver.money += transaction_amount

    sender.save()
    receiver.save()

    stats.increment_stat(stats.Stat.MONEY_TRANSFERRED, transaction_amount)
    if transaction_amount >= 50:
        await game_awards.give_award(ctx.channel, sender, "SugarDaddy", "Sugar daddy!")

    transaction_log = discord.Embed(title=e.BBT_WITH_WINGS + translations.translate(ctx, "player:sendcash:TITLE"), type="rich",
                                    color=gconf.DUE_COLOUR)
    transaction_log.add_field(name=translations.translate(ctx, "player:sendcash:SENDER"), value=sender.name_clean)
    transaction_log.add_field(name=translations.translate(ctx, "player:sendcash:RECIPIENT"), value=receiver.name_clean)
    transaction_log.add_field(name=translations.translate(ctx, "player:sendcash:AMOUNT"), value=amount_string, inline=False)
    if message != "":
        transaction_log.add_field(name=translations.translate(ctx, "player:sendcash:NOTE"), value=message, inline=False)
    transaction_log.set_footer(text=translations.translate(ctx, "player:sendcash:FOOTER"))
    util.logger.info("%s (%s) sent %s to %s (%s)", sender.name, sender.id, amount_string, receiver.name, receiver.id)

    await util.say(ctx.channel, embed=transaction_log)

@commands.command(args_pattern="S?")
@commands.require_cnf(warning="This action cannot be reverted, are you sure you want to prestige?")
async def prestige(ctx, cnf="", **details):
    """player:prestige:HELP"""

    user = details["author"]
    prestige_level = gamerules.get_level_for_prestige(user.prestige_level)
    req_money = gamerules.get_money_for_prestige(user.prestige_level)

    if user.level < prestige_level:
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "player:prestige:LOWLEVEL", prestige_level))
    if user.money < req_money:
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "player:prestige:CANTAFFORD", util.format_number_precise(req_money), e.BBT))

    user.money -= req_money
    user.prestige()

    if prestige_level > 0:
        await game.awards.give_award(ctx.channel, user, 'Prestige')
    await translations.say(ctx, "player:pretige:SUCCESS", user.presitge_level)

@commands.command(args_pattern="P?", aliases=["mp", "showprestige", "sp"])
async def myprestige(ctx, player=None, **details):
    """player:myprestige:HELP"""

    if player is None:
        player = details["author"]
    prestige_level = gamerules.get_level_for_prestige(player.prestige_level)
    req_money = gamerules.get_money_for_prestige(player.prestige_level)

    #this is painful to read
    message = "%s prestige **%s**! " % ("**You** are" if player == details["author"] else "**" + player.name + "** is", player.prestige_level)
    message += "**%s** %s & %s" % ("You" if player == details["author"] else player.name, ("satisfy the level requirement" if prestige_level <= player.level else "need **%s** additional level(s)" % (prestige_level - player.level)),
                                    ("satisfy the money requirement" if req_money <= player.money else "need **%s%s** to afford the next prestige." 
                                    % (util.format_number_precise(req_money - player.money), e.BBT)))
    
    await util.say(ctx.channel, message)

@commands.command(hidden=True, args_pattern=None)
async def benfont(ctx, **details):
    """player:benfont:HELP"""

    player = details["author"]
    player.benfont = not player.benfont
    player.save()
    if player.benfont:
        await ctx.channel.send(discord.File('assets/images/nod.gif'))
        await game_awards.give_award(ctx.channel, player, "BenFont", "ONE TRUE *type* FONT")

"""
WARNING: Setter & my commands use decorators to be lazy

Setters just return the item type & inventory slot. (could be done without
the decorators but setters must be fucntions anyway to be commands)

This is part of my quest in finding lazy ways to do things I cba.
"""

# Think about clean up & reuse
@commands.command(args_pattern='M?')
@playersabstract.item_preview
def mythemes(player):
    """player:mythemes:HELP"""

    return {"thing_type": "theme",
            "thing_list": list(player.get_owned_themes().values()),
            "thing_lister": theme_page,
            "my_command": "mythemes",
            "set_command": "settheme",
            "thing_info": theme_info,
            "thing_getter": customizations.get_theme}


@commands.command(args_pattern='S')
@playersabstract.item_setter
def settheme():
    """player:settheme:HELP"""

    return {"thing_type": "theme", "thing_inventory_slot": "themes"}


@commands.command(args_pattern='M?', aliases=("mybackgrounds", "backgrounds"))
@playersabstract.item_preview
def mybgs(player):
    """player:mybgs:HELP"""

    return {"thing_type": "background",
            "thing_list": list(player.get_owned_backgrounds().values()),
            "thing_lister": background_page,
            "my_command": "mybgs",
            "set_command": "setbg",
            "thing_info": background_info,
            "thing_getter": customizations.get_background}


@commands.command(args_pattern='S', aliases=["setbackground"])
@playersabstract.item_setter
def setbg():
    """player:setbg:HELP"""

    return {"thing_type": "background", "thing_inventory_slot": "backgrounds"}


@commands.command(args_pattern='M?')
@playersabstract.item_preview
def mybanners(player):
    """player:mybanners:HELP"""
    return {"thing_type": "banner",
            "thing_list": list(player.get_owned_banners().values()),
            "thing_lister": banner_page,
            "my_command": "mybanners",
            "set_command": "setbanner",
            "thing_info": banner_info,
            "thing_getter": customizations.get_banner}


@commands.command(args_pattern='S')
@playersabstract.item_setter
def setbanner():
    """player:setbanners:HELP"""

    return {"thing_type": "banner", "thing_inventory_slot": "banners"}

# so uh i need to add the translations later because i need to think -fire
# Part of the shop buy command
@misc.paginator
def theme_page(themes_embed, theme, **extras):
    price_divisor = extras.get('price_divisor', 1)
    themes_embed.add_field(name=theme["icon"] + " | " + theme["name"], value=(theme["description"] + "\n ``"
                                                                              + util.format_number(
        theme["price"] // price_divisor, money=True, full_precision=True) + "``"))


@misc.paginator
def background_page(backgrounds_embed, background, **extras):
    price_divisor = extras.get('price_divisor', 1)
    backgrounds_embed.add_field(name=background["icon"] + " | " + background["name"],
                                value=(background["description"] + "\n ``"
                                       + util.format_number(background["price"] // price_divisor, money=True,
                                                            full_precision=True) + "``"))


@misc.paginator
def banner_page(banners_embed, banner, **extras):
    price_divisor = extras.get('price_divisor', 1)
    banners_embed.add_field(name=banner.icon + " | " + banner.name,
                            value=(banner.description + "\n ``"
                                   + util.format_number(banner.price // price_divisor,
                                                        money=True, full_precision=True) + "``"))


def theme_info(theme_name, **details):
    embed = details["embed"]
    price_divisor = details.get('price_divisor', 1)
    theme = details.get('theme', customizations.get_theme(theme_name))
    embed.title = str(theme)
    embed.set_image(url=theme["preview"])
    embed.set_footer(text="Buy this theme for " + util.format_number(theme["price"] // price_divisor, money=True,
                                                                     full_precision=True))
    return embed


def background_info(background_name, **details):
    embed = details["embed"]
    price_divisor = details.get('price_divisor', 1)
    background = customizations.get_background(background_name)
    embed.title = str(background)
    embed.set_image(url="https://battlebanana.xyz/duefiles/backgrounds/" + background["image"])
    embed.set_footer(
        text="Buy this background for " + util.format_number(background["price"] // price_divisor, money=True,
                                                             full_precision=True))
    return embed


def banner_info(banner_name, **details):
    embed = details["embed"]
    price_divisor = details.get('price_divisor', 1)
    banner = customizations.get_banner(banner_name)
    embed.title = str(banner)
    if banner.donor:
        embed.description = ":star2: This is a __donor__ banner!"
    embed.set_image(url="https://battlebanana.xyz/duefiles/banners/" + banner.image_name)
    embed.set_footer(text="" + util.format_number(banner.price // price_divisor, money=True,
                                                                      full_precision=True))
    return embed

