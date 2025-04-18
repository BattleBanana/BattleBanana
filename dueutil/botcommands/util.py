import asyncio
import json
import os
import sys
import time
from datetime import datetime
from itertools import chain

import discord
import psutil
import repoze.timeago

import generalconfig as gconf
from dueutil import blacklist as bl
from dueutil import commands, events, permissions, util

# Shorthand for emoji as I use gconf to hold emoji constants
from dueutil.game import awards, emojis, players, stats
from dueutil.game.configs import dueserverconfig
from dueutil.game.stats import Stat
from dueutil.permissions import Permission


@commands.command(permission=Permission.DISCORD_USER, args_pattern="S?", aliases=("helpme",))
async def help(ctx, *args, **details):
    """
    [CMD_KEY]help (command name or category)

    INCEPTION SOUND
    """

    help_logo = "https://cdn.discordapp.com/attachments/173443449863929856/275299953528537088/helo_458x458.jpg"

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
                    command_name = "Not found"
                    command_help = "That command was not found!"
                else:
                    # Stupid award reference
                    command_name = "dumbledore?!?"
                    command_help = "Some stupid *joke?* reference to old due!!!111"
                    help_embed.set_image(url="https://i.imgur.com/UrWhI9P.gif")
                    await awards.give_award(
                        ctx.channel, details["author"], "Daddy", "I have no memory of this award..."
                    )
            else:
                command_name = chosen_command.__name__
                alias_count = len(chosen_command.aliases)
                if chosen_command.__doc__ is not None:
                    command_help = chosen_command.__doc__.replace("[CMD_KEY]", server_key)
                else:
                    command_help = "Sorry there is no help for that command!"

            help_embed.description = "Showing help for **" + command_name + "**"
            help_embed.add_field(name=":gear: " + command_name, value=command_help)
            if alias_count > 0:
                help_embed.add_field(
                    name=":performing_arts: " + ("Alias" if alias_count == 1 else "Aliases"),
                    value=", ".join(chosen_command.aliases),
                    inline=False,
                )
        else:
            category = arg
            help_embed.description = "Showing ``" + category + "`` commands."

            commands_for_all = events.command_event.command_list(
                filter=lambda command: command.permission in (Permission.PLAYER, Permission.DISCORD_USER)
                and command.category == category
            )
            admin_commands = events.command_event.command_list(
                filter=lambda command: command.permission == Permission.SERVER_ADMIN and command.category == category
            )
            server_op_commands = events.command_event.command_list(
                filter=lambda command: command.permission == Permission.REAL_SERVER_ADMIN
                and command.category == category
            )

            if len(commands_for_all) > 0:
                help_embed.add_field(name="Commands for everyone", value=", ".join(commands_for_all), inline=False)
            if len(admin_commands) > 0:
                help_embed.add_field(name="Admins only", value=", ".join(admin_commands), inline=False)
            if len(server_op_commands) > 0:
                help_embed.add_field(name="Guild managers only", value=", ".join(server_op_commands), inline=False)
    else:
        help_embed.set_thumbnail(url=util.clients[0].user.display_avatar.url)

        help_embed.description = "Welcome to the help!\n Simply do " + server_key + "help (category) or (command name)."
        help_embed.add_field(name=":file_folder: Command categories", value=", ".join(categories))
        help_embed.add_field(
            name=emojis.THINKY_FONK + " Tips",
            value=(
                "If BattleBanana reacts to your command it means something is wrong!\n"
                + ":question: - Something is wrong with the command's syntax.\n"
                + ":x: - You don't have the required permissions to use the command."
            ),
        )
        help_embed.add_field(
            name=":link: Links",
            value=(
                f"**Invite me: {gconf.BOT_INVITE}**\n"
                + "BattleBanana guide: https://battlebanana.xyz/howto\n"
                + "Need more help?: https://discord.gg/P7DBDEC\n"
                + "Support BattleBanana: https://patreon.com/developeranonymous"
            ),
            inline=False,
        )
        help_embed.set_footer(
            text="To use admin commands you must have the manage guild permission or the 'Banana Commander' role."
        )

    await util.reply(ctx, embed=help_embed)


