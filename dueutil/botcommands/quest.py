import math
import time
import random

import discord

import generalconfig as gconf
from ..game.helpers import imagehelper
from ..permissions import Permission
from ..game import (
    quests,
    game,
    battles,
    weapons,
    stats,
    awards,
    players,
    translations)
from .. import commands, util
from ..game.helpers import misc

from ..game import emojis as e

quest_Fnames = ["Bob", "Albert", "Rodrigo", "Alfonso", "Ricardo", "Jesus", "Dr.", "Greg", "Tony", "Eugene", "Jack", "Ben", "Phil", "Michael", "John", "Benito", "Joseph", "Abraham", "George"]
quest_Lnames = ["Christ", "Heffely", "Clark", "McDouglas", "Sear", "Dover", "Cena", "Jackson", "Lincoln", ]
quest_battle = ["Fight", "Defeat", "Battle"]

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
        await util.reply(ctx,
                       ":cloud_lightning: Spawned **" + quest.name_clean + "** [Level " + str(active_quest.level) + "]")
    except:
        raise util.BattleBananaException(ctx.channel, "Failed to spawn quest!")


@commands.command(args_pattern='C', aliases=['qi'])
@commands.imagecommand()
async def questinfo(ctx, quest_index, **details):
    """quest:questinfo:Help"""

    player = details["author"]
    quest_index -= 1
    if 0 <= quest_index < len(player.quests):
        await imagehelper.quest_screen(ctx, player.quests[quest_index])
    else:
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "quest:questinfo:NotFound"))


@commands.command(args_pattern='C?', aliases=['mq'])
@commands.imagecommand()
async def myquests(ctx, page=1, **details):
    """quest:myquests:Help"""

    player = details["author"]
    page -= 1
    # Always show page 1 (0)
    if page != 0 and page * 5 >= len(player.quests):
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "quest:myquests:PNotFound"))
    await imagehelper.quests_screen(ctx, player, page)


