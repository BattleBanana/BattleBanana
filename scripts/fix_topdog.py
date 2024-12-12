import os
import time
from threading import Thread

from dueutil import dbconn

# Remove "TopDog" from the awards for all players, except _id 999834114486177812

if __name__ == "__main__":
    db = dbconn.conn()
    start = time.time()
    players = db.get_collection("Player").find({"awards": "TopDog"})
    total = db.get_collection("Player").count_documents({})
    count = 0
    threads: list[Thread] = []

    print("Removing TopDog from all players...")

    for player in list(players):
        if player["_id"] == 999834114486177812:
            continue

        try:
            data = player.copy()
            data["awards"] = [award for award in data["awards"] if award != "TopDog"]

            db.get_collection("Player").update_one({"_id": player["_id"]}, {"$set": data})
        except Exception as e:
            print(f"Error removing TopDog from player {player['_id']}: {e}")

        count += 1
        print(f"Removed TopDog from {count}/{total} players", end="\r")

    os._exit(0)
