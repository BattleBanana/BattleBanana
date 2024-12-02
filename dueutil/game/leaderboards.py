import threading
import time

from cachetools.func import ttl_cache
from discord import Guild

from dueutil import dbconn, events, util
from dueutil.game.players import Player

UPDATE_INTERVAL = 3600 / 12

last_leaderboard_update = 0
update_lock = threading.Lock()


def calculate_level_leaderboard():
    db = dbconn.conn()
    players = db.get_collection("Player").find({}, {"_id": 1}).sort("total_exp", -1)
    ranks = []
    for rank, player in enumerate(players):
        if player["_id"] == util.gconf.DEAD_BOT_ID:
            continue

        ranks.append({"rank": rank + 1, "player_id": player["_id"]})

    if len(ranks) > 0:
        db.drop_collection("levels")
        db.get_collection("levels").create_index("rank", unique=True)
        db.get_collection("levels").create_index("player_id", unique=True)
        db.get_collection("levels").insert_many(ranks, ordered=False)

    get_leaderboard.cache_clear()


@ttl_cache(maxsize=16, ttl=UPDATE_INTERVAL)
def get_leaderboard(rank_name: str):
    leaderboard = dbconn.conn().get_collection(rank_name).find().sort("rank")
    return [entry["player_id"] for entry in leaderboard]


def get_local_leaderboard(guild: Guild, rank_name: str):
    leaderboard = get_leaderboard(rank_name)
    member_ids = [member.id for member in guild.members]
    rankings = [
        entry
        for entry in leaderboard
        if entry in member_ids
    ]
    return rankings


def get_rank(player: Player, rank_name: str, guild: Guild = None):
    if guild is not None:
        # Local
        rankings = get_local_leaderboard(guild, rank_name)
    else:
        rankings = get_leaderboard(rank_name)
    try:
        return rankings.index(player.id) + 1
    except (ValueError, IndexError):
        return -1


async def update_leaderboards(_):
    global last_leaderboard_update
    with update_lock:
        if time.time() - last_leaderboard_update >= UPDATE_INTERVAL:
            last_leaderboard_update = time.time()
            leaderboard_thread = threading.Thread(target=calculate_level_leaderboard)
            leaderboard_thread.start()
            util.logger.info("Global leaderboard updated!")


events.register_message_listener(update_leaderboards)
calculate_level_leaderboard()