@commands.command(permission=Permission.DISCORD_USER, args_pattern=None)
async def invite(ctx, **_):
    """
    [CMD_KEY]invite

    Display BattleBanana invite link & Support guild.
    """

    invite_embed = discord.Embed(title="BattleBanana's invites", type="rich", color=gconf.DUE_COLOUR)
    invite_embed.description = "Here are 2 important links about me! :smiley:"
    invite_embed.add_field(name="Invite me:", value=f"[Here]({gconf.BOT_INVITE})", inline=True)
    invite_embed.add_field(name="Support server:", value="[Here](https://discord.gg/P7DBDEC)", inline=True)
    await util.reply(ctx, embed=invite_embed)


@commands.command(permission=Permission.DISCORD_USER, args_pattern=None)
async def donate(ctx, **_):
    """
    [CMD_KEY]donate

    This command show where you can donate to BattleBanana.

    All money received is used to pay BattleBanana's cost.
    """

    donation_embed = discord.Embed(title="Donate", type="rich", color=gconf.DUE_COLOUR)
    donation_embed.add_field(name="Patreon", value="[Here](https://patreon.com/developeranonymous)", inline=True)

    await util.reply(ctx, embed=donation_embed)


@commands.command(permission=Permission.DISCORD_USER, args_pattern=None)
async def botinfo(ctx, **_):
    """
    [CMD_KEY]botinfo

    General information about BattleBanana.
    """

    info_embed = discord.Embed(title="BattleBanana's Information", type="rich", color=gconf.DUE_COLOUR)
    info_embed.description = "BattleBanana is customizable bot to add fun commands, quests and battles to your guild."
    info_embed.add_field(name="Owner", value="[DeveloperAnonymous#9830](https://battlebanana.xyz/)")
    info_embed.add_field(
        name="Framework",
        value=f"[discord.py {discord.__version__} :two_hearts:](https://discordpy.readthedocs.io/en/latest/)",
    )
    info_embed.add_field(name="Version", value=gconf.VERSION)
    info_embed.add_field(name="Invite BB!", value=gconf.BOT_INVITE, inline=False)
    info_embed.add_field(
        name="Support server", value="For help with the bot or a laugh join **https://discord.gg/P7DBDEC**!"
    )
    await util.reply(ctx, embed=info_embed)


@commands.command(permission=Permission.DISCORD_USER, args_pattern=None)
async def prefix(ctx, **details):
    """
    ``@BattleBanana``prefix

    Tells you what the prefix is on a guild.
    """

    server_prefix = dueserverconfig.server_cmd_key(ctx.guild)
    await util.reply(ctx, f"The prefix on **{details["server_name_clean"]}** is ``{server_prefix}``")


