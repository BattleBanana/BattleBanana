import random
import secrets
import time

import discord

import dueutil.game.awards as game_awards
import generalconfig as gconf
from dueutil import commands, dbconn, util
from dueutil.game import customizations, emojis, game, gamerules, players, quests, stats
from dueutil.game.configs import dueserverconfig
from dueutil.game.helpers import imagehelper, misc, playersabstract
from dueutil.permissions import Permission

DAILY_AMOUNT = 50
TRAIN_RANGE = (0.1, 0.3)


@commands.command(args_pattern=None)
@commands.ratelimit(cooldown=86400, error="You can collect your daily reward again **[COOLDOWN]**!", save=True)
async def daily(ctx, **details):
    """
    [CMD_KEY]daily

    ¤50 * your level! Your daily pocket money!

    You can use this command once every 24 hours!

    Joining the support server will give you 10% more! <https://battlebanana.xyz/support>
    """
    player = details["author"]
    responses = game.get_responses()

    balanced_amount = DAILY_AMOUNT * player.level * player.prestige_multiplicator()

    # 10% more for joining the support server
    support_server = util.get_guild(gconf.THE_DEN)
    if not support_server.chunked:
        await support_server.chunk()

    is_in_support_server = support_server.get_member(player.id)
    if is_in_support_server:
        balanced_amount = int(balanced_amount * 1.1)

    player.money += balanced_amount
    player.save()

    await util.reply(
        ctx,
        emojis.BBT
        + f" {secrets.choice(responses).format(user=f"**{player}**", daily=f"{util.format_money(balanced_amount)}")}\n{"" if is_in_support_server else "-# Did you know? You can get 10% more by joining the [support server](<https://battlebanana.xyz/support>)!"}",
    )


@commands.command(args_pattern=None)
@commands.ratelimit(
    cooldown=21600,
    error="You've done all the training you can for now! You can train again **[COOLDOWN]**!",
    save=True,
)
async def train(ctx, **details):
    """
    [CMD_KEY]train

    Train to get a little exp to help you with quests.

    This will never give you much exp! But should help you out with quests early on!

    You can use this command once every 6 hours!
    """

    player = details["author"]
    maxstats = 100 * player.prestige_multiplicator()

    attack_increase = random.uniform(*TRAIN_RANGE) * player.level * player.prestige_multiplicator()
    strg_increase = random.uniform(*TRAIN_RANGE) * player.level * player.prestige_multiplicator()
    accy_increase = random.uniform(*TRAIN_RANGE) * player.level * player.prestige_multiplicator()

    # 10% more for joining support server
    support_server = util.get_guild(gconf.THE_DEN)
    if not support_server.chunked:
        await support_server.chunk()

    is_in_support_server = support_server.get_member(player.id)
    if is_in_support_server:
        attack_increase *= 1.1
        strg_increase *= 1.1
        accy_increase *= 1.1

    player.progress(attack_increase, strg_increase, accy_increase, max_exp=maxstats, max_attr=maxstats)
    progress_message = players.STAT_GAIN_FORMAT % (attack_increase, strg_increase, accy_increase)

    train_embed = discord.Embed(
        title="You trained like a mad man!",
        description="After a hard moment, you feel stronger!",
        type="rich",
        color=gconf.DUE_COLOUR,
    )
    train_embed.add_field(name="Training result:", value=progress_message, inline=True)
    train_embed.set_footer(text="You feel exhausted and may train again in 6 hours!")
    if not is_in_support_server:
        train_embed.set_footer(
            text="Did you know? You can get 10% more by joining the [support server](<https://battlebanana.xyz/support>)!"
        )

    await game.check_for_level_up(ctx, player)
    player.save()
    await util.reply(ctx, f"**{player}** training complete!\n", embed=train_embed)


