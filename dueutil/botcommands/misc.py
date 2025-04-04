import json
import math
import os
import re
import shlex
import subprocess
import textwrap
import time
import traceback
from contextlib import redirect_stdout
from functools import partial
from io import StringIO
from unittest.mock import AsyncMock, patch

import discord
import objgraph

import dueutil.permissions
import generalconfig as gconf
from dueutil import commands, dbconn, events, loader, util
from dueutil.botcommands import fun
from dueutil.botcommands import util as bcutil
from dueutil.game import awards, customizations, emojis, game, leaderboards
from dueutil.game.configs import codes, dueserverconfig
from dueutil.game.helpers import imagehelper
from dueutil.permissions import Permission


@commands.command(permission=Permission.DISCORD_USER, args_pattern=None)
async def permissions(ctx, **_):
    """
    [CMD_KEY]permissions

    A check command for the permissions system.

    """

    permissions_report = ""
    for permission in dueutil.permissions.permissions:
        permissions_report += (
            "``"
            + permission.value[1]
            + "`` → "
            + (":white_check_mark:" if dueutil.permissions.has_permission(ctx.author, permission) else ":no_entry:")
            + "\n"
        )
    await util.reply(ctx, permissions_report)


@commands.command(args_pattern="RR", hidden=True)
async def add(ctx, first_number, second_number, **_):
    """
    [CMD_KEY]add (number) (number)

    One of the first test commands for Due2
    I keep it for sentimental reasons

    """

    result = first_number + second_number
    await util.reply(ctx, "Is " + str(result))


@commands.command()
async def wish(*_, **details):
    """
    [CMD_KEY]wish

    Does this increase the chance of a quest spawn?!

    Who knows?

    Me.

    """

    player = details["author"]
    player.quest_spawn_build_up += 0.005


@commands.command(permission=Permission.BANANA_MOD, args_pattern="SSSSIP?")
async def uploadbg(ctx, icon, name, description, url, price, submitter=None, **details):
    """
    [CMD_KEY]uploadbg (a bunch of args)

    Takes:
      icon
      name
      desc
      url
      price

    in that order.

    NOTE: Make event/shitty backgrounds (xmas) etc **free** (so we can delete them)

    """

    if not (util.char_is_emoji(icon) or util.is_server_emoji(ctx.guild, icon)):
        raise util.BattleBananaException(ctx.channel, "Icon must be emoji available on this guild!")

    if name != util.filter_string(name):
        raise util.BattleBananaException(ctx.channel, "Invalid background name!")
    name = re.sub(" +", " ", name)

    if name.lower() in customizations.backgrounds:
        raise util.BattleBananaException(ctx.channel, "That background name has already been used!")

    if price < 0:
        raise util.BattleBananaException(ctx.channel, "Cannot have a negative background price!")

    image = await imagehelper.load_image_url(url, raw=True)
    if image is None:
        raise util.BattleBananaException(ctx.channel, "Failed to load image!")

    if not imagehelper.has_dimensions(image, (256, 299)):
        raise util.BattleBananaException(ctx.channel, "Image must be ``256*299``!")

    image_name = name.lower().replace(" ", "_") + ".png"
    image.save("assets/backgrounds/" + image_name)

    try:
        backgrounds_file = open(customizations.BACKGROUND_PATH, "r+", encoding="utf-8")
    except IOError:
        backgrounds_file = open(customizations.BACKGROUND_PATH, "w+", encoding="utf-8")
    with backgrounds_file:
        try:
            backgrounds = json.load(backgrounds_file)
        except ValueError:
            backgrounds = {}
        backgrounds[name.lower()] = {
            "name": name,
            "icon": icon,
            "description": description,
            "image": image_name,
            "price": price,
        }
        backgrounds_file.seek(0)
        backgrounds_file.truncate()
        json.dump(backgrounds, backgrounds_file, indent=4)

    customizations.backgrounds._load_backgrounds()

    await util.reply(ctx, f":white_check_mark: Background **{name}** has been uploaded!")
    await util.duelogger.info(f"**{details['author'].name_clean}** added the background **{name}**")

    if submitter is not None:
        await awards.give_award(ctx.channel, submitter, "BgAccepted", "Background Accepted!")


