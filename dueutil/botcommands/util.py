import discord

import time

import repoze.timeago

import generalconfig as gconf
from ..game.configs import dueserverconfig
from ..permissions import Permission
from ..game import stats, awards, discoin
from ..game.stats import Stat
from .. import commands, events, util, permissions

# Shorthand for emoji as I use gconf to hold emoji constants
from ..game import emojis as e


@commands.command(permission=Permission.DISCORD_USER, args_pattern="S?", aliases=("helpme",))
async def help(ctx, *args, **details):
    """
    [CMD_KEY]help (command name or category)
    
    INCEPTION SOUND
    """

    help_logo = 'https://cdn.discordapp.com/attachments/173443449863929856/275299953528537088/helo_458x458.jpg'

    help_embed = discord.Embed(title="BattleBanana's Help", type="rich", color=gconf.DUE_COLOUR)
    server_key = details["cmd_key"]
    categories = events.command_event.category_list()

    if len(args) == 1:

        help_embed.set_thumbnail(url=help_logo)
        arg = args[0].lower()
        if arg not in categories:
            chosen_command = events.get_command(arg)
            # Dumb award
            if chosen_command is None:
                alias_count = 0
                if arg != "dumbledore":
                    command_name = 'Not found'
                    command_help = 'That command was not found!'
                else:
                    # Stupid award reference
                    command_name = 'dumbledore?!?'
                    command_help = 'Some stupid *joke?* reference to old due!!!111'
                    help_embed.set_image(url='http://i.imgur.com/UrWhI9P.gif')
                    await awards.give_award(ctx.channel, details["author"], "Daddy",
                                            "I have no memory of this award...")
            else:
                command_name = chosen_command.__name__
                alias_count = len(chosen_command.aliases)
                if chosen_command.__doc__ is not None:
                    command_help = chosen_command.__doc__.replace('[CMD_KEY]', server_key)
                else:
                    command_help = 'Sorry there is no help for that command!'

            help_embed.description = "Showing help for **" + command_name + "**"
            help_embed.add_field(name=":gear: " + command_name, value=command_help)
            if alias_count > 0:
                help_embed.add_field(name=":performing_arts: " + ("Alias" if alias_count == 1 else "Aliases"),
                                     value=', '.join(chosen_command.aliases), inline=False)
        else:
            category = arg
            help_embed.description = "Showing ``" + category + "`` commands."

            commands_for_all = events.command_event.command_list(
                filter=lambda command:
                command.permission in (Permission.PLAYER, Permission.DISCORD_USER) and command.category == category)
            admin_commands = events.command_event.command_list(
                filter=lambda command:
                command.permission == Permission.SERVER_ADMIN and command.category == category)
            server_op_commands = events.command_event.command_list(
                filter=lambda command:
                command.permission == Permission.REAL_SERVER_ADMIN and command.category == category)

            if len(commands_for_all) > 0:
                help_embed.add_field(name='Commands for everyone', value=', '.join(commands_for_all), inline=False)
            if len(admin_commands) > 0:
                help_embed.add_field(name='Admins only', value=', '.join(admin_commands), inline=False)
            if len(server_op_commands) > 0:
                help_embed.add_field(name='Server managers only', value=', '.join(server_op_commands), inline=False)
    else:

        help_embed.set_thumbnail(url=util.get_client(ctx.server.id).user.avatar_url)

        help_embed.description = 'Welcome to the help!\n Simply do ' + server_key + 'help (category) or (command name).'
        help_embed.add_field(name=':file_folder: Command categories', value=', '.join(categories))
        help_embed.add_field(name=e.THINKY_FONK + " Tips",
                             value=("If BattleBanana reacts to your command it means something is wrong!\n"
                                    + ":question: - Something is wrong with the command's syntax.\n"
                                    + ":x: - You don't have the required permissions to use the command."))
        help_embed.add_field(name=":link: Links", value=("**Invite me: %s**\n" % gconf.BOT_INVITE
                                                         + "BattleBanana guide: https://dueutil.xyz/howto\n"
                                                         + "Support server: https://discord.gg/P7DBDEC\n"
                                                         + "Support me: https://patreon.com/developeranonymous"))
        help_embed.set_footer(text="To use admin commands you must have the manage server permission or the 'Due Commander' role.")

    await util.say(ctx.channel, embed=help_embed)

