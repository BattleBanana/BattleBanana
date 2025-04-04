import json
import re
import secrets
import time

import generalconfig as gconf
from dueutil import dbconn, events, util
from dueutil.game import awards, gamerules, players, quests, stats, weapons
from dueutil.game.configs import dueserverconfig
from dueutil.game.helpers import imagehelper

try:
    import ssdeep
except ImportError:
    import ppdeep as ssdeep

SPAM_TOLERANCE = 50
# For awards in the first week. Not permanent.
old_players = open("oldplayers.txt", encoding="utf-8").read()  # For comeback award
testers = open("testers.txt", encoding="utf-8").read()  # For testers award


def get_responses() -> list[str]:
    return json.load(open("dueutil/game/configs/daily.json", "r", encoding="utf-8"))


def get_spam_level(player, message_content):
    """
    Get's a spam level for a message using a
    fuzzy hash > 50% means it's probably spam
    """
    message_hash = ssdeep.hash(message_content)
    spam_level = 0
    spam_levels = [
        ssdeep.compare(message_hash, prior_hash) for prior_hash in player.last_message_hashes if prior_hash is not None
    ]
    if len(spam_levels) > 0:
        spam_level = sum(spam_levels) / len(spam_levels)
    player.last_message_hashes.append(message_hash)

    return spam_level


def progress_time(player):
    return time.time() - player.last_progress >= 60


def quest_time(player):
    return time.time() - player.last_quest >= quests.QUEST_COOLDOWN


async def player_message(message, player, spam_level):
    """
    W.I.P. Function to allow a small amount of exp
    to be gained from messaging.

    """

    def get_words():
        return re.compile(r"\w+").findall(message.content)

    # Mention the old bot award
    if gconf.DEAD_BOT_ID in message.raw_mentions:
        await awards.give_award(message.channel, player, "SoCold", "They're not coming back.")
    # Art award
    if player.misc_stats["art_created"] >= 100:
        await awards.give_award(message.channel, player, "ItsART")

    if progress_time(player) and spam_level < SPAM_TOLERANCE:
        if len(message.content) > 0:
            player.last_progress = time.time()
        else:
            return

        # Special Awards
        # Comeback award
        if str(player.id) in old_players:
            await awards.give_award(message.channel, player, "CameBack", "Return to BattleBanana")
        # Tester award
        if str(player.id) in testers:
            await awards.give_award(message.channel, player, "Tester", ":bangbang: **Something went wrong...**")
        # Donor award
        if player.donor:
            await awards.give_award(
                message.channel,
                player,
                "Donor",
                "Donate to BattleBanana!!! :money_with_wings: :money_with_wings: :money_with_wings:",
            )
        # DueUtil tech award
        if dbconn.conn()["dueutiltechusers"].count_documents({"_id": player.id}) > 0:
            if "DueUtilTech" not in player.awards:
                player.inventory["themes"].append("dueutil.tech")
            await awards.give_award(message.channel, player, "DueUtilTech", "<https://battlebanana.xyz/>")

        ### DueUtil - the hidden spelling game!
        # The non-thread safe Apsell calls
        # spelling_lock.acquire()
        # DISABLED: Spell checking due to random seg faults (even with locks).
        # lang = guess_language(message.content)
        # if lang in enchant.list_languages():
        #     spelling_dict = enchant.Dict(lang)
        # else:
        #     spelling_dict = enchant.Dict("en_GB")

        spelling_score = 0
        big_word_count = 1
        big_word_spelling_score = 0
        message_words = get_words()
        for word in message_words:
            if len(word) > 4:
                big_word_count += 1
            if secrets.randbits(1):  # spelling_dict.check(word):
                spelling_score += 3
                if len(word) > 4:
                    big_word_spelling_score += 1
            else:
                spelling_score -= 1
        # spelling_lock.release()
        # We survived?!

        spelling_score = max(1, spelling_score / ((len(message_words) * 3) + 1))
        spelling_avg = player.misc_stats["average_spelling_correctness"]
        spelling_strg = big_word_spelling_score / big_word_count
        # Not really an average (like quest turn avg) (but w/e)
        player.misc_stats["average_spelling_correctness"] = (spelling_avg + spelling_score) / 2

        len_limit = max(1, 120 - len(message.content))
        player.progress(spelling_score / len_limit, spelling_strg / len_limit, spelling_avg / len_limit)

        player.hp = 10 * player.level
        await check_for_level_up(message, player)
        player.save()