@commands.command(args_pattern=None)
@commands.ratelimit(cooldown=604800, error="You can collect your weekly reward again **[COOLDOWN]**!", save=True)
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
            image = await imagehelper.new_quest(ctx, new_quest, player)

            quest_file = imagehelper.image_to_discord_file(image, "quest.png")

            embed = discord.Embed(
                title="Weekly Reward!", description="Here is your weekly reward!", type="rich", color=gconf.DUE_COLOUR
            )
            embed.set_image(url="attachment://quest.png")

            await util.reply(ctx, file=quest_file, embed=embed)
        else:
            util.logger.info("Won't send weekly image - channel blocked.")


@commands.command(args_pattern=None)
async def mylimit(ctx, **details):
    """
    [CMD_KEY]mylimit

    Shows the weapon price you're limited to.
    """

    player = details["author"]
    await util.reply(
        ctx,
        (
            "You're currently limited to weapons with a value up to"
            + f"**{util.format_number(player.item_value_limit, money=True, full_precision=True)}**!"
        ),
    )


@commands.command(args_pattern="S?", aliases=["bn"])
async def battlename(ctx, name="", **details):
    """
    [CMD_KEY]battlename (name)

    Sets your name in BattleBanana.
    To reset your name to your discord name run the
    command with no arguments
    """

    player = details["author"]
    if name != "":
        name_len_range = players.Player.NAME_LENGTH_RANGE
        if len(name) not in name_len_range:
            raise util.BattleBananaException(
                ctx.channel,
                f"Battle name must be between **{min(name_len_range)}-{max(name_len_range)}** characters long!",
            )
        player.name = util.filter_string(name)
    else:
        player.name = details["author_name"]
    player.save()
    await util.reply(ctx, f"Your battle name has been set to **{player.name_clean}**!")


@commands.command(args_pattern=None, aliases=["mi"])
@commands.imagecommand()
async def myinfo(ctx, **details):
    """
    [CMD_KEY]myinfo

    Shows your info!
    """

    await imagehelper.stats_screen(ctx, details["author"])


def player_profile_url(player_id):
    private_record = dbconn.conn()["public_profiles"].find_one({"_id": player_id})

    if private_record is None or private_record["private"]:
        return None

    return f"https://battlebanana.xyz/player/id/{player_id}"


@commands.command(args_pattern=None)
async def myprofile(ctx, **details):
    """
    [CMD_KEY]myprofile

    Gives the link to your battlebanana.xyz profile
    """

    profile_url = player_profile_url(details["author"].id)
    if profile_url is None:
        await util.reply(
            ctx,
            (
                ":lock: Your profile is currently set to private!\n"
                + "If you want a public profile login to <https://battlebanana.xyz/>"
                + " and make your profile public in the settings."
            ),
        )
    else:
        await util.reply(ctx, f"Your profile is at {profile_url}")


@commands.command(args_pattern="P")
async def profile(ctx, player, **_):
    """
    [CMD_KEY]profile @player

    Gives a link to a player's profile!
    """

    profile_url = player_profile_url(player.id)

    if profile_url is None:
        await util.reply(ctx, f":lock: **{player.get_name_possession_clean()}** profile is private!")
    else:
        await util.reply(ctx, f"**{player.get_name_possession_clean()}** profile is at {profile_url}")


@commands.command(args_pattern="P", aliases=["in"])
@commands.imagecommand()
async def info(ctx, player, **_):
    """
    [CMD_KEY]info @player

    Shows the info of another player!
    """

    await imagehelper.stats_screen(ctx, player)


async def show_awards(ctx, player, page=0):
    # Always show page 1 (0)
    if page != 0 and page * 5 >= len(player.awards):
        raise util.BattleBananaException(ctx.channel, "Page not found")

    await imagehelper.awards_screen(ctx, player, page, is_player_sender=ctx.author.id == player.id)


@commands.command(args_pattern=None, aliases=["hmw"])
async def hidemyweapon(ctx, **details):
    """
    [CMD_KEY]hidemyweapon

    Hides your weapon
    """
    player = details["author"]

    player.weapon_hidden = not player.weapon_hidden
    player.save()

    await util.reply(
        ctx, "Your weapon is now hidden!" if player.weapon_hidden else "Your weapon is not hidden anymore!"
    )