@commands.command(permission=Permission.DISCORD_USER, args_pattern=None)
async def invite(ctx, **_):
    """
    [CMD_KEY]invite

    Display BattleBanana invite link & Support server.
    """
    
    invite_embed = discord.Embed(title="BattleBanana's invites", type="rich", color=gconf.DUE_COLOUR)
    invite_embed.description = "Here are 2 important links about me! :smiley:"
    invite_embed.add_field(name="Invite me:", value=("[Here](%s)" % gconf.BOT_INVITE), inline=True)
    invite_embed.add_field(name="Support server:", value="[Here](https://discord.gg/P7DBDEC)", inline=True)
    await util.say(ctx.channel, embed=invite_embed)

@commands.command(permission=Permission.DISCORD_USER, args_pattern=None)
async def donate(ctx, **_):
    """
    [CMD_KEY]donate

    This command show where you can donate to <@115269304705875969>. 
    All money received will be used for the server costs and other expenses.
    """

    donation_embed = discord.Embed(title="Donate", type="rich", color=gconf.DUE_COLOUR)
    donation_embed.add_field(name="Patreon (Donation)", value="[Here](https://patreon.com/developeranonymous)", inline=True)
    await util.say(ctx.channel, embed=donation_embed)

@commands.command(permission=Permission.DISCORD_USER, args_pattern=None)
async def botinfo(ctx, **_):
    """
    [CMD_KEY]botinfo

    General information about BattleBanana.
    """

    info_embed = discord.Embed(title="BattleBanana's Information", type="rich", color=gconf.DUE_COLOUR)
    info_embed.description = "BattleBanana is customizable bot to add fun commands, quests and battles to your server."
    info_embed.add_field(name="Originally DueUtil by", value="[MacDue#4453](https://dueutil.tech/)")
    info_embed.add_field(name="Continued by", value="[DeveloperAnonymous#9830](https://dueutil.xyz/)")
    info_embed.add_field(name="Framework",
                         value="[discord.py %s :two_hearts:](http://discordpy.readthedocs.io/en/latest/)"
                               % discord.__version__)
    info_embed.add_field(name="Version", value=gconf.VERSION),
    info_embed.add_field(name="Invite BB!", value="%s" % gconf.BOT_INVITE, inline=False)
    info_embed.add_field(name="Support server",
                         value="For help with the bot or a laugh join **https://discord.gg/P7DBDEC**!")
    await util.say(ctx.channel, embed=info_embed)


@commands.command(permission=Permission.DISCORD_USER, args_pattern=None)
async def prefix(ctx, **details):
    """
    ``@BattleBanana``prefix

    Tells you what the prefix is on a server.
    """

    server_prefix = dueserverconfig.server_cmd_key(ctx.server)
    await util.say(ctx.channel, "The prefix on **%s** is ``%s``" % (details.get("server_name_clean"), server_prefix))