@commands.command(permission=Permission.DISCORD_USER, args_pattern=None)
async def botstats(ctx: discord.Message, **_):
    """
    [CMD_KEY]botstats

    BattleBanana's stats since the dawn of time!
    """

    game_stats = stats.get_stats()
    stats_embed = discord.Embed(title="BattleBanana's Statistics!", type="rich", color=gconf.DUE_COLOUR)

    created_at = datetime.fromtimestamp(ctx.guild.me.created_at.timestamp())
    stats_embed.description = (
        "The numbers and stuff of BattleBanana right now!\nThe **worst** Discord bot since"
        + f" {created_at.strftime("%d/%m/%Y")}, {repoze.timeago.get_elapsed(created_at)}!"
    )

    # General
    commands_used = game_stats[Stat.COMMANDS_USED]
    discoin_received = game_stats[Stat.DISCOIN_RECEIVED]
    images_served = game_stats[Stat.IMAGES_SERVED]

    stats_embed.add_field(
        name="General",
        value=(
            f"{emojis.MYINFO} **{util.format_number_precise(images_served)}** images served.\n"
            + f"{emojis.DISCOIN} **Đ{util.format_number_precise(discoin_received)}** Discoin received.\n"
            + f"{emojis.CHANNEL} **%s** commands used.\n" % util.format_number_precise(commands_used)
        ),
    )

    # Game
    new_players = game_stats[Stat.NEW_PLAYERS_JOINED]
    quests_given = game_stats[Stat.QUESTS_GIVEN]
    quests_attempted = game_stats[Stat.QUESTS_ATTEMPTED]
    players_leveled = game_stats[Stat.PLAYERS_LEVELED]
    money_created = game_stats[Stat.MONEY_CREATED]
    money_transferred = game_stats[Stat.MONEY_TRANSFERRED]
    money_taxed = game_stats[Stat.MONEY_TAXED]

    stats_embed.add_field(
        name="Game",
        value=(
            f"{emojis.QUESTER} **{util.format_number_precise(new_players)}** players.\n"
            + f"{emojis.QUEST} **{util.format_number_precise(quests_given)}** quests given.\n"
            + f"{emojis.FIST} **{util.format_number_precise(quests_attempted)}** quests attempted.\n"
            + f"{emojis.LEVEL_UP} **{util.format_number_precise(players_leveled)}** level ups.\n"
            + f"{emojis.BBT} **{util.format_money(money_created)}** awarded.\n"
            + f"{emojis.BBT_WITH_WINGS} **{util.format_money(money_transferred)}** transferred between players.\n"
            + f"{emojis.RECEIPT} **{util.format_money(money_taxed)}** taxed."
        ),
        inline=False,
    )

    # Sharding
    client = util.clients[0]
    current_shard = util.get_shard_index(ctx.guild.id)
    stats_embed.add_field(
        name="Shard",
        value=(
            f"You're connected to shard **{current_shard + 1}/{client.shard_count}** "
            + f"(that is named {gconf.shard_names[current_shard]}).\n"
            + f"Current uptime is {util.display_time(time.time() - client.start_time, granularity=4)}."
        ),
        inline=False,
    )

    # Server infos
    process = psutil.Process(os.getpid())
    os_platform = sys.platform
    match os_platform:
        case "linux":
            os_platform = "Linux"
        case "win32":
            os_platform = "Windows"
        case "darwin":
            os_platform = "macOS"
        case _:
            os_platform = "Unknown"

    cpu_usage = round(process.cpu_percent(), 2)
    cpu_model = util.get_cpu_info()

    gb_divisor = 1024 * 1024 * 1024
    used_ram = round(process.memory_info().rss / gb_divisor, 2)
    total_ram = round(psutil.virtual_memory().total / gb_divisor, 2)
    percent_ram = round(process.memory_percent(), 2)

    stats_embed.add_field(
        name="System infos",
        value=(
            f"{emojis.OS} **{os_platform}**\n"
            f"{emojis.CPU} **{cpu_model} ({cpu_usage}% usage)**\n"
            f"{emojis.RAM} **{used_ram}/{total_ram} GB ({percent_ram}%)**"
        ),
        inline=False,
    )

    await util.reply(ctx, embed=stats_embed)


@commands.command(permission=Permission.DISCORD_USER, args_pattern=None)
async def servers(ctx, **_):
    """
    [CMD_KEY]servers

    Shows the number of servers BattleBanana is chillin on.

    """

    server_count = util.get_server_count()
    await util.reply(
        ctx, "BattleBanana is active on **" + str(server_count) + " guild" + ("s" if server_count != 1 else "") + "**"
    )