@commands.command(args_pattern='C', aliases=['aq'])
@commands.imagecommand()
async def acceptquest(ctx, quest_index, **details):
    """quest:acceptquest:Help"""

    player = details["author"]
    quest_index -= 1
    if quest_index >= len(player.quests):
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "quest:acceptquest:QNotFound"))
    if player.money - player.quests[quest_index].money // 2 < 0:
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "quest:acceptquest:CantAfford"))
    if player.quests_completed_today >= quests.MAX_DAILY_QUESTS:
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "quest:acceptquest:QLimit", str(quests.MAX_DAILY_QUESTS)))

    quest = player.quests.pop(quest_index)
    battle_log = battles.get_battle_log(ctx, player_one=player, player_two=quest, p2_prefix="the ")
    battle_embed = battle_log.embed
    turns = battle_log.turn_count
    winner = battle_log.winner
    stats.increment_stat(stats.Stat.QUESTS_ATTEMPTED)
    # Not really an average (but w/e)
    average_quest_battle_turns = player.misc_stats["average_quest_battle_turns"] = (player.misc_stats[
                                                                                        "average_quest_battle_turns"] + turns) / 2
    if winner == quest:
        quest_results = (translations.translate(ctx, "quest:acceptquest:Lose", player.name_clean, quest.name_clean, util.format_number(quest.money // 2, full_precision=True, money=True)))
        player.money -= quest.money // 2
        player.quest_spawn_build_up += 0.1
        player.misc_stats["quest_losing_streak"] += 1
        if player.misc_stats["quest_losing_streak"] == 10:
            await awards.give_award(ctx.channel, player, "QuestLoser")
    elif winner == player:
        if player.quest_day_start == 0:
            player.quest_day_start = time.time()
        player.quests_completed_today += 1
        player.quests_won += 1

        reward = (translations.translate(ctx, "quest:acceptquest:Win", player.name_clean, quest.name, util.format_number(quest.money, full_precision=True, money=True)))
        quest_scale = quest.get_quest_scale()
        avg_player_stat = player.get_avg_stat()

        def attr_gain(stat):
            return (max(0.01, (stat / avg_player_stat)
                        * quest.level * (turns / average_quest_battle_turns) / 2 * (quest_scale + 0.5) * 3))

        # Put some random in the prestige gain so its not a raw 20 * prestige
        max_stats_gain = 100 * player.prestige_multiplicator()
        if player.donor:
            max_stats_gain *= 1.5

        add_strg = min(attr_gain(quest.strg), max_stats_gain)
        # Limit these with add_strg. Since if the quest is super strong. It would not be beatable.
        # Add a little random so the limit is not super visible
        add_attack = min(attr_gain(quest.attack), min(add_strg * 3 * random.uniform(0.6, 1.5), max_stats_gain))
        add_accy = min(attr_gain(quest.accy), min(add_strg * 3 * random.uniform(0.6, 1.5), max_stats_gain))

        stats_reward = players.STAT_GAIN_FORMAT % (add_attack, add_strg, add_accy)
        quest_results = reward + stats_reward

        prevExp = player.total_exp 
        player.progress(add_attack, add_strg, add_accy, max_attr=max_stats_gain, max_exp=10000 * player.prestige_multiplicator())
        expGain = player.total_exp - prevExp
        quest_results = (reward +translations.translate(ctx, "other:singleword:And")+" `" + str(round(expGain)) + "` EXP\n" + stats_reward)

        player.money += quest.money
        stats.increment_stat(stats.Stat.MONEY_CREATED, quest.money)

        quest_info = quest.info
        if quest_info is not None:
            quest_info.times_beaten += 1
            quest_info.save()
        await game.check_for_level_up(ctx, player)
        player.misc_stats["quest_losing_streak"] = 0
    else:
        quest_results = translations.translate(ctx, "quest:acceptquest:Tie")
    battle_embed.add_field(name=translations.translate(ctx, "quest:acceptquest:QResult"), value=quest_results, inline=False)
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

#@commands.command(args_pattern=None, aliases=['aaq'])
#@commands.imagecommand()
#async def acceptallquests(ctx, **details):
#    """
#    [CMD_KEY]acceptallquests
#
#    acceptquest, but without the spamming!
#    """
#
#    if not player.donor:
#        raise util.BattleBananaException(ctx.channel, "This command is for donors only!")
#
#    player = details["author"]
#
#    if 0 >= len(player.quests):
#        raise util.BattleBananaException(ctx.channel, "You have no quests!")
#    a = 0
#    #while a < len(player.quests):
#    #    if player.money - player.quests[a].money // 2 < 0:
#    #        raise util.BattleBananaException(ctx.channel, "You can't afford the risk of doing all of your quests!")
#    #    a +=1
#    #if player.quests_completed_today >= quests.MAX_DAILY_QUESTS:
#    #    raise util.BattleBananaException(ctx.channel,
#    #                                "You can't do more than " + str(quests.MAX_DAILY_QUESTS) + " quests a day!")
#    
#    totalCash = 0
#    totalXp = 0
#    totalAttack = 0
#    totalStrength = 0
#    totalAccuracy = 0
#    totalTurns = 0
#    wins = 0
#    lose = 0
#    draw = 0
#    b = 0
#    quests = len(player.quests)
#    while b < quests:
#        quest = player.quests.pop(b)
#        battle_log = battles.get_battle_log(ctx, player_one=player, player_two=quest, p2_prefix="the ")
#        turns = battle_log.turn_count
#        winner = battle_log.winner
#        stats.increment_stat(stats.Stat.QUESTS_ATTEMPTED)
#        # Not really an average (but w/e)
#        average_quest_battle_turns = player.misc_stats["average_quest_battle_turns"] = (player.misc_stats[
#                                                                                            "average_quest_battle_turns"] + turns) / 2
#        if winner == quest:
#            lose += 1
#            totalCash -= quest.money // 2
#            player.quest_spawn_build_up += 0.1
#            player.misc_stats["quest_losing_streak"] += 1
#            if player.misc_stats["quest_losing_streak"] == 10:
#                await awards.give_award(ctx.channel, player, "QuestLoser")
#        elif winner == player:
#            wins += 1
#            if player.quest_day_start == 0:
#                player.quest_day_start = time.time()
#            player.quests_completed_today += 1
#            player.quests_won += 1
#            totalCash += quest.money
#            quest_scale = quest.get_quest_scale()
#            avg_player_stat = player.get_avg_stat()
#
#            def attr_gain(stat):
#                return (max(0.01, (stat / avg_player_stat)
#                            * quest.level * (turns / average_quest_battle_turns) / 2 * (quest_scale + 0.5) * 3))
#
#            # Put some random in the prestige gain so its not a raw 20 * prestige
#            max_stats_gain = 100 * player.prestige_multiplicator()
#            if player.donor:
#                max_stats_gain *= 1.5
#
#            add_strg = min(attr_gain(quest.strg), max_stats_gain)
#            add_attack = min(attr_gain(quest.attack), min(add_strg * 3 * random.uniform(0.6, 1.5), max_stats_gain))
#            add_accy = min(attr_gain(quest.accy), min(add_strg * 3 * random.uniform(0.6, 1.5), max_stats_gain))
#
#            prevExp = player.total_exp 
#            player.progress(add_attack, add_strg, add_accy, max_attr=max_stats_gain, max_exp=10000 * player.prestige_multiplicator())
#            expGain = player.total_exp - prevExp
#
#            totalXp += expGain
#            totalAccuracy += add_accy
#            totalAttack += add_attack
#            totalStrength += add_strg
#            # that's the wrong way to calculate total turns
#            totalTurns += average_quest_battle_turns
#
#            stats.increment_stat(stats.Stat.MONEY_CREATED, quest.money)
#
#            quest_info = quest.info
#            if quest_info is not None:
#                quest_info.times_beaten += 1
#                quest_info.save()
#            await game.check_for_level_up(ctx, player)
#            player.misc_stats["quest_losing_streak"] = 0
#        else:
#            draw += 1
#        quests -=1
#
#    if draw > 0:
#        drawQuest = ("\nDraw: " + draw)
#    else:
#        drawQuest = ""
#    
#    player.money += totalCash
#    
#    battle_embed = discord.Embed(title=("Battle Results"), type="rich", color=gconf.DUE_COLOUR)
#    battle_embed.add_field(name="Quests Fought", value=("Total quests: "+str(int(wins+lose))+"\nWon: " +str(wins)+"\nLost "+str(lose)+drawQuest))
#    battle_embed.add_field(name="Stat gains", value=("Added Cash: `¤"+str(totalCash)+"`\nAdded EXP: `"+str(round(totalXp))+"`\n"+emojis.ATK+": "+str(totalAttack)+"\n"+emojis.ACCY+": "+str(totalAccuracy)+"\n"+emojis.STRG+": "+str(totalStrength)))
#    # totalTurns is wrong with the implementation of adding the averages
#    #    battle_embed.add_field(name="Total turns", value=(str(round(totalTurns))))
#    battle_embed.set_footer(text="If the added money is negative, then you lost more money from losing battles than you gained from winning them.")
#    
#    await util.reply(ctx, embed=battle_embed)
#
#    if wins > 0:
#        await awards.give_award(ctx.channel, player, "QuestDone", "*Saved* the guild!")
#    elif lose > 0:
#        await awards.give_award(ctx.channel, player, "RedMist", "Red mist...")
#    elif draw > 0:
#        await awards.give_award(ctx.channel, player, "InconceivableQuest")
#
#    player.save()


@commands.command(args_pattern='C', aliases=["dq"])
async def declinequest(ctx, quest_index, **details):
    """quest:declinequest:Help"""

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
            quest_task = translations.translate(ctx, "quest:declinequest:Forgotten")
        await translations.say(ctx, "quest:declinequest:Success", player.name_clean, quest_task, quest.name_clean, str(math.trunc(quest.level)))
    else:
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "quest:declinequest:NotFound"))

@commands.command(aliases=["daq"])
@commands.require_cnf(warning="quest:declineallquests:CNF")
async def declineallquests(ctx, **details):
    """quest:declineallquests:Help"""

    player = details["author"]
    #if not player.donor:
        #raise util.BattleBananaException(ctx.channel, "This command is for donors only!")

    quests = len(player.quests)
    if quests == 0:
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "quest:declineallquests:NoQuests"))

    player.quests.clear()
    player.save()
    
    await translations.say(ctx, "quest:declineallquests:Success", quests)