@commands.command(permission=Permission.DISCORD_USER, args_pattern=None)
async def botstats(ctx, **_):
    """
    [CMD_KEY]stats
    
    BattleBanana's stats since the dawn of time!
    """

    game_stats = stats.get_stats()
    stats_embed = discord.Embed(title="BattleBanana's Statistics!", type="rich", color=gconf.DUE_COLOUR)

    stats_embed.description = ("The numbers and stuff of BattleBanana right now!\n"
                               + "The **worst** Discord bot since %s, %s!"
                               % (gconf.DUE_START_DATE.strftime("%d/%m/%Y"),
                                  repoze.timeago.get_elapsed(gconf.DUE_START_DATE)))

    # General
    stats_embed.add_field(name="General",
                          value=(e.MYINFO + " **%s** images served.\n"
                                 % util.format_number_precise(game_stats[Stat.IMAGES_SERVED])
                                 + e.DISCOIN + " **Đ%s** Discoin received.\n"
                                 % util.format_number_precise(game_stats[Stat.DISCOIN_RECEIVED])))
    # Game
    stats_embed.add_field(name="Game",
                          value=(e.QUESTER + " **%s** players.\n"
                                 % util.format_number_precise(game_stats[Stat.NEW_PLAYERS_JOINED])
                                 + e.QUEST + " **%s** quests given.\n"
                                 % util.format_number_precise(game_stats[Stat.QUESTS_GIVEN])
                                 + e.FIST + " **%s** quests attempted.\n"
                                 % util.format_number_precise(game_stats[Stat.QUESTS_ATTEMPTED])
                                 + e.LEVEL_UP + " **%s** level ups.\n"
                                 % util.format_number_precise(game_stats[Stat.PLAYERS_LEVELED])
                                 + e.BBT + " **%s** awarded.\n"
                                 % util.format_money(game_stats[Stat.MONEY_CREATED])
                                 + e.BBT_WITH_WINGS + " **%s** transferred between players."
                                 % util.format_money(game_stats[Stat.MONEY_TRANSFERRED])),
                          inline=False)
    # Sharding
    shards = util.shard_clients
    current_shard = util.get_client(ctx.server.id)
    stats_embed.add_field(name="Shard",
                          value=("You're connected to shard **%d/%d** (that is named %s).\n"
                                 % (current_shard.shard_id + 1, len(shards), current_shard.name)
                                 + "Current uptime (shard) is %s."
                                 % util.display_time(time.time() - current_shard.start_time, granularity=4)),
                          inline=False)

    await util.say(ctx.channel, embed=stats_embed)


@commands.command(permission=Permission.DISCORD_USER, args_pattern=None)
async def servers(ctx, **_):
    """
    [CMD_KEY]servers
    
    Shows the number of servers BattleBanana is chillin on.
    
    """

    server_count = util.get_server_count()
    await util.say(ctx.channel, "BattleBanana is active on **" + str(server_count) + " server"
                   + ("s" if server_count != 1 else "") + "**")


@commands.command(permission=Permission.SERVER_ADMIN, args_pattern="S", aliases=("setprefix",))
async def setcmdkey(ctx, new_key, **details):
    """
    [CMD_KEY]setcmdkey
    
    Sets the prefix for commands on your server.
    The default is '!'
    """
    if util.filter_string(new_key) != new_key:
        raise util.DueUtilException(ctx.channel, "You must set a valid command key!")

    if len(new_key) in (1, 2):
        dueserverconfig.server_cmd_key(ctx.server, new_key)
        await util.say(ctx.channel,
                       "Command prefix on **" + details["server_name_clean"] + "** set to ``" + new_key + "``!")
    else:
        raise util.DueUtilException(ctx.channel, "Command prefixes can only be one or two characters!")


