import discord
import random
import time

import dueutil.game.awards as game_awards
import generalconfig as gconf
from ..game import players, customizations
from ..game import stats, game, quests
from ..game.helpers import misc, playersabstract, imagehelper
from ..game.configs import dueserverconfig
from .. import commands, util, dbconn
from ..game import emojis as e

DAILY_AMOUNT = 50
TRAIN_RANGE = (0.1, 0.3)

@commands.command(args_pattern=None)
@commands.ratelimit(cooldown=86400, error="You can't collect your daily reward again for **[COOLDOWN]**!", save=True)
async def daily(ctx, **details):
    """
    [CMD_KEY]daily

    ¤50! Your daily pocket money!

    You can use this command once very 24 hours!
    """
    player = details["author"]
    BALANCED_AMOUNT = DAILY_AMOUNT * player.level
    player.money += BALANCED_AMOUNT
    player.save()
    await util.say(ctx.channel, e.DUT + " **%s** collected their daily ¤%d!" % (player, BALANCED_AMOUNT))

@commands.command(args_pattern=None)
@commands.ratelimit(cooldown=21600, error="You've done all the training you can for now! You can train again in **[COOLDOWN]**!", save=True)
async def train(ctx, **details):
    """
    [CMD_KEY]train

    Train to get a little exp to help you with quests.

    This will never give you much exp! But should help you out with quests early on!

    You can use this command once every 6 hours!
    """

    player = details["author"]
    maxstats = 100

    attack_increase = random.uniform(*TRAIN_RANGE) * player.level
    strg_increase = random.uniform(*TRAIN_RANGE) * player.level
    accy_increase = random.uniform(*TRAIN_RANGE) * player.level

    prestige_gain = random.uniform(0.75, 1.25) * (20 * player.prestige_level)
    maxstats = maxstats + prestige_gain

    if player.donor:
        maxstats = 200
        attack_increase = attack_increase * 2 + prestige_gain
        strg_increase = strg_increase * 2 + prestige_gain
        accy_increase = accy_increase * 2 + prestige_gain

    if attack_increase > maxstats:
        attack_increase = maxstats
    if strg_increase > maxstats:
        strg_increase = maxstats
    if accy_increase > maxstats:
        accy_increase = maxstats

    player.progress(attack_increase, strg_increase, accy_increase,
                    max_exp=100, max_attr=maxstats)
    progress_message = players.STAT_GAIN_FORMAT % (attack_increase, strg_increase, accy_increase)

    train_embed = discord.Embed(title="You trained like a mad man!", description="After a hard moment, you feel stronger!", type="rich", color=gconf.DUE_COLOUR)
    train_embed.add_field(name="Training result:", value=progress_message, inline=True)
    train_embed.set_footer(text='You feel exhausted and may train again in 6 hours!')

    await game.check_for_level_up(ctx, player)
    player.save()
    await util.say(ctx.channel, "**%s** training complete!\n" % player, embed=train_embed)

@commands.command(args_pattern=None)
@commands.ratelimit(cooldown=604800, error="You can't collect your weekly reward again for **[COOLDOWN]**!", save=True)
async def weekly(ctx, **details):
    """
    [CMD_KEY]weekly

    Your weekly free and easy to get quest!

    You can use this command once very 7 days!
    """
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
    """
    [CMD_KEY]mylimit

    Shows the weapon price you're limited to.
    """

    player = details["author"]
    await util.say(ctx.channel, "You're currently limited to weapons with a value up to **%s**!"
                   % util.format_number(player.item_value_limit, money=True, full_precision=True))


@commands.command(args_pattern="S?")
async def battlename(ctx, name="", **details):
    """
    [CMD_KEY]battlename (name)
    
    Sets your name in DueUtil.
    To reset your name to your discord name run the
    command with no arguments
    """

    player = details["author"]
    if name != "":
        name_len_range = players.Player.NAME_LENGTH_RANGE
        if len(name) not in name_len_range:
            raise util.DueUtilException(ctx.channel, "Battle name must be between **%d-%d** characters long!"
                                                     % (min(name_len_range), max(name_len_range)))
        player.name = name
    else:
        player.name = details["author_name"]
    player.save()
    await util.say(ctx.channel, "Your battle name has been set to **%s**!" % player.name_clean)