@commands.command(permission=Permission.BANANA_MOD, args_pattern="S")
async def testbg(ctx, url, **_):
    """
    [CMD_KEY]testbg (image url)

    Tests if a background is the correct dimensions.

    """

    image = await imagehelper.load_image_url(url)
    if image is None:
        raise util.BattleBananaException(ctx.channel, "Failed to load image!")

    if not imagehelper.has_dimensions(image, (256, 299)):
        width, height = image.size
        await util.reply(
            ctx,
            (
                ":thumbsdown: **That does not meet the requirements!**\n"
                + "The tested image had the dimensions ``"
                + str(width)
                + "*"
                + str(height)
                + "``!\n"
                + "It should be ``256*299``!"
            ),
        )
    else:
        await util.reply(ctx, ":thumbsup: **That looks good to me!**\nP.s. I can't check for low quality images!")


@commands.command(permission=Permission.BANANA_MOD, args_pattern="S")
async def deletebg(ctx, background_to_delete, **details):
    """
    [CMD_KEY]deletebg (background name)

    Deletes a background.

    DO NOT DO THIS UNLESS THE BACKGROUND IS FREE

    """
    background_to_delete = background_to_delete.lower()
    if background_to_delete not in customizations.backgrounds:
        raise util.BattleBananaException(ctx.channel, "Background not found!")
    if background_to_delete == "default":
        raise util.BattleBananaException(ctx.channel, "Can't delete default background!")
    background = customizations.backgrounds[background_to_delete]

    try:
        with open(customizations.BACKGROUND_PATH, "r+", encoding="utf-8") as backgrounds_file:
            backgrounds = json.load(backgrounds_file)
            if background_to_delete not in backgrounds:
                raise util.BattleBananaException(ctx.channel, "You cannot delete this background!")
            del backgrounds[background_to_delete]
            backgrounds_file.seek(0)
            backgrounds_file.truncate()
            json.dump(backgrounds, backgrounds_file, indent=4)
    except IOError as io_error:
        raise util.BattleBananaException(
            ctx.channel, "Only uploaded backgrounds can be deleted and there are no uploaded backgrounds!"
        ) from io_error
    os.remove("assets/backgrounds/" + background["image"])

    customizations.backgrounds._load_backgrounds()

    await util.reply(ctx, ":wastebasket: Background **" + background.name_clean + "** has been deleted!")
    await util.duelogger.info(f"**{details['author'].name_clean}** deleted the background **{background.name_clean}**")


def cleanup_code(content):
    """Automatically removes code blocks from the code."""
    # remove ```py\n```
    if content.startswith("```") and content.endswith("```"):
        return "\n".join(content.split("\n")[1:-1])
    else:
        return content


def get_syntax_error(e):
    if e.text is None:
        return f"```py\n{e.__class__.__name__}: {e}\n```"
    return f'```py\n{e.text}{"^":>{e.offset}}\n{e.__class__.__name__}: {e}```'


@commands.command(permission=Permission.BANANA_OWNER, args_pattern="S")
@commands.imagecommand()
async def drawgraph(ctx, input, **details):
    """
    [CMD_KEY]drawgraph (1 or 2)
    Both options show all moneygenerated
    1 - Also shows all moneyremoved
    2 - Only shows moneyremoved from taxed sources (currently only sendcash)
    """
    if input not in ("1", "2"):
        await util.reply(ctx, "https://www.youtube.com/watch?v=2naim9F4010")
    else:
        await imagehelper.draw_graph(ctx, input)

@commands.command(permission=Permission.BANANA_OWNER, args_pattern="S", aliases=["eval"])
async def evaluate(ctx, body, **details):
    """
    [CMD_KEY]eval (code)

    For 1337 haxors only! Go away!

    Evaluates code
    """

    env = {
        "bot": util.clients[0],
        "ctx": ctx,
        "channel": ctx.channel,
        "author": ctx.author,
        "guild": ctx.guild,
        "player": details["author"],
    }

    env.update(globals())
    body = cleanup_code(body)
    stdout = StringIO()

    code_in_l = body.split("\n")
    code_in = ""
    line = 1
    for item in code_in_l:
        if item.startswith(" "):
            code_in += f"{line}... {item}\n"
        else:
            code_in += f"{line}>>> {item}\n"
        line += 1

    to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

    msg = await util.say(ctx.channel, "Evaluating")
    t1 = time.time()
    try:
        exec(to_compile, env)
    except Exception as e:
        return await msg.edit(content=f"```py\n{code_in}\n{e.__class__.__name__}: {e}\n```")
    func = env["func"]
    try:
        with redirect_stdout(stdout):
            ret = await func()
            t2 = time.time()
            timep = f"#{(round((t2 - t1) * 1000000)) / 1000} ms"
    except Exception:
        value = stdout.getvalue()
        t2 = time.time()
        timep = f"#{(round((t2 - t1) * 1000000)) / 1000} ms"
        await msg.edit(content=f"```py\n{code_in}\n{value}{traceback.format_exc()}\n{timep}\n```")
    else:
        value = stdout.getvalue()

        if ret is None:
            if value:
                await msg.edit(content=f"```py\n{code_in}\n{value}\n{timep}\n```")
            else:
                await msg.edit(content=f"```py\n{code_in}\n{timep}\n```")
        else:
            await msg.edit(content=f"```py\n{code_in}\n{value}{ret}\n{timep}\n```")