@commands.command(permission=Permission.SERVER_ADMIN, args_pattern="S?")
async def shutup(ctx, *args, **details):
    """
    [CMD_KEY]shutup
    
    Mutes BattleBanana in the channel the command is used in.
    By default the ``[CMD_KEY]shutup`` will stop alerts (level ups, ect)
    using ``[CMD_KEY]shutup all`` will make BattleBanana ignore all commands
    from non-admins.
  
    """

    if len(args) == 0:
        mute_success = dueserverconfig.mute_channel(ctx.channel)
        if mute_success:
            await util.say(ctx.channel, (":mute: I won't send any alerts in this channel!\n"
                                         + "If you meant to disable commands too do ``" + details[
                                             "cmd_key"] + "shutup all``."))
        else:
            await util.say(ctx.channel, (":mute: I've already been set not to send alerts in this channel!\n"
                                         + "If you want to disable commands too do ``" + details["cmd_key"] 
                                         + "shutup all``.\n"
                                         + "To unmute me do ``" + details["cmd_key"] + "unshutup``."))
    else:
        mute_level = args[0].lower()
        if mute_level == "all":
            mute_success = dueserverconfig.mute_channel(ctx.channel, mute_all=True)
            if mute_success:
                await util.say(ctx.channel, ":mute: Disabled all commands in this channel for non-admins!")
            else:
                await util.say(ctx.channel, (":mute: Already mute af in this channel!.\n"
                                             + "To allow commands & alerts again do ``" + details[
                                                 "cmd_key"] + "unshutup``."))
        else:
            await util.say(ctx.channel, ":thinking: If you wanted to mute all the command is ``" + details[
                "cmd_key"] + "shutup all``.")


@commands.command(permission=Permission.REAL_SERVER_ADMIN, args_pattern="S?")
@commands.require_cnf(warning="The bot will leave your server and __**everything**__ will be reset!")
async def leave(ctx, **_):
    """
    [CMD_KEY]leave
    
    Makes BattleBanana leave your server cleanly.
    This will delete all quests & weapons created
    on your server.
    
    This command can only be run by real server admins
    (you must have manage server permissions).
    
    """

    bye_embed = discord.Embed(title="Goodbye!", color=gconf.DUE_COLOUR)
    bye_embed.set_image(url="http://i.imgur.com/N65P9gL.gif")
    await util.say(ctx.channel, embed=bye_embed)
    try:
        await util.get_client(ctx.server.id).leave_server(ctx.server)
    except:
        raise util.DueUtilException(ctx.channel, "Could not leave server!")


@commands.command(permission=Permission.SERVER_ADMIN, args_pattern=None)
async def unshutup(ctx, **_):
    """
    [CMD_KEY]unshutup

    Reverts ``[CMD_KEY]shutup`` or ``[CMD_KEY]shutup all``
    (allowing BattleBanana to give alerts and be used again).

    """
    if dueserverconfig.unmute_channel(ctx.channel):
        await util.say(ctx.channel,
                       ":speaker: Okay! I'll once more send alerts and listen for commands in this channel!")
    else:
        await util.say(ctx.channel, ":thinking: Okay... I'm unmuted but I was not muted anyway.")


@commands.command(permission=Permission.SERVER_ADMIN, args_pattern="S*")
async def whitelist(ctx, *args, **_):
    """
    [CMD_KEY]whitelist
    
    Choose what BattleBanana commands you want to allow in a channel.
    E.g. ``[CMD_KEY]whitelist help battle shop myinfo info``
    
    Normal users will not be able to use any other commands than the ones you
    choose.
    The whitelist does not effect server admins.
    
    To reset the whitelist run the command with no arguments.

    Note: Whitelisting a command like !info will also whitelist !myinfo
    (since !info is mapped to !myinfo)
    """

    if len(args) > 0:
        due_commands = events.command_event.command_list(aliases=True)
        whitelisted_commands = set(commands.replace_aliases([command.lower() for command in args]))
        if whitelisted_commands.issubset(due_commands):
            dueserverconfig.set_command_whitelist(ctx.channel, list(whitelisted_commands))
            await util.say(ctx.channel, (":notepad_spiral: Whitelist in this channel set to the following commands: ``"
                                         + ', '.join(whitelisted_commands) + "``"))
        else:
            incorrect_commands = whitelisted_commands.difference(due_commands)
            await util.say(ctx.channel, (":confounded: Cannot set whitelist! The following commands don't exist: ``"
                                         + ', '.join(incorrect_commands) + "``"))
    else:
        dueserverconfig.set_command_whitelist(ctx.channel, [])
        await util.say(ctx.channel, ":pencil: Command whitelist set back to all commands.")