@commands.command(args_pattern=None, aliases=["mi"])
@commands.imagecommand()
async def myinfo(ctx, **details):
    """
    [CMD_KEY]myinfo
    
    Shows your info!
    """

    await imagehelper.stats_screen(ctx.channel, details["author"])


def player_profile_url(player_id):
    private_record = dbconn.conn()["public_profiles"].find_one({"_id": player_id})

    if private_record is None or private_record["private"]:
        return None
    return "https://dueutil.tech/player/id/%s" % player_id


@commands.command(args_pattern=None)
async def myprofile(ctx, **details):
    """
    [CMD_KEY]myprofile

    Gives the link to your dueutil.tech profile
    """

    profile_url = player_profile_url(details["author"].id)

    if profile_url is None:
        await util.say(ctx.channel, (":lock: Your profile is currently set to private!\n"
                                     + "If you want a public profile login to <https://dueutil.tech/>"
                                     + " and make your profile public in the settings."))
    else:
        await util.say(ctx.channel, "Your profile is at %s" % profile_url)


@commands.command(args_pattern='P')
async def profile(ctx, player, **_):
    """
    [CMD_KEY]profile @player

    Gives a link to a player's profile!
    """

    profile_url = player_profile_url(player.id)

    if profile_url is None:
        await util.say(ctx.channel, ":lock: **%s** profile is private!" % player.get_name_possession_clean())
    else:
        await util.say(ctx.channel, "**%s** profile is at %s" % (player.get_name_possession_clean(), profile_url))


@commands.command(args_pattern='P', aliases=["in"])
@commands.imagecommand()
async def info(ctx, player, **_):
    """
    [CMD_KEY]info @player
    
    Shows the info of another player!
    """

    await imagehelper.stats_screen(ctx.channel, player)


async def show_awards(ctx, player, page=0):
    # Always show page 1 (0)
    if page != 0 and page * 5 >= len(player.awards):
        raise util.DueUtilException(ctx.channel, "Page not found")

    await imagehelper.awards_screen(ctx.channel, player, page,
                                    is_player_sender=ctx.author.id == player.id)


@commands.command(args_pattern='C?')
@commands.imagecommand()
async def myawards(ctx, page=1, **details):
    """
    [CMD_KEY]myawards (page number)
    
    Shows your awards!
    """

    await show_awards(ctx, details["author"], page - 1)


@commands.command(args_pattern='PC?')
@commands.imagecommand()
async def awards(ctx, player, page=1, **_):
    """
    [CMD_KEY]awards @player (page number)
    
    Shows a players awards!
    """

    await show_awards(ctx, player, page - 1)


@commands.command(args_pattern="S?")
@commands.require_cnf(warning="This will **__permanently__** reset your user!")
async def resetme(ctx, cnf="", **details):
    """
    [CMD_KEY]resetme
    
    Resets all your stats & any customization.
    This cannot be reversed!
    """

    player = details["author"]
    player.reset(ctx.author)
    await util.say(ctx.channel, "Your user has been reset.")

@commands.command(args_pattern='PCS?', aliases=["sq"])
async def sendquest(ctx, receiver, quest_index, message="", **details):
    """
    [CMD_KEY]sendquest @player (quest number) (optional message)

    Sends one of your quest to another player.
    Note: The quest can't be 10 level higher the other player's level.
    """

    plr = details["author"]
    quest_index -= 1

    if receiver.id == plr.id:
        raise util.DueUtilException(ctx.channel, "There is no reason to send a quest to yourself!")
    if quest_index >= len(plr.quests):
        raise util.DueUtilException(ctx.channel, "Quest not found!")
    plr_quest = plr.quests[quest_index]
    if plr_quest.level > (receiver.level + 10):
        raise util.DueUtilException(ctx.channel, "The quest is too strong for the player! Highest quest level for this player is " + str(receiver.level + 10) + "!")

    quest_name = plr_quest.name
    quest_level = str(plr_quest.level)

    receiver.quests.append(plr_quest)
    del plr.quests[quest_index]

    receiver.save()
    plr.save()
    
    transaction_log = discord.Embed(title=e.QUESTER + " Transaction complete!", type="rich",
                                    color=gconf.DUE_COLOUR)
    transaction_log.add_field(name="Sender:", value=plr.name_clean)
    transaction_log.add_field(name="Recipient:", value=receiver.name_clean)
    transaction_log.add_field(name="Transaction:", value=quest_name + ", level " + quest_level, inline=False)
    if message != "":
        transaction_log.add_field(name=":pencil: Attached note:", value=message, inline=False)
    transaction_log.set_footer(text="Please keep this receipt for your records.")
    util.logger.info("%s (%s) sent %s to %s (%s)", plr.name, plr.id, quest_name + ", level " + quest_level, receiver.name, receiver.id)

    await util.say(ctx.channel, embed=transaction_log)