@commands.command(args_pattern="C?")
@commands.imagecommand()
async def myawards(ctx, page=1, **details):
    """
    [CMD_KEY]myawards (page number)

    Shows your awards!
    """

    await show_awards(ctx, details["author"], page - 1)


@commands.command(args_pattern="PC?")
@commands.imagecommand()
async def awards(ctx, player, page=1, **_):
    """
    [CMD_KEY]awards @player (page number)

    Shows a players awards!
    """

    await show_awards(ctx, player, page - 1)


@commands.command(args_pattern="S?")
@commands.require_cnf(warning="This will **__permanently__** reset your user!")
async def resetme(ctx, **details):
    """
    [CMD_KEY]resetme

    Resets all your stats & any customization.
    This cannot be reversed!
    """

    player = details["author"]
    player.reset(ctx.author)
    await util.reply(ctx, "Your user has been reset.")


@commands.command(permission=Permission.DISCORD_USER, args_pattern=None, aliases=["start"])
async def createaccount(ctx, **details):
    """
    [CMD_KEY]createaccount

    Create your account to start your BattleBanana adventure
    """

    player = details["author"]

    if player:
        return await util.reply(ctx, "You are already registered")

    player = players.Player(ctx.author)
    player.save()
    stats.increment_stat(stats.Stat.NEW_PLAYERS_JOINED)

    embed = discord.Embed(title="Welcome to BattleBanana!", color=0xFEE761)
    embed.add_field(
        name="How to play?",
        value="We have an extensive guide on how to play BattleBanana.\n"
        "You can find it at <https://battlebanana.xyz/howto>",
    )
    embed.add_field(
        name="How to get started?", value="You can find a list of all commands at <https://battlebanana.xyz/commands>"
    )
    embed.add_field(
        name="Need more help?",
        value=(
            "You can join our support server at <https://battlebanana.xyz/support>"
            + "and we'll be more than happy to help you out!"
        ),
    )
    embed.set_footer(text="BattleBanana - Created by @DeveloperAnonymous")

    await util.reply(ctx, "Your account has been created!", embed=embed)


@commands.command(args_pattern="S?")
@commands.require_cnf(warning="This will **__permanently__** delete your account!")
async def deleteme(ctx, **details):
    """
    [CMD_KEY]deleteme

    Deletes all your stats & any customization.
    This cannot be reversed!
    """

    player = details["author"]

    dbconn.delete_player(player)

    await util.reply(ctx, "Your account has been deleted.")


@commands.command(args_pattern="PCS?", aliases=["sq"])
async def sendquest(ctx, receiver, quest_index, message="", **details):
    """
    [CMD_KEY]sendquest @player (quest number) (optional message)

    Sends one of your quest to another player.
    Note: The quest can't be 10 level higher the other player's level.
    """

    plr = details["author"]
    quest_index -= 1

    if receiver.id == plr.id:
        raise util.BattleBananaException(ctx.channel, "There is no reason to send a quest to yourself!")
    if quest_index >= len(plr.quests):
        raise util.BattleBananaException(ctx.channel, "Quest not found!")
    plr_quest = plr.quests[quest_index]
    if plr_quest.level > (receiver.level + 10):
        raise util.BattleBananaException(
            ctx.channel,
            "The quest is too strong for the player! Highest quest level for this player is "
            + str(receiver.level + 10)
            + "!",
        )

    quest_name = plr_quest.name
    quest_level = str(plr_quest.level)

    receiver.quests.append(plr_quest)
    del plr.quests[quest_index]

    rec_quest = receiver.quests[-1]
    rec_quest.quester_id = receiver.id
    rec_quest.quester = receiver

    receiver.save()
    plr.save()

    transaction_log = discord.Embed(
        title=emojis.QUESTER + " Transaction complete!", type="rich", color=gconf.DUE_COLOUR
    )
    transaction_log.add_field(name="Sender:", value=plr.name_clean)
    transaction_log.add_field(name="Recipient:", value=receiver.name_clean)
    transaction_log.add_field(name="Transaction:", value=quest_name + ", level " + quest_level, inline=False)
    if message != "":
        transaction_log.add_field(name=":pencil: Attached note:", value=message, inline=False)
    transaction_log.set_footer(text="Please keep this receipt for your records.")
    util.logger.info(
        "%s (%s) sent %s to %s (%s)",
        plr.name,
        plr.id,
        quest_name + ", level " + quest_level,
        receiver.name,
        receiver.id,
    )

    await util.reply(ctx, embed=transaction_log)