async def check_for_level_up(ctx, player):
    """
    Handles player level ups.
    """

    exp_for_next_level = gamerules.get_exp_for_next_level(player.level)
    level_up_reward = 0
    while player.exp >= exp_for_next_level:
        player.exp -= exp_for_next_level
        player.level += 1
        level_up_reward += player.level * 10
        player.money += level_up_reward

        stats.increment_stat(stats.Stat.PLAYERS_LEVELED)

        exp_for_next_level = gamerules.get_exp_for_next_level(player.level)
    stats.increment_stat(stats.Stat.MONEY_CREATED, level_up_reward)
    if level_up_reward > 0:
        if dueserverconfig.mute_level(ctx.channel) < 0:
            await imagehelper.level_up_screen(ctx, player, level_up_reward)
        else:
            util.logger.info("Won't send level up image - channel blocked.")
        rank = player.rank
        if 1 <= rank <= 10:
            await awards.give_award(ctx.channel, player, f"Rank{rank}", f"Attain rank {rank}.")


async def manage_quests(message, player: players.Player, spam_level):
    """
    Gives out quests!
    """

    channel = message.channel
    if time.time() - player.quest_day_start > quests.QUEST_DAY and player.quest_day_start != 0:
        player.quests_completed_today = 0
        player.quest_day_start = 0
        player.save()
        util.logger.info("%s (%s) daily completed quests reset", player.name_assii, player.id)

    # Testing
    if len(quests.get_server_quest_list(channel.guild)) == 0:
        quests.add_default_quest_to_server(message.guild)

    if (quest_time(player) and spam_level < SPAM_TOLERANCE) and (
        quests.has_quests(channel)
        and len(player.quests) < quests.MAX_ACTIVE_QUESTS
        and player.quests_completed_today < quests.MAX_DAILY_QUESTS
    ):
        player.last_quest = time.time()
        quest = quests.get_random_quest_in_channel(channel)
        new_quest = await quests.ActiveQuest.create(quest.q_id, player)
        stats.increment_stat(stats.Stat.QUESTS_GIVEN)
        player.quest_spawn_build_up = 1
        player.save()
        if dueserverconfig.mute_level(message.channel) < 0:
            await imagehelper.new_quest_screen(message, new_quest, player)
        else:
            util.logger.info("Won't send new quest image - channel blocked.")
        util.logger.info("%s has received a quest [%s]", player.name_assii, new_quest.q_id)


async def check_for_recalls(ctx, player):
    """
    Checks for weapons that have been recalled
    """

    current_weapon_id = player.equipped["weapon"]

    weapons_to_recall = [
        weapon_id
        for weapon_id in player.inventory["weapons"] + [current_weapon_id]
        if (weapons.get_weapon_from_id(weapon_id).id == weapons.NO_WEAPON_ID and weapon_id != weapons.NO_WEAPON_ID)
    ]

    if len(weapons_to_recall) == 0:
        return
    if current_weapon_id in weapons_to_recall:
        player.weapon = weapons.NO_WEAPON_ID
    player.inventory["weapons"] = [
        weapon_id for weapon_id in player.inventory["weapons"] if weapon_id not in weapons_to_recall
    ]
    recall_amount = sum([weapons.get_weapon_summary_from_id(weapon_id).price for weapon_id in weapons_to_recall])
    player.money += recall_amount
    player.save()
    stats.increment_stat(stats.Stat.MONEY_GENERATED, recall_amount, source="shop")
    await util.reply(
        ctx,
        (
            ":bangbang: "
            + ("One" if len(weapons_to_recall) == 1 else "Some")
            + " of your weapons has been recalled!\n"
            + "You get a refund of ``"
            + util.format_number(recall_amount, money=True, full_precision=True)
            + "``"
        ),
    )


async def check_for_missing_new_stats(player):
    """
    Check if the player have all the fields
    """
    if not hasattr(player, "prestige_level"):
        player.__setstate__({"prestige_level": 0})
    if not hasattr(player, "team"):
        player.__setstate__({"team": None})
    if not hasattr(player, "team_invites"):
        player.__setstate__({"team_invites": []})
    if not hasattr(player, "weapon_hidden"):
        player.__setstate__({"weapon_hidden": False})
    if not hasattr(player, "gamble_play"):
        player.__setstate__({"gamble_play": False})
    if not hasattr(player, "last_played"):
        player.__setstate__({"last_played": 0})


async def check_for_removed_stats(player):
    """
    Removes stats that were removed
    """
    if hasattr(player, "spam_detections"):
        delattr(player, "spam_detections")
    if hasattr(player, "additional_attributes"):
        delattr(player, "additional_attributes")
    if hasattr(player, "language"):
        delattr(player, "language")


async def on_message(message):
    player = players.find_player(message.author.id)
    spam_level = 100
    if player is not None:
        if not player.is_playing(message.author):
            return
        if quest_time(player) or progress_time(player):
            spam_level = get_spam_level(player, message.content)

        await player_message(message, player, spam_level)
        await manage_quests(message, player, spam_level)
        await check_for_recalls(message, player)
        await check_for_missing_new_stats(player)
        await check_for_removed_stats(player)


events.register_message_listener(on_message)
