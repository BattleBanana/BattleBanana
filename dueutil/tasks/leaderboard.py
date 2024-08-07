import jsonpickle
from pymongo import CursorType

from dueutil import tasks, dbconn, util
from dueutil.game.players import Player

async def set_calculating_leaderboard(is_calculating: bool) -> None:
    dbconn.conn().get_collection("configs").update_one({"calculating_leaderboard": is_calculating}, upsert=True)

# @tasks.task(60*30)
async def calculate_leaderboard():
    util.logger.info("Calculating leaderboard")
    conn = dbconn.conn()

    set_calculating_leaderboard(True)

    players = conn.get_collection("Player")
    leaderboard = conn.get_collection("leaderboard")

    leaderboard.drop()
    async for document in players.find({"cursor_type": CursorType.EXHAUST}):
        player: Player = jsonpickle.decode(document["data"])

        leaderboard.insert_one({
            "_id": player.id,
            "name": player.name,
            "level": player.level,
            "exp": player.total_exp,
            "money": player.money,
            "quests_won": player.quests_won
        })

    set_calculating_leaderboard(False)

    util.logger.info("Finished calculating leaderboard")