@commands.command(args_pattern="PP?")
async def compare(ctx, player1, player2=None, **details):
    """
    [CMD_KEY]compare Player1 Player2

    Compares 2 player's statistic!

    If the "Player2" argument is not given, it will compare you to the "Player1"
    """

    plr = details["author"]
    if player2 is None and player1 == plr:
        raise util.BattleBananaException(
            ctx.channel, "There is no reason to compare yourself! You are as good as yourself (:"
        )
    if player1 == player2:
        raise util.BattleBananaException(ctx.channel, "There is no reason to compare the same player!")

    if player2 is None:
        player2 = player1
        player1 = plr

    compare_embed = discord.Embed(title=f"Comparing **{player1.name_clean}** with **{player2.name_clean}**!")
    compare_embed.add_field(
        name=player1.name_clean,
        value=(
            f"Prestige: {player1.prestige_level}\n"
            + f"Level: {player1.level}\n"
            + f"Health: {player1.hp * player1.strg:.2f}\n"
            + f"Attack: {player1.attack:.2f}\n"
            + f"Strength: {player1.strg:.2f}\n"
            + f"Accuracy: {player1.accy:.2f}"
        ),
        inline=True,
    )
    compare_embed.add_field(
        name=player2.name_clean,
        value=(
            f"Prestige: {player2.prestige_level}\n"
            + f"Level: {player2.level}\n"
            + f"Health: {player2.hp * player2.strg:.2f}\n"
            + f"Attack: {player2.attack:.2f}\n"
            + f"Strength: {player2.strg:.2f}\n"
            + f"Accuracy: {player2.accy:.2f}"
        ),
        inline=True,
    )

    await util.reply(ctx, embed=compare_embed)


@commands.command(args_pattern="PCS?", aliases=["sc"])
async def sendcash(ctx, receiver, transaction_amount, message="", **details):
    """
    [CMD_KEY]sendcash @player amount (optional message)

    Sends some cash to another player.
    Note: The maximum amount someone can receive is ten times their limit.

    Example usage:

    [CMD_KEY]sendcash @MrAwais 1000000 "for the lit bot fam"

    or

    [CMD_KEY]sendcash @MrAwais 1
    """

    sender = details["author"]
    amount_string = util.format_number(transaction_amount, money=True, full_precision=True)

    if receiver.id == sender.id:
        raise util.BattleBananaException(ctx.channel, "There is no reason to send money to yourself!")

    if sender.money - transaction_amount < 0:
        if sender.money > 0:
            await util.reply(
                ctx,
                (
                    "You do not have **" + amount_string + "**!\n"
                    "The maximum you can transfer is **"
                    + util.format_number(sender.money, money=True, full_precision=True)
                    + "**"
                ),
            )
        else:
            await util.reply(ctx, "You do not have any money to transfer!")
        return

    max_receive = int(receiver.item_value_limit * 10)
    if transaction_amount > max_receive and sender.id != 426822266412728323:  # Chara
        await util.reply(
            ctx,
            (
                f"**{amount_string}** is more than ten times **{receiver.name_clean}**'s limit!\n"
                + f"The maximum **{receiver.name_clean}** can receive is **{util.format_number(max_receive, money=True, full_precision=True)}**!"
            ),
        )
        return

    sender.money -= transaction_amount

    battle_banana = players.find_player(ctx.guild.me.id)
    taxed_transaction_amount = await util.tax(transaction_amount, battle_banana)
    taxed_amount_string = util.format_number(taxed_transaction_amount, money=True, full_precision=True)
    taxed_total_string = util.format_number(
        transaction_amount - taxed_transaction_amount, money=True, full_precision=True
    )
    receiver.money += taxed_transaction_amount

    sender.save()
    receiver.save()

    stats.increment_stat(stats.Stat.MONEY_TRANSFERRED, taxed_transaction_amount)
    if taxed_transaction_amount >= 50:
        await game_awards.give_award(ctx.channel, sender, "SugarDaddy", "Sugar daddy!")

    transaction_log = discord.Embed(
        title=f"{emojis.BBT_WITH_WINGS} transaction complete!", type="rich", color=gconf.DUE_COLOUR
    )
    transaction_log.add_field(name="Sender:", value=sender.name_clean)
    transaction_log.add_field(name="Recipient:", value=receiver.name_clean)
    transaction_log.add_field(name="Transaction amount (BBT):", value=taxed_amount_string, inline=False)
    if message != "":
        transaction_log.add_field(name=":pencil: Attached note:", value=message, inline=False)
    transaction_log.set_footer(
        text=f"Please keep this receipt for your records • {taxed_total_string} (13%) was subtracted for taxes"
    )
    util.logger.info(
        "%s (%s) sent %s (%s) to %s (%s)",
        sender.name,
        sender.id,
        amount_string,
        taxed_amount_string,
        receiver.name,
        receiver.id,
    )

    await util.reply(ctx, embed=transaction_log)