@commands.command(permission=Permission.SERVER_ADMIN, args_pattern="S*")
async def blacklist(ctx, *args, **_):
    """
    [CMD_KEY]blacklist
    
    Choose what BattleBanana commands you want to ban in a channel.
    E.g. ``[CMD_KEY]blacklist acceptquest battleme sell``
    
    Normal users will only be able to use commands not in the blacklist.
    The blacklist does not effect server admins.
    
    To reset the blacklist run the command with no arguments.
    
    The blacklist is not independent from the whitelist.

    Note: Blacklisting a command like !info will also blacklist !myinfo
    (since !info is mapped to !myinfo)
    """

    if len(args) > 0:
        due_commands = events.command_event.command_list(aliases=True)
        blacklisted_commands = set(commands.replace_aliases([command.lower() for command in args]))
        if blacklisted_commands.issubset(due_commands):
            whitelisted_commands = list(set(due_commands).difference(blacklisted_commands))
            whitelisted_commands.append("is_blacklist")
            dueserverconfig.set_command_whitelist(ctx.channel, whitelisted_commands)
            await util.say(ctx.channel, (":notepad_spiral: Blacklist in this channel set to the following commands: ``"
                                         + ', '.join(blacklisted_commands) + "``"))
        else:
            incorrect_commands = blacklisted_commands.difference(due_commands)
            await util.say(ctx.channel, (":confounded: Cannot set blacklist! The following commands don't exist: ``"
                                         + ', '.join(incorrect_commands) + "``"))
    else:
        dueserverconfig.set_command_whitelist(ctx.channel, [])
        await util.say(ctx.channel, ":pencil: Command blacklist removed.")


@commands.command(permission=Permission.REAL_SERVER_ADMIN, args_pattern=None)
async def setuproles(ctx, **_):
    """
    [CMD_KEY]setuproles
    
    Creates any discord roles BattleBanana needs. These will have been made when
    BattleBanana joined your server but if you deleted any & need them you'll 
    want to run this command.
    
    """
    roles_made = await util.set_up_roles(ctx.server)
    roles_count = len(roles_made)
    if roles_count > 0:
        result = ":white_check_mark: Created **%d %s**!\n" % (roles_count, util.s_suffix("role", roles_count))
        for role in roles_made:
            result += "→ ``%s``\n" % role["name"]
        await util.say(ctx.channel, result)
    else:
        await util.say(ctx.channel, "No roles need to be created!")


async def optout_is_topdog_check(channel, player):
    topdog = player.is_top_dog()
    if topdog:
        await util.say(channel, (":dog: You cannot opt out while you're top dog!\n"
                                 + "Pass on the title before you leave us!"))
    return topdog


@commands.command(permission=Permission.DISCORD_USER, args_pattern=None)
async def optout(ctx, **details):
    """
    [CMD_KEY]optout

    Optout of BattleBanana.

    When you opt out:
        You don't get quests or exp.
        Other players can't use you in commands.
        You lose access to all "game" commands.

    Server admins (that opt out) still have access to admin commands.

    (This applies to all servers with BattleBanana)
    """

    player = details["author"]
    if player.is_playing():
        current_permission = permissions.get_special_permission(ctx.author)
        if await optout_is_topdog_check(ctx.channel, player):
            return
        if current_permission >= Permission.DUEUTIL_MOD:
            raise util.DueUtilException(ctx.channel, "You cannot optout everywhere and stay a BattleBanana mod or admin!")
        permissions.give_permission(ctx.author, Permission.DISCORD_USER)
        await util.say(ctx.channel, (":ok_hand: You've opted out of BattleBanana everywhere.\n"
                                     + "You won't get exp, quests, and other players can't use you in commands."))
    else:
        await util.say(ctx.channel, ("You've already opted out everywhere!\n"
                                     + "You can join the fun again with ``%soptin``." % details["cmd_key"]))