@commands.command(permission=Permission.SERVER_ADMIN, args_pattern='SRRRRS?S?S?%?')
async def createquest(ctx, name, attack, strg, accy, hp,
                      task=None, weapon=None, image_url=None, spawn_chane=25, **_):
    """quest:createquest:Help"""
    if len(quests.get_server_quest_list(ctx.guild)) >= gconf.THING_AMOUNT_CAP:
        raise util.BattleBananaException(ctx.guild, translations.translate(ctx, "quest:createquest:Limit", gconf.THING_AMOUNT_CAP))

    extras = {"spawn_chance": spawn_chane}
    if task is not None:
        extras['task'] = task
    if weapon is not None:
        weapon_name_or_id = weapon
        weapon = weapons.find_weapon(ctx.guild, weapon_name_or_id)
        if weapon is None:
            raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "quest:createquest:MissingWeapon"))
        extras['weapon_id'] = weapon.w_id
    if image_url is not None:
        extras['image_url'] = image_url

    new_quest = quests.Quest(name, attack, strg, accy, hp, **extras, ctx=ctx)
    await translations.say(ctx, "quest:createquest:Success", util.ultra_escape_string(new_quest.task), new_quest.name_clean)
    if "image_url" in extras:
        await imagehelper.warn_on_invalid_image(ctx.channel, url=extras["image_url"])