@commands.command(args_pattern="S?")
@commands.require_cnf(warning="This action cannot be reverted, are you sure you want to prestige?")
async def prestige(ctx, **details):
    """
    [CMD_KEY]prestige

    Make you restart from 0,
    keeping few stats
    and having some bonuses :)
    """

    player = details["author"]
    prestige_level = gamerules.get_level_for_prestige(player.prestige_level)
    req_money = gamerules.get_money_for_prestige(player.prestige_level)

    if player.level < prestige_level:
        raise util.BattleBananaException(
            ctx.channel, f"You need to be level {prestige_level} or higher to go to the next prestige!"
        )
    if player.money < req_money:
        raise util.BattleBananaException(
            ctx.channel,
            f"You need atleast {util.format_number_precise(req_money)} {emojis.BBT} to afford the next prestige!",
        )

    player.money -= req_money
    player.prestige()

    if prestige_level > 0:
        await game.awards.give_award(ctx.channel, player, "Prestige")
    await util.reply(ctx, f"You successfully prestiged! You are now at prestige {player.prestige_level}, congrats!")


@commands.command(args_pattern="P?", aliases=["mp", "showprestige", "sp"])
async def myprestige(ctx, _=None, **__):
    """
    [CMD_KEY]myprestige (player)

    ~~Display what prestige the player is at.
    if no argument is given, it will display your prestige
    and how many BBTs & level you need for the next prestige!~~

    You can now see the prestige next to the level in the profile!
    It is shown as "Level X (Prestige)"

    NOTE: This command is deprecated and will be removed in the future.
    """

    await ctx.reply(
        'You can now see the prestige next to the level in the profile! It is shown as "Level X (Prestige)"'
        + "NOTE: This command is deprecated and will be removed in the future."
    )


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
        await ctx.channel.send(discord.File("assets/images/nod.gif"))
        await game_awards.give_award(ctx.channel, player, "BenFont", "ONE TRUE *type* FONT")


# WARNING: Setter & my commands use decorators to be lazy
# Setters just return the item type & inventory slot. (could be done without
# the decorators but setters must be fucntions anyway to be commands)
# This is part of my quest in finding lazy ways to do things I cba.


# Think about clean up & reuse
@commands.command(args_pattern="M?")
@playersabstract.item_preview
def mythemes(player):
    """
    [CMD_KEY]mythemes (optional theme name)

    Shows the amazing themes you can use on your profile.
    If you use this command with a theme name you can get a preview of the theme!
    """

    return {
        "thing_type": "theme",
        "thing_list": list(player.get_owned_themes().values()),
        "thing_lister": theme_page,
        "my_command": "mythemes",
        "set_command": "settheme",
        "thing_info": theme_info,
        "thing_getter": customizations.get_theme,
    }