@commands.command(permission=Permission.DISCORD_USER, args_pattern=None)
async def optin(ctx, **details):
    """
    [CMD_KEY]optin

    Optin to BattleBanana.

    (This applies to all servers with BattleBanana)
    """

    player = details["author"]
    local_optout = not player.is_playing(ctx.server, local=True)
    # Already playing
    if player.is_playing():
        if not local_optout:
            await util.say(ctx.channel, "You've already opted in everywhere!")
        else:
            await util.say(ctx.channel, ("You've only opted out on this server!\n"
                                         + "To optin here do ``%soptinhere``" % details["cmd_key"]))
    else:
        permissions.give_permission(ctx.author, Permission.PLAYER)
        await util.say(ctx.channel, ("You've opted in everywhere"
                                     + (" (does not override your server level optout)" * local_optout) + "!\n"
                                     + "Glad to have you back."))


@commands.command(permission=Permission.DISCORD_USER, args_pattern=None)
async def optouthere(ctx, **details):
    """
    [CMD_KEY]optouthere

    Optout of BattleBanana on the server you run the command.
    This has the same effect as [CMD_KEY]optout but is local.
    """

    player = details["author"]

    if not player.is_playing():
        await util.say(ctx.channel, "You've already opted out everywhere!")
        return

    if player.is_playing(ctx.server, local=True):
        optout_role = util.get_role_by_name(ctx.server, gconf.OPTOUT_ROLE)
        if optout_role is None:
            await util.say(ctx.channel, ("There is no optout role on this server!\n"
                                         + "Ask an admin to run ``%ssetuproles``" % details["cmd_key"]))
        else:
            if await optout_is_topdog_check(ctx.channel, player):
                return
            client = util.get_client(ctx.server.id)
            await client.add_roles(ctx.author, optout_role)
            await util.say(ctx.channel, (":ok_hand: You've opted out of BattleBanana on this server!\n"
                                         + "You won't get exp, quests or be able to use commands here."))
    else:
        await util.say(ctx.channel, ("You've already opted out on this sever!\n"
                                     + "Join the fun over here do ``%soptinhere``" % details["cmd_key"]))


@commands.command(permission=Permission.DISCORD_USER, args_pattern=None)
async def optinhere(ctx, **details):
    """
    [CMD_KEY]optinhere

    Optin to BattleBanana on a server.
    """

    player = details["author"]
    globally_opted_out = not player.is_playing()

    optout_role = util.get_role_by_name(ctx.server, gconf.OPTOUT_ROLE)
    if optout_role is not None and not player.is_playing(ctx.server, local=True):
        client = util.get_client(ctx.server.id)
        await client.remove_roles(ctx.author, optout_role)
        await util.say(ctx.channel, ("You've opted in on this server!\n"
                                     + ("However this is overridden by your global optout.\n"
                                        + "To optin everywhere to ``%soptin``" % details["cmd_key"])
                                     * globally_opted_out))
    else:
        if globally_opted_out:
            await util.say(ctx.channel, ("You've opted out of BattleBanana everywhere!\n"
                                         + "To use BattleBanana do ``%soptin``" % details["cmd_key"]))
        else:
            await util.say(ctx.channel, "You've not opted out on this server.")

@commands.command(args_pattern=None)
async def currencies(ctx, **details):
    """
    [CMD_KEY]currencies
    
    Display every currencies currently available on Discoin
    """
    
    embed = discord.Embed(title=e.DISCOIN + " Current currencies!", type="rich", color=gconf.DUE_COLOUR)
    for id in discoin.CODES:
        currency = discoin.CODES[id]
        embed.add_field(name=id, value=currency['name'], inline=False)
    
    if len(embed.fields) == 0:
        embed.add_field(name="An error occured!", value="There was an error retrieving Discoin's currencies.")
    embed.set_footer(text="Visit https://dash.discoin.zws.im/#/currencies for exchange rate.")
    
    await util.say(ctx.channel, embed=embed)

