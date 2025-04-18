import random
import time

import discord

import generalconfig as gconf
from dueutil import commands, util
from dueutil.game import awards, battles, emojis, game, players, quests, stats, weapons
from dueutil.game.helpers import imagehelper, misc
from dueutil.permissions import Permission


@commands.command(permission=Permission.BANANA_MOD, args_pattern="S?P?C?", hidden=True)
async def spawnquest(ctx, *args, **details):
    """
    [CMD_KEY]spawnquest (name) (@user) (level)

    A command for TESTING only please (awais) do not abuse this power.
    All arguments are optional however the final three must all be entered
    to use them.
    """

    player = details["author"]
    if len(args) == 0:
        if quests.has_quests(ctx.channel):
            quest = quests.get_random_quest_in_channel(ctx.channel)
        else:
            raise util.BattleBananaException(ctx.channel, "Could not find a quest in this channel to spawn!")
    else:
        if len(args) >= 2:
            player = args[1]
        quest_name = args[0].lower()
        quest = quests.get_quest_from_id(f"{ctx.guild.id}/{quest_name}")
    try:
        active_quest = await quests.ActiveQuest.create(quest.q_id, player)
        if len(args) == 3:
            active_quest.level = args[2]
            await active_quest._calculate_stats()
        player.save()
        await util.reply(
            ctx, ":cloud_lightning: Spawned **" + quest.name_clean + "** [Level " + str(active_quest.level) + "]"
        )
    except Exception as error:
        raise util.BattleBananaException(ctx.channel, "Failed to spawn quest!") from error


@commands.command(args_pattern="C", aliases=["qi"])
@commands.imagecommand()
async def questinfo(ctx, quest_index, **details):
    """
    [CMD_KEY]questinfo index

    Shows a simple stats page for the quest
    """

    player = details["author"]
    quest_index -= 1
    if 0 <= quest_index < len(player.quests):
        await imagehelper.quest_screen(ctx, player.quests[quest_index])
    else:
        raise util.BattleBananaException(ctx.channel, quests.QUEST_NOT_FOUND)


@commands.command(args_pattern="C?", aliases=["mq"])
@commands.imagecommand()
async def myquests(ctx, page=1, **details):
    """
    [CMD_KEY]myquests

    Shows the list of active quests you have pending.
    """

    player = details["author"]
    page -= 1
    # Always show page 1 (0)
    if page != 0 and page * 5 >= len(player.quests):
        raise util.BattleBananaException(ctx.channel, "Page not found")
    await imagehelper.quests_screen(ctx, player, page)