@commands.command(args_pattern="S")
@playersabstract.item_setter
def settheme():
    """
    [CMD_KEY]settheme (theme name)

    Sets your profile theme
    """

    return {"thing_type": "theme", "thing_inventory_slot": "themes"}


@commands.command(args_pattern="M?", aliases=("mybackgrounds", "backgrounds"))
@playersabstract.item_preview
def mybgs(player):
    """
    [CMD_KEY]mybgs (optional background name)

    Shows the backgrounds you've bought!
    """

    return {
        "thing_type": "background",
        "thing_list": list(player.get_owned_backgrounds().values()),
        "thing_lister": background_page,
        "my_command": "mybgs",
        "set_command": "setbg",
        "thing_info": background_info,
        "thing_getter": customizations.get_background,
    }


@commands.command(args_pattern="S", aliases=["setbackground"])
@playersabstract.item_setter
def setbg():
    """
    [CMD_KEY]setbg (background name)

    Sets your profile background
    """

    return {"thing_type": "background", "thing_inventory_slot": "backgrounds"}


@commands.command(args_pattern="M?")
@playersabstract.item_preview
def mybanners(player):
    """
    [CMD_KEY]mybanners (optional banner name)

    Shows the banners you've bought!
    """
    return {
        "thing_type": "banner",
        "thing_list": list(player.get_owned_banners().values()),
        "thing_lister": banner_page,
        "my_command": "mybanners",
        "set_command": "setbanner",
        "thing_info": banner_info,
        "thing_getter": customizations.get_banner,
    }


@commands.command(args_pattern="S")
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
    price_divisor = extras.get("price_divisor", 1)
    themes_embed.add_field(
        name=theme["icon"] + " | " + theme["name"],
        value=(
            theme["description"]
            + "\n ``"
            + util.format_number(theme["price"] // price_divisor, money=True, full_precision=True)
            + "``"
        ),
    )


@misc.paginator
def background_page(backgrounds_embed, background, **extras):
    price_divisor = extras.get("price_divisor", 1)
    backgrounds_embed.add_field(
        name=background["icon"] + " | " + background["name"],
        value=(
            background["description"]
            + "\n ``"
            + util.format_number(background["price"] // price_divisor, money=True, full_precision=True)
            + "``"
        ),
    )


@misc.paginator
def banner_page(banners_embed, banner, **extras):
    price_divisor = extras.get("price_divisor", 1)
    banners_embed.add_field(
        name=banner.icon + " | " + banner.name,
        value=(
            banner.description
            + "\n ``"
            + util.format_number(banner.price // price_divisor, money=True, full_precision=True)
            + "``"
        ),
    )


def theme_info(theme_name, **details):
    embed = details["embed"]
    price_divisor = details.get("price_divisor", 1)
    theme = details.get("theme", customizations.get_theme(theme_name))
    embed.title = str(theme)
    embed.set_image(url=theme["preview"])
    embed.set_footer(
        text="Buy this theme for "
        + util.format_number(theme["price"] // price_divisor, money=True, full_precision=True)
    )
    return embed


def background_info(background_name, **details):
    embed = details["embed"]
    price_divisor = details.get("price_divisor", 1)
    background = customizations.get_background(background_name)
    embed.title = str(background)
    embed.set_image(url="https://battlebanana.xyz/duefiles/backgrounds/" + background["image"])
    embed.set_footer(
        text="Buy this background for "
        + util.format_number(background["price"] // price_divisor, money=True, full_precision=True)
    )
    return embed


def banner_info(banner_name, **details):
    embed = details["embed"]
    price_divisor = details.get("price_divisor", 1)
    banner = customizations.get_banner(banner_name)
    embed.title = str(banner)
    if banner.donor:
        embed.description = ":star2: This is a __donor__ banner!"
    embed.set_image(url="https://battlebanana.xyz/duefiles/banners/" + banner.image_name)
    embed.set_footer(
        text="Buy this banner for " + util.format_number(banner.price // price_divisor, money=True, full_precision=True)
    )
    return embed