@commands.command(permission=Permission.SERVER_ADMIN, args_pattern='SS*')
@commands.extras.dict_command(optional={"attack/atk": "R", "strg/strength": "R", "hp": "R",
                                        "accy/accuracy": "R", "spawn": "%", "weapon/weap": "S",
                                        "image": "S", "task": "S", "channel": "S"})
async def editquest(ctx, quest_name, updates, **_):
    """quest:editquest:Help"""

    quest = quests.get_quest_on_server(ctx.guild, quest_name)
    if quest is None:
        raise util.BattleBananaException(ctx.channel, "Quest not found!")

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
                updates[quest_property] = translations.translate(ctx, "quest:editquest:Under1")
            continue
        elif quest_property == "spawn":
            if 25 >= value >= 1:
                quest.spawn_chance = value / 100
            else:
                updates[quest_property] = translations.translate(ctx, "quest:editquest:WrongPercent")
        elif quest_property == "hp":
            if value >= 30:
                quest.base_hp = value
            else:
                updates[quest_property] = translations.translate(ctx, "quest:editquest:BadHealth")
        elif quest_property in ("weap", "weapon"):
            weapon = weapons.get_weapon_for_server(ctx.guild.id, value)
            if weapon is not None:
                quest.w_id = weapon.w_id
                updates[quest_property] = weapon
            else:
                updates[quest_property] = translations.translate(ctx, "quest:editquest:WpnNotFound")
        elif quest_property == "channel":
            if value.upper() in ("ALL", "NONE"):
                quest.channel = value.upper()
                updates[quest_property] = value.title()
            else:
                channel_id = value.replace("<#", "").replace(">", "")
                channel = util.get_channel(channel_id)
                if channel is not None:
                    quest.channel = channel.id
                else:
                    updates[quest_property] = translations.translate(ctx, "quest:editquest:ChanNotFound")
        else:
            updates[quest_property] = util.ultra_escape_string(value)
            if quest_property == "image":
                new_image_url = quest.image_url = value
            else:
                # Task
                quest.task = value
                updates[quest_property] = '"%s"' % updates[quest_property]

    # Format result.
    if len(updates) == 0:
        await translations.say(ctx, "quest:editquest:InvalidChange")
    else:
        quest.save()
        result = e.QUEST + translations.translate(ctx, "quest:editquest:Updates", quest.name_clean)
        for quest_property, update_result in updates.items():
            result += ("``%s`` → %s\n" % (quest_property, update_result))
        await util.reply(ctx, result)
        if new_image_url is not None:
            await imagehelper.warn_on_invalid_image(ctx.channel, new_image_url)