@commands.command(args_pattern="C", aliases=["aq"])
@commands.imagecommand()
async def acceptquest(ctx, quest_index, **details):
    """
    [CMD_KEY]acceptquest (quest number)

    You know what to do. Spam ``[CMD_KEY]acceptquest 1``!
    """

    player = details["author"]
    quest_index -= 1
    if quest_index >= len(player.quests):
        raise util.BattleBananaException(ctx.channel, quests.QUEST_NOT_FOUND)
    if player.money - player.quests[quest_index].money // 2 < 0:
        raise util.BattleBananaException(ctx.channel, "You can't afford the risk!")
    if player.quests_completed_today >= quests.MAX_DAILY_QUESTS:
        raise util.BattleBananaException(
            ctx.channel, "You can't do more than " + str(quests.MAX_DAILY_QUESTS) + " quests a day!"
        )

    quest = player.quests.pop(quest_index)
    battle_log = battles.get_battle_log(player_one=player, player_two=quest, p2_prefix="the ")
    battle_embed = battle_log.embed
    turns = battle_log.turn_count
    winner = battle_log.winner
    stats.increment_stat(stats.Stat.QUESTS_ATTEMPTED)
    # Not really an average (but w/e)
    average_quest_battle_turns = player.misc_stats["average_quest_battle_turns"] = (
        player.misc_stats["average_quest_battle_turns"] + turns
    ) / 2
    if winner == quest:
        quest_results = (
            ":skull: **"
            + player.name_clean
            + "** lost to the **"
            + quest.name_clean
            + "** and dropped ``"
            + util.format_number(quest.money // 2, full_precision=True, money=True)
            + "``"
        )
        player.money -= quest.money // 2
        stats.increment_stat(stats.Stat.MONEY_REMOVED, quest.money // 2, source="quests")
        player.quest_spawn_build_up += 0.1
        player.misc_stats["quest_losing_streak"] += 1
        if player.misc_stats["quest_losing_streak"] == 10:
            await awards.give_award(ctx.channel, player, "QuestLoser")
    elif winner == player:
        if player.quest_day_start == 0:
            player.quest_day_start = time.time()
        player.quests_completed_today += 1
        player.quests_won += 1

        reward = (
            ":sparkles: **"
            + player.name_clean
            + "** defeated the **"
            + quest.name
            + "** and was rewarded with ``"
            + util.format_number(quest.money, full_precision=True, money=True)
            + "`` "
        )
        quest_scale = quest.get_quest_scale()
        avg_player_stat = player.get_avg_stat()

        def attr_gain(stat):
            return max(
                0.01,
                (stat / avg_player_stat)
                * quest.level
                * (turns / average_quest_battle_turns)
                / 2
                * (quest_scale + 0.5)
                * 3,
            )

        # Put some random in the prestige gain so its not a raw 20 * prestige
        max_stats_gain = 100 * player.prestige_multiplicator()
        if player.donor:
            max_stats_gain *= 1.5

        add_strg = min(attr_gain(quest.strg), max_stats_gain)
        # Limit these with add_strg. Since if the quest is super strong. It would not be beatable.
        # Add a little random so the limit is not super visible
        add_attack = min(attr_gain(quest.attack), add_strg * 3 * random.uniform(0.6, 1.5), max_stats_gain)
        add_accy = min(attr_gain(quest.accy), add_strg * 3 * random.uniform(0.6, 1.5), max_stats_gain)

        stats_reward = players.STAT_GAIN_FORMAT % (add_attack, add_strg, add_accy)

        prev_exp = player.total_exp
        player.progress(
            add_attack, add_strg, add_accy, max_attr=max_stats_gain, max_exp=10000 * player.prestige_multiplicator()
        )
        exp_gain = player.total_exp - prev_exp
        quest_results = reward + "and `" + str(round(exp_gain)) + "` EXP\n" + stats_reward

        player.money += quest.money
        stats.increment_stat(stats.Stat.MONEY_CREATED, quest.money)
        stats.increment_stat(stats.Stat.MONEY_GENERATED, quest.money, source="quests")

        quest_info = quest.info
        if quest_info is not None:
            quest_info.times_beaten += 1
            quest_info.save()
        await game.check_for_level_up(ctx, player)
        player.misc_stats["quest_losing_streak"] = 0
    else:
        quest_results = ":question: Against all you drew with the quest!"
    battle_embed.add_field(name="Quest results", value=quest_results, inline=False)
    await imagehelper.battle_screen(ctx, player, quest)
    await util.say(ctx.channel, embed=battle_embed)
    # Put this here to avoid 'spoiling' results before battle log
    if winner == player:
        await awards.give_award(ctx.channel, player, "QuestDone", "*Saved* the guild!")
    elif winner == quest:
        await awards.give_award(ctx.channel, player, "RedMist", "Red mist...")
    else:
        await awards.give_award(ctx.channel, player, "InconceivableQuest")
    player.save()


@commands.command(args_pattern=None, aliases=["aaq"])
@commands.require_cnf(
    warning=(
        "Check your equipped weapon, cash and stats.\n"
        + "This command will accept **all your quests** "
        + "and could potentially result in :bangbang:**MASSIVE money loss**:bangbang: "
        + f"{emojis.NOT_STONK}.\nAre you sure you want to continue?"
    )
)
async def acceptallquests(ctx, **details):
    """
    [CMD_KEY]acceptallquests

    acceptquest, but without the spamming!
    """

    player: players.Player = details["author"]
    if not player.donor:
        raise util.BattleBananaException(ctx.channel, "This command is for donors only!")

    total_quests = len(player.quests)
    if total_quests == 0:
        raise util.BattleBananaException(ctx.channel, "You have no quests!")

    if player.money < sum([quest.money for quest in player.quests]) // 2:
        raise util.BattleBananaException(ctx.channel, "You can't afford the risk of doing all of your quests!")

    if player.quests_completed_today + total_quests >= quests.MAX_DAILY_QUESTS:
        raise util.BattleBananaException(
            ctx.channel,
            "You can't accept all your quests because it will exceed your daily quest limit of "
            + str(quests.MAX_DAILY_QUESTS),
        )

    if player.quest_day_start == 0:
        player.quest_day_start = time.time()

    previous_exp = player.exp
    previous_attack = player.attack
    previous_strength = player.strg
    previous_accuracy = player.accy
    previous_money = player.money

    wins = 0
    lose = 0
    draw = 0
    quest_turns_list = [player.misc_stats["average_quest_battle_turns"]]
    player_quests = list(player.quests)
    for quest in player_quests:
        battle_log = battles.get_battle_log(player_one=player, player_two=quest, p2_prefix="the ")
        quest_turns_list.append(battle_log.turn_count)
        winner = battle_log.winner
        stats.increment_stat(stats.Stat.QUESTS_ATTEMPTED)

        if winner == quest:
            lose += 1
            player.money -= quest.money // 2
            stats.increment_stat(stats.Stat.MONEY_REMOVED, quest.money // 2, source="quests")
            player.quest_spawn_build_up += 0.1
            player.misc_stats["quest_losing_streak"] += 1
            if player.misc_stats["quest_losing_streak"] == 10:
                await awards.give_award(ctx.channel, player, "QuestLoser")

        elif winner == player:
            wins += 1
            player.money += quest.money
            player.quests_completed_today += 1
            player.quests_won += 1

            average_turns = sum(quest_turns_list) / len(quest_turns_list)
            add_strg, add_attack, add_accy, max_stats_gain = player.calculate_progress(
                quest, battle_log.turn_count, average_turns
            )
            player.progress(
                add_attack, add_strg, add_accy, max_attr=max_stats_gain, max_exp=10000 * player.prestige_multiplicator()
            )

            stats.increment_stat(stats.Stat.MONEY_CREATED, quest.money)
            stats.increment_stat(stats.Stat.MONEY_GENERATED, quest.money, source="quests")

            quest_info = quest.info
            if quest_info is not None:
                quest_info.times_beaten += 1
                quest_info.save()
            await game.check_for_level_up(ctx, player)
            player.misc_stats["quest_losing_streak"] = 0

        else:
            draw += 1

        player.quests.remove(quest)

    average_turns = round(sum(quest_turns_list) / len(quest_turns_list), 2)
    player.misc_stats["average_quest_battle_turns"] = average_turns
    battle_embed = discord.Embed(title="Battle Results", type="rich", color=gconf.DUE_COLOUR)
    battle_embed.add_field(
        name="Quests Fought",
        value=(
            f"Total quests: {total_quests}\n"
            + f"Won: {wins}\n"
            + f"Lost: {lose}\n"
            + f"Draw: {draw}\n"
            + f"Total Turns: {int(sum(quest_turns_list))}\n"
            + f"Average Turns: {average_turns}"
        ),
    )
    battle_embed.add_field(
        name="Results",
        value=(
            f"{emojis.ATK}: {round(player.attack - previous_attack, 2)}\n"
            + f"{emojis.ACCY}: {round(player.accy - previous_accuracy, 2)}\n"
            + f"{emojis.STRG}: {round(player.strg - previous_strength, 2)}\n"
            + f"Money: ¤{player.money - previous_money}\n"
            + f"EXP: {round(player.exp - previous_exp)}"
        ),
    )
    battle_embed.set_footer(
        text="If the money is negative, then you lost more money from losing battles than you gained from winning them."
    )

    await util.reply(ctx, embed=battle_embed)

    if wins > 0:
        await awards.give_award(ctx.channel, player, "QuestDone", "*Saved* the guild!")
    if lose > 0:
        await awards.give_award(ctx.channel, player, "RedMist", "Red mist...")
    if draw > 0:
        await awards.give_award(ctx.channel, player, "InconceivableQuest")

    player.save()


@commands.command(args_pattern="C", aliases=["dq"])
async def declinequest(ctx, quest_index, **details):
    """
    [CMD_KEY]declinequest index

    Declines a quest because you're too wimpy to accept it.
    """

    player = details["author"]
    quest_index -= 1
    if quest_index < len(player.quests):
        quest = player.quests[quest_index]
        del player.quests[quest_index]
        player.save()
        quest_info = quest.info
        if quest_info is not None:
            quest_task = quest_info.task
        else:
            quest_task = "do a long forgotten quest:"
        await util.reply(
            ctx,
            f"**{player.name_clean}** declined to {quest_task} **{quest.name_clean} [Level {quest.level}]**!",
        )
    else:
        raise util.BattleBananaException(ctx.channel, quests.QUEST_NOT_FOUND)


@commands.command(aliases=["daq"])
@commands.require_cnf(warning="This will **__permanently__** delete **__all__** your quests!")
async def declineallquests(ctx, **details):
    """
    [CMD_KEY]declineallquest

    Declines all of your quests because you're too wimpy to do any of them.
    """

    player = details["author"]

    quests_count = len(player.quests)
    if quests_count == 0:
        raise util.BattleBananaException(ctx.channel, "You have no quests to decline!")

    player.quests.clear()
    player.save()

    await util.reply(ctx, f"Declined {quests_count} quests!")


@commands.command(permission=Permission.SERVER_ADMIN, args_pattern="SRRRRS?S?S?%?")
async def createquest(ctx, name, attack, strg, accy, hp, task=None, weapon=None, image_url=None, spawn_chance=25, **_):
    """
    [CMD_KEY]createquest name (base attack) (base strg) (base accy) (base hp)

    You can also add (task string) (weapon) (image url) (spawn chance)
    after the first four args.

    Note a base value is how strong the quest would be at level 1

    __Example__:
    Basic Quest:
        ``[CMD_KEY]createquest "Mega Mouse" 1.3 2 1.1 32``
        This creates a quest named "Mega Mouse".
        With base values:
            Attack = 1.3
            Strg = 2
            Accy = 1.1
            HP = 32
    Advanced Quest:
        ``[CMD_KEY]createquest "Snek Man" 1.3 2 1.1 32 "Kill the" "Dagger" https://battlebanana.xyz/img/snek_man.png 21``
        This creates a quest with the same base values as before but with the message "Kill the"
        when the quest pops up, a dagger, a quest icon image and a spawn chance of 21%
    """
    if len(quests.get_server_quest_list(ctx.guild)) >= gconf.THING_AMOUNT_CAP:
        raise util.BattleBananaException(
            ctx.guild, f"Whoa, you've reached the limit of {gconf.THING_AMOUNT_CAP} quests!"
        )

    extras = {"spawn_chance": spawn_chance}
    if task is not None:
        extras["task"] = task
    if weapon is not None:
        weapon_name_or_id = weapon
        weapon = weapons.find_weapon(ctx.guild, weapon_name_or_id)
        if weapon is None:
            raise util.BattleBananaException(ctx.channel, "Weapon for the quest not found!")
        extras["weapon_id"] = weapon.w_id
    if image_url is not None:
        extras["image_url"] = image_url

    if "image_url" in extras and not await imagehelper.is_url_image(image_url):
        extras.pop("image_url")
        await imagehelper.warn_on_invalid_image(ctx.channel)

    new_quest = quests.Quest(name, attack, strg, accy, hp, **extras, ctx=ctx)
    await util.reply(
        ctx,
        ":white_check_mark: "
        + util.ultra_escape_string(new_quest.task)
        + " **"
        + new_quest.name_clean
        + "** is now active!",
    )


@commands.command(permission=Permission.SERVER_ADMIN, args_pattern="SS*")
@commands.extras.dict_command(
    optional={
        "attack/atk": "R",
        "strg/strength": "R",
        "hp": "R",
        "accy/accuracy": "R",
        "spawn": "%",
        "weapon/weap": "S",
        "image": "S",
        "task": "S",
        "channel": "S",
    }
)
async def editquest(ctx, quest_name, updates, **_):
    """
    [CMD_KEY]editquest name (property value)+

    Any number of properties can be set at once.
    This is also how you set quest channels!

    Properties:
        __attack__, __hp__, __accy__, __spawn__, __weapon__,
        __image__, __task__, __strg__, and __channel__

    Example usage:

        [CMD_KEY]editquest "snek man" hp 43 attack 4.2 task "Kill the monster"

        [CMD_KEY]editquest slime channel ``#slime_fields``
    """

    quest = quests.get_quest_on_server(ctx.guild, quest_name)
    if quest is None:
        raise util.BattleBananaException(ctx.channel, quests.QUEST_NOT_FOUND)

    new_image_url = None
    for quest_property, value in updates.items():
        # Validate and set updates.
        if quest_property in ("attack", "atk", "accy", "accuracy", "strg", "strength"):
            if value >= 1:
                if quest_property in ("attack", "atk"):
                    quest.base_attack = value
                elif quest_property in ("accy", "accuracy"):
                    quest.base_accy = value
                else:
                    quest.base_strg = value
            else:
                updates[quest_property] = "Must be at least 1!"
        elif quest_property == "spawn":
            if 25 >= value >= 1:
                quest.spawn_chance = value / 100
            else:
                updates[quest_property] = "Must be 1-25%!"
        elif quest_property == "hp":
            if value >= 30:
                quest.base_hp = value
            else:
                updates[quest_property] = "Must be at least 30!"
        elif quest_property in ("weap", "weapon"):
            weapon = weapons.get_weapon_for_server(ctx.guild.id, value)
            if weapon is not None:
                quest.w_id = weapon.w_id
                updates[quest_property] = weapon
            else:
                updates[quest_property] = "Weapon not found!"
        elif quest_property == "channel":
            if value.upper() in ("ALL", "NONE"):
                quest.channel = value.upper()
                updates[quest_property] = value.title()
            else:
                new_value = [i.strip() for i in value.split(",")]  # split through comma
                new_value = [i.split() for i in new_value]  # split through space
                new_value = [
                    id for l in new_value for id in l
                ]  # flatten the list - final output will always be list with list containing single elements
                quest_channels = []
                channel_list_string = ""
                for channel in new_value:
                    channel_id = channel.replace("<#", "").replace(">", "")
                    ret_channel = util.get_channel(channel_id)
                    if ret_channel is not None:
                        if ret_channel not in quest_channels:  # avoid duplicates
                            quest_channels.append(channel_id)
                            channel_list_string += f"\n\t{ret_channel.mention}"
                    else:
                        channel_list_string += f"\n\t{channel} Channel not found!"
                if quest_channels:
                    quest.channel = quest_channels
                updates[quest_property] = channel_list_string
        else:
            updates[quest_property] = util.ultra_escape_string(value)
            if quest_property == "image":
                new_image_url = quest.image_url = value
            else:
                # Task
                quest.task = value
                updates[quest_property] = f'"{updates[quest_property]}"'

    # Format result.
    if len(updates) == 0:
        await util.reply(ctx, "You need to provide a valid list of changes for the quest!")
    else:
        result = f"{emojis.QUEST} **{quest.name_clean}** updates!\n"

        if new_image_url is not None and not await imagehelper.is_url_image(new_image_url):
            quest.image_url = quest.DEFAULT_IMAGE
            updates["image"] = None
            await imagehelper.warn_on_invalid_image(ctx.channel)

        for quest_property, update_result in updates.items():
            result += f"``{quest_property}`` → {update_result}\n"

        quest.save()
        await util.reply(ctx, result)


@commands.command(permission=Permission.SERVER_ADMIN, args_pattern="S")
async def removequest(ctx, quest_name, **_):
    """
    [CMD_KEY]removequest (quest name)

    Systematically exterminates all instances of the quest...
    ...Even those yet to be born
    """

    quest_name = quest_name.lower()
    quest = quests.get_quest_on_server(ctx.guild, quest_name)
    if quest is None:
        raise util.BattleBananaException(ctx.channel, quests.QUEST_NOT_FOUND)

    quests.remove_quest_from_server(ctx.guild, quest_name)
    await util.reply(ctx, ":white_check_mark: **" + quest.name_clean + "** is no more!")


@commands.command(permission=Permission.REAL_SERVER_ADMIN, args_pattern="S?")
@commands.require_cnf(warning="This will **__permanently__** delete all your quests!")
async def resetquests(ctx, **_):
    """
    [CMD_KEY]resetquests

    Genocide in a command!
    This command will **delete all quests** on your guild.
    """

    quests_deleted = quests.remove_all_quests(ctx.guild)
    if quests_deleted > 0:
        await util.reply(
            ctx,
            (
                ":wastebasket: Your quests have been reset — "
                + f"**{quests_deleted} {util.s_suffix('quest', quests_deleted)}** deleted."
            ),
        )
    else:
        await util.reply(ctx, "There's no quests to delete!")


@commands.command(permission=Permission.SERVER_ADMIN, args_pattern="M?")
async def serverquests(ctx, page=1, **details):
    """
    [CMD_KEY]serverquests (page or quest name)

    Lists the quests active on your guild.

    If you would like to see the base stats of a quest do [CMD_KEY]serverquests (quest name)

    Remember you can edit any of the quests on your guild with [CMD_KEY]editquest
    """

    if isinstance(page, int):
        page -= 1

        quests_list = list(quests.get_server_quest_list(ctx.guild).values())
        quests_list.sort(key=lambda server_quest: server_quest.times_beaten, reverse=True)

        @misc.paginator
        def quest_list(quests_embed, current_quest, **_):
            quests_embed.add_field(
                name=current_quest.name_clean,
                value=f"Completed {current_quest.times_beaten} {util.s_suffix('time', current_quest.times_beaten)}\n"
                + f"Active channel: {current_quest.get_channel_mention(ctx.guild)}",
            )

        # misc.paginator handles all the messy checks.
        quest_list_embed = quest_list(
            quests_list,
            page,
            title=emojis.QUEST + " Quests on " + details["server_name_clean"],
            footer_more=f"But wait there more! Do {details['cmd_key']}serverquests {page + 2}",
            empty_list="There are no quests on this guild!\nHow sad.",
        )

        await util.reply(ctx, embed=quest_list_embed)
    else:
        # TODO: Improve
        quest_name = page
        quest = quests.get_quest_on_server(ctx.guild, quest_name)
        if quest is None:
            raise util.BattleBananaException(ctx.channel, quests.QUEST_NOT_FOUND)

        quest_info_embed = discord.Embed(
            type="rich",
            color=gconf.DUE_COLOUR,
            title=f"Quest information for the {quest.name_clean}",
            description=(
                "You can edit these values with"
                + f"{details['cmd_key']}editquest {quest.name_command_clean.lower()} (values)"
            ),
        )

        attributes_formatted = tuple(
            util.format_number(base_value, full_precision=True)
            for base_value in (*quest.base_values(), quest.spawn_chance * 100)
        )
        quest_info_embed.add_field(
            name="Base stats",
            value=(
                (
                    f"{emojis.ATK} **ATK** - %s \n"
                    + f"{emojis.STRG} **STRG** - %s\n"
                    + f"{emojis.ACCY} **ACCY** - %s\n"
                    + f"{emojis.HP} **HP** - %s\n"
                    + f"{emojis.QUEST} **Spawn %%** - %s\n"
                )
                % attributes_formatted
            ),
        )
        quest_weapon = weapons.get_weapon_from_id(quest.w_id)
        quest_info_embed.add_field(
            name="Other attributes",
            value=(
                f"{emojis.QUESTINFO} **Image** - [Click to view]({util.ultra_escape_string(quest.image_url)})\n"
                + f':speech_left: **Task message** - "{util.ultra_escape_string(quest.task)}"\n'
                + f"{emojis.WPN} **Weapon** - {quest_weapon}\n"
                + f"{emojis.CHANNEL} **Channel** - {quest.get_channel_mention(ctx.guild)}\n"
            ),
            inline=False,
        )
        quest_info_embed.set_thumbnail(url=quest.image_url)
        await util.reply(ctx, embed=quest_info_embed)