@commands.command(permission=Permission.BANANA_OWNER, args_pattern="S?", hidden=True)
async def oseval(ctx, cmd, **_):
    temp = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = temp.communicate()

    if temp.returncode == 0:
        await util.reply(ctx, f"```\n{stdout.encode('utf-8').decode('utf-8')}```")
    else:
        await util.reply(ctx, f"```\n{stderr.encode('utf-8').decode('utf-8')}```")


@commands.command(permission=Permission.BANANA_ADMIN, args_pattern="CC?B?", hidden=True)
async def generatecode(ctx, value, count=1, show=True, **details):
    """
    [CMD_KEY]generatecode ($$$) (amount)

    Generates the number of codes (amount) with price ($$$)
    """

    new_codes = codes.generate(value, count)

    if show:
        code_embed = discord.Embed(title="New codes!", type="rich", colour=gconf.DUE_COLOUR)
        code_embed.add_field(name="Codes:", value="\n".join([code.code for code in new_codes]))
        code_embed.set_footer(
            text=f"These codes can only be used once! Use {details['cmd_key']}redeem (code) to redeem the prize!"
        )
        await util.reply(ctx, embed=code_embed)


@commands.command(permission=Permission.BANANA_ADMIN, args_pattern="C?")
async def showcodes(ctx, page=1, **details):
    """
    [CMD_KEY]showcodes

    Shows remaining codes
    """

    paged_codes = codes.get_paged(page, 30)
    if paged_codes is None:
        raise util.BattleBananaException(ctx.channel, "Page not found")

    code_embed = discord.Embed(title="New codes!", type="rich", colour=gconf.DUE_COLOUR)
    code_embed.add_field(
        name="Codes:",
        value="\n".join([code.code for code in paged_codes]) if len(paged_codes) != 0 else "No code to display!",
    )
    code_embed.set_footer(
        text=f"These codes can only be used once! Use {details['cmd_key']}redeem (code) to redeem the prize!"
    )
    await util.reply(ctx, embed=code_embed)


@commands.command(args_pattern="S")
async def redeem(ctx, code, **details):
    """
    [CMD_KEY]redeem (code)

    Redeem your code
    """

    price = codes.redeem(code)
    if price is None:
        raise util.BattleBananaException(ctx.channel, "Code does not exist!")

    player = details["author"]
    player.money += price
    player.save()

    await util.reply(ctx, f"You successfully redeemed **{util.format_money(price)}** !!")


@commands.command(permission=Permission.BANANA_OWNER, args_pattern="PS")
async def sudo(ctx, victim, command, **_):
    """
    [CMD_KEY]sudo victim command

    Infect a victims mind to make them run any command you like!
    """

    try:
        ctx.author = await ctx.guild.fetch_member(victim.id)
        if ctx.author is None:
            # This may not fix all places where author is used.
            ctx.author = victim.to_member(ctx.guild)
            ctx.author.guild = ctx.guild  # Lie about what guild they're on.
        ctx.content = command
        await util.reply(ctx, f":smiling_imp: Sudoing **{victim.name_clean}**!")
        await events.command_event(ctx)
    except util.BattleBananaException as command_failed:
        raise util.BattleBananaException(ctx.channel, f'Sudo failed! "{command_failed.message}"')