@commands.command(args_pattern='PP?')
async def compare(ctx, player1, player2=None, **details):
    """
    [CMD_KEY]compare Player1 Player2

    Compares 2 player's statistic! 
    
    If the "Player2" argument is not given, it will compare you to the "Player1"
    """
    
    plr = details["author"]
    if player2 is None and player1 == plr:
        raise util.DueUtilException(ctx.channel, "There is no reason to compare yourself! You are as good as yourself (:")
    if player1 == player2:
        raise util.DueUtilException(ctx.channel, "There is no reason to compare the same player!")
    
    compare_Embed = discord.Embed()

    if player2 is None:
        player2 = player1
        player1 = plr
    compare_Embed.title = "Comparing **%s** with **%s**!" % (player1.name_clean, player2.name_clean)
    compare_Embed.add_field(
        name=player1.name_clean,
        value=("Level: %s\nHealth: %.2f\nAttack: %.2f\nStrength: %.2f\nAccuracy: %.2f" % (player1.level, player1.hp * player1.strg, player1.attack, player1.strg, player1.accy)), 
        inline=True
    )
    compare_Embed.add_field(
        name=player2.name_clean,
        value=("Level: %s\nHealth: %.2f\nAttack: %.2f\nStrength: %.2f\nAccuracy: %.2f" % (player2.level, player2.hp * player2.strg, player2.attack, player2.strg, player2.accy)), 
        inline=True
    )

    await util.say(ctx.channel, embed=compare_Embed)

@commands.command(args_pattern='PCS?', aliases=["sc"])
async def sendcash(ctx, receiver, transaction_amount, message="", **details):
    """
    [CMD_KEY]sendcash @player amount (optional message)
    
    Sends some cash to another player.
    Note: The maximum amount someone can receive is ten times their limit.
    
    Example usage:
    
    [CMD_KEY]sendcash @MacDue 1000000 "for the lit bot fam"
    
    or
    
    [CMD_KEY]sendcash @MrAwais 1
    """

    sender = details["author"]
    amount_string = util.format_number(transaction_amount, money=True, full_precision=True)

    if receiver.id == sender.id:
        raise util.DueUtilException(ctx.channel, "There is no reason to send money to yourself!")

    if sender.money - transaction_amount < 0:
        if sender.money > 0:
            await util.say(ctx.channel, ("You do not have **" + amount_string + "**!\n"
                                                                                "The maximum you can transfer is **"
                                         + util.format_number(sender.money, money=True, full_precision=True) + "**"))
        else:
            await util.say(ctx.channel, "You do not have any money to transfer!")
        return

    max_receive = int(receiver.item_value_limit * 10)
    if transaction_amount > max_receive:
        await util.say(ctx.channel, ("**" + amount_string
                                     + "** is more than ten times **" + receiver.name_clean
                                     + "**'s limit!\nThe maximum **" + receiver.name_clean
                                     + "** can receive is **"
                                     + util.format_number(max_receive, money=True, full_precision=True) + "**!"))
        return

    sender.money -= transaction_amount
    receiver.money += transaction_amount

    sender.save()
    receiver.save()

    stats.increment_stat(stats.Stat.MONEY_TRANSFERRED, transaction_amount)
    if transaction_amount >= 50:
        await game_awards.give_award(ctx.channel, sender, "SugarDaddy", "Sugar daddy!")

    transaction_log = discord.Embed(title=e.DUT_WITH_WINGS + " Transaction complete!", type="rich",
                                    color=gconf.DUE_COLOUR)
    transaction_log.add_field(name="Sender:", value=sender.name_clean)
    transaction_log.add_field(name="Recipient:", value=receiver.name_clean)
    transaction_log.add_field(name="Transaction amount (DUT):", value=amount_string, inline=False)
    if message != "":
        transaction_log.add_field(name=":pencil: Attached note:", value=message, inline=False)
    transaction_log.set_footer(text="Please keep this receipt for your records.")
    util.logger.info("%s (%s) sent %s to %s (%s)", sender.name, sender.id, amount_string, receiver.name, receiver.id)

    await util.say(ctx.channel, embed=transaction_log)

