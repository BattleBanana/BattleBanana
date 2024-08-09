from datetime import datetime
import jsonpickle
from pymongo import CursorType

from dueutil import tasks, dbconn, util
from dueutil.game.players import Player

async def set_calculating_leaderboard(is_calculating: bool) -> None:
    dbconn.conn().get_collection("configs").update_one({"calculating_leaderboard": is_calculating}, upsert=True)

# @tasks.task(60*30)
async def calculate_leaderboard():
    t = datetime.now().timestamp()
    util.logger.info("Updating leaderboard")
    conn = dbconn.conn()

    set_calculating_leaderboard(True)

    players = conn.get_collection("Player")
    leaderboard = conn.get_collection("leaderboard")

    leaderboard.drop()
    to_insert = []
    async for document in players.find({"cursor_type": CursorType.EXHAUST}):
        try:
            player: Player = jsonpickle.decode(document["data"])

            to_insert.append({
                "_id": player.id,
                "name": player.name,
                "level": player.level,
                "exp": player.total_exp,
                "money": player.money,
                "quests_won": player.quests_won
            })

            if len(to_insert) % 1000 == 0:
                leaderboard.insert_many(to_insert)
                to_insert.clear()

        except Exception as e:
            util.logger.error(f"Error loading player {document['_id']} for leaderboard: {e}")

    set_calculating_leaderboard(False)

    util.logger.info(f"Leaderboard updated in {datetime.now().timestamp() - t}")