@commands.command(permission=Permission.SERVER_ADMIN, args_pattern="S", aliases=("setprefix",))
async def setcmdkey(ctx, new_key, **details):
    """
    [CMD_KEY]setcmdkey

    Sets the prefix for commands on your guild.
    The default is '!'
    """
    if util.filter_string(new_key) != new_key:
        raise util.BattleBananaException(ctx.channel, "You must set a valid command key!")

    if len(new_key) in (1, 2):
        dueserverconfig.server_cmd_key(ctx.guild, new_key)
        await util.reply(ctx, "Command prefix on **" + details["server_name_clean"] + "** set to ``" + new_key + "``!")
    else:
        raise util.BattleBananaException(ctx.channel, "Command prefixes can only be one or two characters!")


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
            await util.reply(
                ctx,
                (
                    ":mute: I won't send any alerts in this channel!\n"
                    + "If you meant to disable commands too do ``"
                    + details["cmd_key"]
                    + "shutup all``."
                ),
            )
        else:
            await util.reply(
                ctx,
                (
                    ":mute: I've already been set not to send alerts in this channel!\n"
                    + "If you want to disable commands too do ``"
                    + details["cmd_key"]
                    + "shutup all``.\n"
                    + "To unmute me do ``"
                    + details["cmd_key"]
                    + "unshutup``."
                ),
            )
    else:
        mute_level = args[0].lower()
        if mute_level == "all":
            mute_success = dueserverconfig.mute_channel(ctx.channel, mute_all=True)
            if mute_success:
                await util.reply(ctx, ":mute: Disabled all commands in this channel for non-admins!")
            else:
                await util.reply(
                    ctx,
                    (
                        ":mute: Already mute af in this channel!.\n"
                        + "To allow commands & alerts again do ``"
                        + details["cmd_key"]
                        + "unshutup``."
                    ),
                )
        else:
            await util.reply(
                ctx, ":thinking: If you wanted to mute all the command is ``" + details["cmd_key"] + "shutup all``."
            )


@commands.command(permission=Permission.REAL_SERVER_ADMIN, args_pattern="S?")
@commands.require_cnf(warning="The bot will leave your guild and __**everything**__ will be reset!")
async def leave(ctx, **_):
    """
    [CMD_KEY]leave

    Makes BattleBanana leave your guild cleanly.
    This will delete all quests & weapons created
    on your guild.

    This command can only be run by real guild admins
    (you must have manage guild permissions).

    """

    bye_embed = discord.Embed(title="Goodbye!", color=gconf.DUE_COLOUR)
    bye_embed.set_image(url="https://i.imgur.com/N65P9gL.gif")
    await util.reply(ctx, embed=bye_embed)
    try:
        await ctx.guild.leave()
    except discord.HTTPException as e:
        raise util.BattleBananaException(ctx.channel, f"Could not leave guild! ({e.text})")


@commands.command(permission=Permission.SERVER_ADMIN, args_pattern=None)
async def unshutup(ctx, **_):
    """
    [CMD_KEY]unshutup

    Reverts ``[CMD_KEY]shutup`` or ``[CMD_KEY]shutup all``
    (allowing BattleBanana to give alerts and be used again).

    """
    if dueserverconfig.unmute_channel(ctx.channel):
        await util.reply(ctx, ":speaker: Okay! I'll once more send alerts and listen for commands in this channel!")
    else:
        await util.reply(ctx, ":thinking: Okay... I'm unmuted but I was not muted anyway.")


@commands.command(permission=Permission.SERVER_ADMIN, args_pattern="S*")
async def whitelist(ctx, *args, **_):
    """
    [CMD_KEY]whitelist

    Choose what BattleBanana commands you want to allow in a channel.
    E.g. ``[CMD_KEY]whitelist help battle shop myinfo info``

    Normal users will not be able to use any other commands than the ones you
    choose.
    The whitelist does not effect guild admins.

    To reset the whitelist run the command with no arguments.

    Note: Whitelisting a command like !info will also whitelist !myinfo
    (since !info is mapped to !myinfo)
    """

    if len(args) > 0:
        due_commands = events.command_event.command_list(aliases=True)
        whitelisted_commands = set(commands.replace_aliases([command.lower() for command in args]))
        if whitelisted_commands.issubset(due_commands):
            dueserverconfig.set_command_whitelist(ctx.channel, list(whitelisted_commands))
            await util.reply(
                ctx,
                (
                    ":notepad_spiral: Whitelist in this channel set to the following commands: ``"
                    + ", ".join(whitelisted_commands)
                    + "``"
                ),
            )
        else:
            incorrect_commands = whitelisted_commands.difference(due_commands)
            await util.reply(
                ctx,
                (
                    ":confounded: Cannot set whitelist! The following commands don't exist: ``"
                    + ", ".join(incorrect_commands)
                    + "``"
                ),
            )
    else:
        dueserverconfig.set_command_whitelist(ctx.channel, [])
        await util.reply(ctx, ":pencil: Command whitelist set back to all commands.")