@commands.command(permission=Permission.BANANA_ADMIN, args_pattern="PC")
async def setpermlevel(ctx, player, level, **_):
    if dueutil.permissions.get_special_permission(ctx.author) <= dueutil.permissions.get_special_permission(player):
        raise util.BattleBananaException(
            ctx.channel, "You cannot change the permissions for someone with a higher or equal permission level to you!"
        )

    member = player.to_member(ctx.guild)
    permission_index = level - 1
    permission_list = dueutil.permissions.permissions
    if permission_index < len(permission_list):
        permission = permission_list[permission_index]
        if not dueutil.permissions.has_permission(ctx.author, permission):
            raise util.BattleBananaException(ctx.channel, "You do not have permission to set this permission")

        dueutil.permissions.give_permission(member, permission)
        await util.reply(ctx, f"**{player.name_clean}** permission level set to ``{permission.value[1]}``.")
        if permission == Permission.BANANA_MOD:
            await awards.give_award(ctx.channel, player, "Mod", "Become an mod!")
            await util.duelogger.info(f"**{player.name_clean}** is now a BattleBanana mod! ({player.id})")
        elif "Mod" in player.awards:
            player.awards.remove("Mod")
        if permission == Permission.BANANA_ADMIN:
            await awards.give_award(ctx.channel, player, "Admin", "Become an admin!")
            await util.duelogger.info(f"**{player.name_clean}** is now a BattleBanana admin! ({player.id})")
        elif "Admin" in player.awards:
            player.awards.remove("Admin")
        if permission == Permission.BANANA_OWNER:
            await util.duelogger.info(f"**{player.name_clean}** is now a BattleBanana Owner! ({player.id})")
    else:
        raise util.BattleBananaException(ctx.channel, "Permission not found")


@commands.command(permission=Permission.BANANA_ADMIN, args_pattern="P", aliases=["giveban"])
async def ban(ctx, player, **_):
    if dueutil.permissions.get_special_permission(ctx.author) <= dueutil.permissions.get_special_permission(player):
        raise util.BattleBananaException(
            ctx.channel, "You cannot ban someone with a higher or equal permission level to you!"
        )

    dueutil.permissions.give_permission(player.to_member(ctx.guild), Permission.BANNED)
    await util.reply(ctx, emojis.MACBAN + " **" + player.name_clean + "** banned!")
    await util.duelogger.concern(f"**{player.name_clean}** has been banned! ({player.id})")


@commands.command(permission=Permission.BANANA_ADMIN, args_pattern="P", aliases=["pardon"])
async def unban(ctx, player, **_):
    member = player.to_member(ctx.guild)
    if not dueutil.permissions.has_special_permission(member, Permission.BANNED):
        await util.reply(ctx, f"**{player.name_clean}** is not banned...")
        return
    dueutil.permissions.give_permission(member, Permission.PLAYER)
    await util.reply(ctx, f":unicorn: **{player.name_clean}** has been unbanned!")
    await util.duelogger.info(f"**{player.name_clean}** has been unbanned ({player.id})")


@commands.command(permission=Permission.BANANA_ADMIN, args_pattern="C?", hidden=True)
async def bans(ctx, page=1, **_):
    bans_embed = discord.Embed(title="Ban list", type="rich", color=gconf.DUE_COLOUR)
    string = ""

    start = (page - 1) * 10
    for cursor in dbconn.conn()["permissions"].find({"permission": "banned"}, {"_id": 1}).skip(start).limit(10):
        string += f"<@{cursor['_id']}> ({cursor['_id']})\n"

    bans_embed.add_field(name="There is what I collected about bad people:", value=string or "Nobody is banned!")

    await util.reply(ctx, embed=bans_embed)


@commands.command(permission=Permission.BANANA_ADMIN, args_pattern="P")
async def toggledonor(ctx, player, **_):
    player.donor = not player.donor
    if player.donor:
        await util.reply(ctx, f"**{player.name_clean}** is now a donor!")
    else:
        await util.reply(ctx, f"**{player.name_clean}** is no longer donor")
    player.save()


@commands.command(permission=Permission.BANANA_OWNER, args_pattern=None)
async def reloadbot(ctx, **_):
    await util.reply(ctx, ":ferris_wheel: Reloading BattleBanana modules!")
    await util.duelogger.concern("BattleBanana Reloading!")
    loader.reload_modules(packages=loader.COMMANDS)
    raise util.DueReloadException(ctx.channel)


@commands.command(permission=Permission.BANANA_ADMIN, args_pattern="IP*")
async def givecash(ctx, amount, *players, **_):
    to_send = ""
    for player in players:
        player.money += amount
        amount_str = util.format_number(abs(amount), money=True, full_precision=True)
        if amount >= 0:
            to_send += f"Added ``{amount_str}`` to **{player.get_name_possession_clean()}** account!\n"
        else:
            to_send += f"Subtracted ``{amount_str}`` to **{player.get_name_possession_clean()}** account!\n"
        player.save()

    await util.reply(ctx, to_send)