@commands.ratelimit(cooldown=300, error="Your next transfer available is in **[COOLDOWN]**!", save=True)
@commands.command(args_pattern="CS", aliases=["convert"])
async def exchange(ctx, amount, currency, **details):
    """
    [CMD_KEY]exchange (amount) (currency)
    Exchange your BBT (BattleBanana Tokens) for other bot currencies!
    For more information go to: https://dash.discoin.zws.im/#/
    Note: Exchanges can take a few minutes to process!
    """

    player = details["author"]
    currency = currency.upper()

    if currency == discoin.CURRENCY_CODE:
        raise util.DueUtilException(ctx.channel, "There is no reason to exchange %s for %s!" % (discoin.CURRENCY_CODE, discoin.CURRENCY_CODE))
    if not currency in discoin.CODES:
        raise util.DueUtilException(ctx.channel, "Not a valid currency! Use `%scurrencies` to know which currency is available." % details['cmd_key'])
    if amount > discoin.MAX_TRANSACTION:
        raise util.DueUtilException(ctx.channel, "The amount you try to exchange exceeds the maximum %s transfer limit of %s." 
                                                                                                % (discoin.CURRENCY_CODE, discoin.MAX_TRANSACTION))

    if player.money - amount < 0:
        await util.say(ctx.channel, "You do not have **%s**!\n"
                        % util.format_number(amount, full_precision=True, money=True)
                       + "The maximum you can exchange is **%s**"
                       % util.format_number(player.money, full_precision=True, money=True))
        return

    try:
        response = await discoin.make_transaction(player.id, amount, currency)
    except Exception as discoin_error:
        util.logger.error("Discoin exchange failed %s", discoin_error)
        raise util.DueUtilException(ctx.channel, "Something went wrong at Discoin!")

    if response.get('statusCode'):
        try:
            raise util.DueUtilException(ctx.channel, "Something went wrong at Discoin! %s, %s" % (response['statusCode'], response['error']))
        except:
            raise util.DueUtilException(ctx.channel, "Something went wrong at Discoin! " + str(response))

    await awards.give_award(ctx.channel, player, "Discoin")
    player.money -= amount
    player.save()
    
    transaction = response
    receipt = discoin.DISCOINDASH + "/" + transaction['id'] + "/show"
    
    exchange_embed = discord.Embed(title=e.DISCOIN + " Exchange complete!", type="rich", color=gconf.DUE_COLOUR)
    exchange_embed.add_field(name=f"Exchange amount ({discoin.CURRENCY_CODE}):", value=util.format_number(amount, money=True, full_precision=True))
    exchange_embed.add_field(name="Result amount (%s):" % currency, value="$" + util.format_number_precise(transaction['payout']))
    exchange_embed.add_field(name="Receipt:", value=receipt, inline=False)
    exchange_embed.set_footer(text="Keep the receipt for if something goes wrong!")
    
    await util.say(ctx.channel, embed=exchange_embed)
    await util.say(gconf.other_configs['transactions'], ":grey_exclamation: Discoin transaction with receipt ``%s`` processed.\n" % transaction['id']
                        + "User: %s | Amount: %.2f | To: %s" % (player.id, amount, "%s (%s)" % (transaction['to']['name'], currency)))

@commands.command(args_pattern="S?", permission=Permission.DUEUTIL_ADMIN)
async def status(ctx, message=None, **details):
    """
    If message is none the status will be reset to the default one.

    This sets the status of all the shards to the one specified.
    """

    if message is None:
        count = len(util.shard_clients)
        for shard in util.shard_clients:
            shardID = shard.shard_id + 1
            game = discord.Game(name="dueutil.xyz | shard %d/%d" % (shardID, count))
            await shard.change_presence(game=game, afk=False)
    else:
        for shard in util.shard_clients:
            await shard.change_presence(game=discord.Game(name=message), afk=False)

    await util.say(ctx.channel, "All done!")