@commands.command(permission=Permission.SERVER_ADMIN, args_pattern='S')
async def removequest(ctx, quest_name, **_):
    """quest:removequest:Help"""

    quest_name = quest_name.lower()
    quest = quests.get_quest_on_server(ctx.guild, quest_name)
    if quest is None:
        raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "quest:removequest:QuestNotFound"))

    quests.remove_quest_from_server(ctx.guild, quest_name)
    await translations.say(ctx, "quest:removequest:Success", quest.name_clean)


@commands.command(permission=Permission.REAL_SERVER_ADMIN, args_pattern="S?")
@commands.require_cnf(warning="quest:resetquests:CNF")
async def resetquests(ctx, **_):
    """quest:resetquests:Help"""

    quests_deleted = quests.remove_all_quests(ctx.guild)
    if quests_deleted > 0:
        await translations.say(ctx, "quest:resetquests:Success", quests_deleted, util.s_suffix("quest", quests_deleted))
    else:
        await translations.say(ctx, "quest:resetquests:NoQuests")


@commands.command(permission=Permission.SERVER_ADMIN, args_pattern='M?')
async def serverquests(ctx, page=1, **details):
    """quest:serverquests:Help"""

    @misc.paginator
    def quest_list(quests_embed, current_quest, **_):
        quests_embed.add_field(name=current_quest.name_clean,
                               value="Completed %s time" % current_quest.times_beaten
                                     + ("s" if current_quest.times_beaten != 1 else "") + "\n"
                                     + "Active channel: %s"
                                       % current_quest.get_channel_mention(ctx.guild))

    if type(page) is int:
        page -= 1

        quests_list = list(quests.get_server_quest_list(ctx.guild).values())
        quests_list.sort(key=lambda server_quest: server_quest.times_beaten, reverse=True)

        # misc.paginator handles all the messy checks.
        quest_list_embed = quest_list(quests_list, page, e.QUEST+" Quests on " + details["server_name_clean"],
                                      footer_more="But wait there more! Do %sserverquests %d" % (details["cmd_key"], page+2),
                                      empty_list="There are no quests on this guild!\nHow sad.")

        await util.reply(ctx, embed=quest_list_embed)
    else:
        # TODO: Improve
        quest_info_embed = discord.Embed(type="rich", color=gconf.DUE_COLOUR)
        quest_name = page
        quest = quests.get_quest_on_server(ctx.guild, quest_name)
        if quest is None:
            raise util.BattleBananaException(ctx.channel, "Quest not found!")
        quest_info_embed.title = "Quest information for the %s " % quest.name_clean
        quest_info_embed.description = "You can edit these values with %seditquest %s (values)" \
                                       % (details["cmd_key"], quest.name_command_clean.lower())

        attributes_formatted = tuple(util.format_number(base_value, full_precision=True)
                                     for base_value in quest.base_values() + (quest.spawn_chance * 100,))
        quest_info_embed.add_field(name="Base stats", value=((e.ATK + " **ATK** - %s \n"
                                                              + e.STRG + " **STRG** - %s\n"
                                                              + e.ACCY + " **ACCY** - %s\n"
                                                              + e.HP + " **HP** - %s\n"
                                                              + e.QUEST + " **Spawn %%** - %s\n")
                                                             % attributes_formatted))
        quest_weapon = weapons.get_weapon_from_id(quest.w_id)
        quest_info_embed.add_field(name="Other attributes", value=(e.QUESTINFO + " **Image** - [Click to view](%s)\n"
                                                                   % util.ultra_escape_string(quest.image_url)
                                                                   + ':speech_left: **Task message** - "%s"\n'
                                                                   % util.ultra_escape_string(quest.task)
                                                                   + e.WPN + " **Weapon** - %s\n" % quest_weapon
                                                                   + e.CHANNEL + " **Channel** - %s\n"
                                                                   % quest.get_channel_mention(ctx.guild)),
                                   inline=False)
        quest_info_embed.set_thumbnail(url=quest.image_url)
        await util.reply(ctx, embed=quest_info_embed)