@commands.command(permission=Permission.BANANA_ADMIN, args_pattern="PI")
async def setcash(ctx, player, amount, **_):
    player.money = amount
    amount_str = util.format_number(amount, money=True, full_precision=True)
    await util.reply(ctx, f"Set **{player.get_name_possession_clean()}** balance to ``{amount_str}``")


@commands.command(permission=Permission.BANANA_ADMIN, args_pattern="PI")
async def setprestige(ctx, player, prestige, **_):
    player.prestige_level = prestige
    player.save()
    await util.reply(ctx, f"Set prestige to **{prestige}** for **{player.get_name_possession_clean()}**")


@commands.command(permission=Permission.BANANA_ADMIN, args_pattern="PS")
async def giveaward(ctx, player, award_id, **_):
    if awards.get_award(award_id) is not None:
        await awards.give_award(ctx.channel, player, award_id)
    else:
        raise util.BattleBananaException(ctx.channel, "Award not found!")


@commands.command(permission=Permission.BANANA_ADMIN, args_pattern="PR")
async def giveexp(ctx, player, exp, **_):
    # (attack + strg + accy) * 100
    if exp < 0.1:
        raise util.BattleBananaException(ctx.channel, "The minimum exp that can be given is 0.1!")
    increase_stat = exp / 300
    player.progress(increase_stat, increase_stat, increase_stat, max_exp=math.inf, max_attr=math.inf)
    await util.reply(
        ctx, f"**{player.name_clean}** has been given **{util.format_number(exp, full_precision=True)}** exp!"
    )
    await game.check_for_level_up(ctx, player)
    player.save()


@commands.command(permission=Permission.BANANA_MOD, args_pattern=None)
async def updateleaderboard(ctx, **_):
    leaderboards.last_leaderboard_update = 0
    await leaderboards.update_leaderboards(ctx)
    await util.reply(ctx, ":ferris_wheel: Updating leaderboard!")


@commands.command(permission=Permission.BANANA_ADMIN, args_pattern=None)
async def updatebot(ctx, **_):
    """
    [CMD_KEY]updatebot

    Updates BattleBanana to the latest version.
    """

    update_result = await util.run_script("update_script.sh")
    stdout, stderr = await update_result.communicate()
    if stdout:
        update_result = stdout.decode("utf-8")
    elif stderr:
        update_result = stderr.decode("utf-8")
    else:
        update_result = "Something went wrong!"

    if len(update_result.strip()) == 0:
        update_result = "No output."
    update_embed = discord.Embed(title=":gear: Updating BattleBanana!", type="rich", color=gconf.DUE_COLOUR)
    update_embed.description = "Pulling lastest version from **github**!"
    update_embed.add_field(name="Changes", value="```" + update_result[:1018] + "```", inline=False)
    await util.reply(ctx, embed=update_embed)
    update_result = update_result.strip()
    if not (
        update_result.endswith("is up to date.")
        or update_result.endswith("up-to-date.")
        or update_result == "Something went wrong!"
    ):
        await util.clients[0].change_presence(
            activity=discord.Activity(name="BattleBanana update...", type=discord.ActivityType.watching),
            status=discord.Status.idle,
        )
        await util.duelogger.concern("BattleBanana updating!")
        await util.run_script("start.sh")


@commands.command(permission=Permission.BANANA_ADMIN, args_pattern=None)
async def stopbot(ctx, **_):
    await util.reply(ctx, ":wave: Stopping BattleBanana!")
    await util.duelogger.concern("BattleBanana shutting down!")
    await util.clients[0].change_presence(
        activity=discord.Activity(name="BattleBanana stop...", type=discord.ActivityType.watching),
        status=discord.Status.idle,
    )
    os._exit(0)


@commands.command(permission=Permission.BANANA_ADMIN, args_pattern=None)
async def restartbot(ctx, **_):
    await util.reply(ctx, ":ferris_wheel: Restarting BattleBanana!")
    await util.duelogger.concern("BattleBanana restarting!!")
    await util.clients[0].change_presence(
        activity=discord.Activity(name="BattleBanana restart...", type=discord.ActivityType.watching),
        status=discord.Status.idle,
    )
    await util.run_script("start.sh")


@commands.command(permission=Permission.BANANA_ADMIN, args_pattern=None)
async def meminfo(ctx, **_):
    mem_info = StringIO()
    objgraph.show_most_common_types(file=mem_info)
    await util.reply(ctx, f"```{mem_info.getvalue()}```")
    mem_info = StringIO()
    objgraph.show_growth(file=mem_info)
    await util.reply(ctx, f"```{mem_info.getvalue()}```")