@commands.command(permission=Permission.SERVER_ADMIN, args_pattern="S*")
async def blacklist(ctx, *args, **_):
    """
    [CMD_KEY]blacklist

    Choose what BattleBanana commands you want to ban in a channel.
    E.g. ``[CMD_KEY]blacklist acceptquest battleme sell``

    Normal users will only be able to use commands not in the blacklist.
    The blacklist does not effect guild admins.

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
            await util.reply(
                ctx,
                (
                    ":notepad_spiral: Blacklist in this channel set to the following commands: ``"
                    + ", ".join(blacklisted_commands)
                    + "``"
                ),
            )
        else:
            incorrect_commands = blacklisted_commands.difference(due_commands)
            await util.reply(
                ctx,
                (
                    ":confounded: Cannot set blacklist! The following commands don't exist: ``"
                    + ", ".join(incorrect_commands)
                    + "``"
                ),
            )
    else:
        dueserverconfig.set_command_whitelist(ctx.channel, [])
        await util.reply(ctx, ":pencil: Command blacklist removed.")


@commands.command(permission=Permission.REAL_SERVER_ADMIN, args_pattern=None)
async def setuproles(ctx, **_):
    """
    [CMD_KEY]setuproles

    Creates any discord roles BattleBanana needs. These will have been made when
    BattleBanana joined your guild but if you deleted any & need them you'll
    want to run this command.

    """
    roles_made = await util.set_up_roles(ctx.guild)
    roles_count = len(roles_made)
    if roles_count > 0:
        result = f":white_check_mark: Created **{roles_count} {util.s_suffix('role', roles_count)}**!\n"
        for role in roles_made:
            result += f"→ ``{role['name']}``\n"
        await util.reply(ctx, result)
    else:
        await util.reply(ctx, "No roles need to be created!")


async def optout_is_topdog_check(channel, player):
    topdog = player.is_top_dog()
    if topdog:
        await util.say(
            channel, (":dog: You cannot opt out while you're top dog!\n" + "Pass on the title before you leave us!")
        )
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

    Guild admins (that opt out) still have access to admin commands.

    (This applies to all servers with BattleBanana)
    """

    player = details["author"]
    if player.is_playing():
        current_permission = permissions.get_special_permission(ctx.author)
        if await optout_is_topdog_check(ctx.channel, player):
            return
        if current_permission >= Permission.BANANA_MOD:
            raise util.BattleBananaException(
                ctx.channel, "You cannot optout everywhere and stay a BattleBanana mod or admin!"
            )
        permissions.give_permission(ctx.author, Permission.DISCORD_USER)
        await util.reply(
            ctx,
            (
                ":ok_hand: You've opted out of BattleBanana everywhere.\n"
                + "You won't get exp, quests, and other players can't use you in commands."
            ),
        )
    else:
        await util.reply(
            ctx,
            (
                "You've already opted out everywhere!\n"
                + f"You can join the fun again with ``{details['cmd_key']}optin``."
            ),
        )