@commands.command(args_pattern=None)
async def prestige(ctx, **details):
    """
    [CMD_KEY]prestige

    Make you restart from 0, 
    keeping few stats 
    and having some bonuses :)
    """

    user = details["author"]
    prestige_level = 80 + (20 * user.prestige_level)
    req_money = 5000000 * (user.prestige_level + 1)

    if user.level < prestige_level:
        raise util.DueUtilException(ctx.channel, "You need to be level %s or higher to go to the next prestige!" % prestige_level)
    if user.money < req_money:
        raise util.DueUtilException(ctx.channel, "You need atleast %s %s to afford the next prestige!" % (util.format_number_precise(req_money), e.DUT))

    user.money -= req_money
    user.prestige()

@commands.command(args_pattern="P?", aliases=["mp", "showprestige", "sp"])
async def myprestige(ctx, player=None, **details):
    """
    [CMD_KEY]myprestige (player)

    Display what prestige the player is, if no argument is given, it will display your prestige and how many DUTs & level you need for the next prestige!
    """

    if player is None:
        player = details["author"]
    prestige_level = 80 + (20 * player.prestige_level)
    req_money = 5000000 * (player.prestige_level + 1)

    message = "You are prestige **%s**! " % player.prestige_level
    if prestige_level > player.level:
        message += "You need **%s** more levels & " % (prestige_level - player.level)
    else:
        message += "You satisfy the level requirement & "
    if req_money > player.money:
        message += "you need **%s %s** to afford the next prestige!" % (util.format_number_precise(req_money - player.money), e.DUT)
    else:
        message += "you satisfy the money requirement!"
    
    await util.say(ctx.channel, message)

@commands.command(hidden=True, args_pattern=None)
async def benfont(ctx, **details):
    """
    [CMD_KEY]benfont 
    
    Shhhhh...
    """

    player = details["author"]
    player.benfont = not player.benfont
    player.save()
    if player.benfont:
        await util.get_client(ctx.server.id).send_file(ctx.channel, 'assets/images/nod.gif')
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
    """
    [CMD_KEY]mythemes (optional theme name)
    
    Shows the amazing themes you can use on your profile.
    If you use this command with a theme name you can get a preview of the theme!
    """

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
    """
    [CMD_KEY]settheme (theme name)
    
    Sets your profile theme
    """

    return {"thing_type": "theme", "thing_inventory_slot": "themes"}


@commands.command(args_pattern='M?', aliases=("mybackgrounds", "backgrounds"))
@playersabstract.item_preview
def mybgs(player):
    """
    [CMD_KEY]mybgs (optional background name)
    
    Shows the backgrounds you've bought!
    """

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
    """
    [CMD_KEY]setbg (background name)
    
    Sets your profile background
    """

    return {"thing_type": "background", "thing_inventory_slot": "backgrounds"}


@commands.command(args_pattern='M?')
@playersabstract.item_preview
def mybanners(player):
    """
    [CMD_KEY]mybanners (optional banner name)
    
    Shows the banners you've bought!
    """
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
    """
    [CMD_KEY]setbanner (banner name)
    
    Sets your profile banner
    """

    return {"thing_type": "banner", "thing_inventory_slot": "banners"}


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
    embed.set_image(url="https://dueutil.tech/duefiles/backgrounds/" + background["image"])
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
    embed.set_image(url="https://dueutil.tech/duefiles/banners/" + banner.image_name)
    embed.set_footer(text="Buy this banner for " + util.format_number(banner.price // price_divisor, money=True,
                                                                      full_precision=True))
    return embed