@commands.command(args_pattern=None, aliases=["pong"])
async def ping(ctx, **_):
    """
    [CMD_KEY]ping

    Pong! Gives you the response time.
    """
    message = await util.reply(ctx, ":ping_pong:")
    t1 = time.time()
    dbconn.db.command("ping")
    t2 = time.time()
    dbms = round((t2 - t1) * 1000)

    apims = round((message.created_at - ctx.created_at).total_seconds() * 1000)

    embed = discord.Embed(title=":ping_pong: Pong!", type="rich", colour=gconf.DUE_COLOUR)
    embed.add_field(name="Bot Latency:", value=f"`{apims}ms`")
    try:
        latency = round(util.clients[0].latencies[util.get_shard_index(ctx.guild.id)][1] * 1000)

        embed.add_field(name="API Latency:", value=f"`{latency}ms`")
    except OverflowError:
        embed.add_field(name="API Latency:", value="``NaN``")

    embed.add_field(name="Database Latency:", value=f"``{dbms}ms``", inline=False)
    await message.edit(embed=embed)


@commands.command(args_pattern=None)
@commands.ratelimit(cooldown=5, error="Please wait to benchmark the bot again **[COOLDOWN]**!", save=True)
async def benchmark(ctx, **details):
    """
    [CMD_KEY]benchmark

    Runs a few commands to test time taken to do stuff, and outputs results in a nice pretty embed.
    [PERM]
    """

    message = await util.say(ctx.channel, "Results coming within a few seconds!")
    with (
        patch("dueutil.game.helpers.imagehelper.send_image", new_callable=AsyncMock),
        patch("dueutil.util.say", new_callable=AsyncMock),
        patch("dueutil.util.reply", new_callable=AsyncMock),
    ):
        ping = discord.Embed(title="Ping Stats!", type="rich", color=gconf.DUE_COLOUR)
        player = details["author"]
        image_funcs = [
            partial(imagehelper.stats_screen, player=player),
            partial(imagehelper.quests_screen, player=player, page=0),
            partial(imagehelper.battle_screen, player_one=player, player_two=player),
        ]

        text_funcs = [fun.topdog, bcutil.botstats, bcutil.help]
        times = []
        begin = time.time()
        for func in image_funcs:
            time1 = time.time()
            await func(ctx)
            times.append(util.display_time(int((time.time() - time1) * 1000), milliseconds=True))

        for func in text_funcs:
            time1 = time.time()
            await func(ctx, dueserverconfig.server_cmd_key(ctx.guild), "", [], **details)
            idk = util.display_time(int((time.time() - time1) * 1000), milliseconds=True)
            if idk is None or str(idk) == "":
                times.append("<1 ms")
            else:
                times.append(idk)

    total_elapsed = util.display_time(int((time.time() - begin) * 1000), milliseconds=True)
    ping.add_field(name="Total Time Taken for Every Command:", value="**" + total_elapsed + "**")
    icantnamethings = round((util.clients[0].latency * 1000), 2)
    ping.add_field(
        name="Pings by Image Command:",
        value=f"Myinfo: **{times[0]}**\nMyquests: **{times[1]}**\nBattle: **{times[2]}**",
    )
    ping.add_field(
        name="Pings by Text Command:",
        value=f"Topdog: **{times[3]}**\nBotstats: **{times[4]}**\nHelp: **{times[5]}**",
    )
    ping.add_field(name="Discord API Ping:", value="**" + str(icantnamethings) + "ms**")
    ping.set_footer(text="Times don't include the time spent while sending the image/text to Discord!")

    await message.edit(content=None, embed=ping)


@commands.command(args_pattern=None)
async def vote(ctx, **_):
    """
    Obtain up to ¤40'000 for voting
    """

    vote_embed = discord.Embed(title="Vote for your favorite Discord Bot", type="rich", colour=gconf.DUE_COLOUR)
    vote_embed.add_field(
        name="Vote:",
        value="[top.gg](https://top.gg/bot/464601463440801792/vote)\n"
        "[discordbotlist.com](https://discordbotlist.com/bots/battlebanana/upvote)\n"
        "[bots.ondiscord.xyz](https://bots.ondiscord.xyz/bots/464601463440801792)",
    )
    vote_embed.set_footer(text="You will receive your reward shortly after voting! (Up to 5 minutes)")

    await util.reply(ctx, embed=vote_embed)