@commands.command(permission=Permission.DISCORD_USER, args_pattern=None)
async def optin(ctx, **details):
    """
    [CMD_KEY]optin

    Optin to BattleBanana.

    (This applies to all servers with BattleBanana)
    """

    player = details["author"]
    if player is None:
        return await util.reply(ctx, f"Please run `{details['cmd_key']}createaccount` if you want to use BattleBanana.")

    local_optout = not player.is_playing(ctx.author, local=True)
    # Already playing
    if player.is_playing():
        if not local_optout:
            await util.reply(ctx, "You've already opted in everywhere!")
        else:
            await util.reply(
                ctx,
                f"You've only opted out on this guild!\nTo optin here do ``{details['cmd_key']}optinhere``",
            )
    else:
        permissions.give_permission(ctx.author, Permission.PLAYER)
        await util.reply(
            ctx,
            (
                "You've opted in everywhere"
                + (" (does not override your guild level optout)" * local_optout)
                + "!\n"
                + "Glad to have you back."
            ),
        )


@commands.command(permission=Permission.DISCORD_USER, args_pattern=None)
async def optouthere(ctx, **details):
    """
    [CMD_KEY]optouthere

    Optout of BattleBanana on the guild you run the command.
    This has the same effect as [CMD_KEY]optout but is local.
    """

    player = details["author"]

    if not player.is_playing():
        await util.reply(ctx, "You've already opted out everywhere!")
        return

    if player.is_playing(ctx.author, local=True):
        optout_role = util.get_role_by_name(ctx.guild, gconf.OPTOUT_ROLE)
        if optout_role is None:
            await util.reply(
                ctx,
                (
                    "There is no optout role on this guild!\n"
                    + f"Ask an admin to run ``{details['cmd_key']}setuproles``"
                ),
            )
        else:
            if await optout_is_topdog_check(ctx.channel, player):
                return
            await ctx.author.add_roles(optout_role)
            await util.reply(
                ctx,
                (
                    ":ok_hand: You've opted out of BattleBanana on this guild!\n"
                    + "You won't get exp, quests or be able to use commands here."
                ),
            )
    else:
        await util.reply(
            ctx,
            (
                "You've already opted out on this sever!\n"
                + f"Join the fun over here do ``{details['cmd_key']}optinhere``"
            ),
        )


@commands.command(permission=Permission.DISCORD_USER, args_pattern=None)
async def optinhere(ctx, **details):
    """
    [CMD_KEY]optinhere

    Optin to BattleBanana on a guild.
    """

    player = details["author"]
    if player is None:
        return await util.reply(ctx, f"Please run `{details['cmd_key']}createaccount` if you want to use BattleBanana.")

    globally_opted_out = not player.is_playing()

    optout_role = util.get_role_by_name(ctx.guild, gconf.OPTOUT_ROLE)
    if optout_role is not None and not player.is_playing(ctx.author, local=True):
        await ctx.author.remove_roles(optout_role)
        await util.reply(
            ctx,
            (
                "You've opted in on this guild!\n"
                + (
                    "However this is overridden by your global optout.\n"
                    + f"To optin everywhere to ``{details['cmd_key']}optin``"
                )
                * globally_opted_out
            ),
        )
    else:
        if globally_opted_out:
            await util.reply(
                ctx,
                (
                    "You've opted out of BattleBanana everywhere!\n"
                    + f"To use BattleBanana do ``{details['cmd_key']}optin``"
                ),
            )
        else:
            await util.reply(ctx, "You've not opted out on this guild.")


@commands.command(args_pattern=None)
async def currencies(ctx, **_):
    """
    [CMD_KEY]currencies

    Display every currencies currently available on Discoin
    """
    raise util.BattleBananaException(ctx.channel, "Discoin is currently offline.")


@commands.command(args_pattern="CS", aliases=["convert"])
async def exchange(ctx, amount, currency, **details):
    """
    [CMD_KEY]exchange (amount) (currency)

    Exchange your BBT (BattleBanana Tokens) for other bot currencies!
    For more information go to: https://dash.discoin.zws.im/#/

    Note: Exchanges can take a few minutes to process!
    """
    raise util.BattleBananaException(ctx.channel, "Discoin is currently offline.")


@commands.command(args_pattern="S?", permission=Permission.BANANA_ADMIN, hidden=True)
async def status(ctx, message=None, **_):
    """
    If message is none the status will be reset to the default one.

    This sets the status of all the shards to the one specified.
    """
    client: discord.AutoShardedClient = util.clients[0]
    if message is None:
        count = client.shard_count
        for shard_id in range(0, count):
            game = discord.Activity(
                name=f"battlebanana.xyz | shard {shard_id}/{count}", type=discord.ActivityType.watching
            )
            await client.change_presence(activity=game, shard_id=shard_id)
    else:
        await client.change_presence(activity=discord.Activity(name=message, type=discord.ActivityType.watching))

    await util.reply(ctx, "All done!")


@commands.command(args_pattern="S?", aliases=["transdata", "td"])
@commands.require_cnf(
    warning="Transferring your data will override your current data, assuming you have any, on TheelUtil!"
)
@commands.ratelimit(cooldown=604800, error="You can transfer your data again **[COOLDOWN]**!", save=True)
async def transferdata(ctx, **details):
    _, writer = await asyncio.open_connection(
        gconf.other_configs["connectionIP"], gconf.other_configs["connectionPort"]
    )
    attributes_to_remove = [
        "inventory",
        "quests",
        "equipped",
        "received_wagers",
        "awards",
        "team",
        "donor",
        "quest_spawn_build_up",
    ]
    message = dict(details["author"])
    for attr in attributes_to_remove:
        try:
            message.pop(attr)
        except KeyError:
            continue
    message = json.dumps(message)
    writer.write(message.encode())
    await util.reply(ctx, "Your data has been sent! It should appear on the other bot within a few seconds!")
    writer.close()
    await writer.wait_closed()


async def get_stuff(self):
    for attr in chain.from_iterable(getattr(cls, "__slots__", []) for cls in self.__class__.__mro__):
        try:
            yield attr
        except AttributeError:
            continue


@commands.command(permission=Permission.BANANA_OWNER, args_pattern=None, hidden=True)
async def startsocketserver(ctx, **_):
    """
    [CMD_KEY]sss

    Only in case the server doesn't boot up in run.py
    """
    global async_server
    async_server = await asyncio.start_server(players.handle_client, "", gconf.other_configs["connectionPort"])
    server_port = async_server.sockets[0].getsockname()[
        1
    ]  # get port that the server is on, to confirm it started on 4000
    await util.say(ctx.channel, f"Listening on port {server_port}!")


@commands.command(permission=Permission.BANANA_OWNER, args_pattern="PS?", aliases=["cldr"], hidden=True)
async def cooldownreset(ctx, player, cooldown=None, **_):
    if cooldown is None:
        player.command_rate_limits = {}
    else:
        if cooldown not in player.command_rate_limits:
            raise util.BattleBananaException(ctx.channel, "Invalid cooldown")
        player.command_rate_limits.pop(cooldown)

    player.save()
    await util.say(ctx.channel, "The target player's cooldowns have been reset!")


@commands.command(permission=Permission.BANANA_OWNER, args_pattern="PS?", aliases=["scld"], hidden=True)
async def showcooldown(ctx, player, **_):
    await util.say(ctx.channel, [cooldown for cooldown in player.command_rate_limits])


@commands.command(permission=Permission.BANANA_ADMIN, args_pattern="MS", hidden=True)
async def block(ctx, id, reason="No reason specified", **_):
    """
    [CMD_KEY]block (member id)

    Blocks the member from the on_message event.
    """
    if bl.find(id):
        raise util.BattleBananaException(ctx.channel, "This member is already blacklisted!")

    bl.add(id, reason)
    await util.reply(ctx, "The user has been blacklisted!")


@commands.command(permission=Permission.BANANA_ADMIN, args_pattern="M", hidden=True)
async def unblock(ctx, id, **_):
    """
    [CMD_KEY]unblock (member id)

    Unblock the member from the on_message event.
    """
    if not bl.find(id):
        raise util.BattleBananaException(ctx.channel, "This member is not blacklisted!")

    bl.remove(id)
    await util.reply(ctx, "The user has been unblacklisted!")
