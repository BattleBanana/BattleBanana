import os
import time
from threading import Thread

import jsonpickle
import pymongo

from dueutil import dbconn
from dueutil.game.players import Player


def insert_players(players_to_insert: list[Player]):
    conn = dbconn.conn()
    for player in players_to_insert:
        try:
            data = player.to_mongo()

            conn.get_collection("Player").update_one(
                {"_id": player.id}, {"$set": data, "$unset": {"data": 1}}, upsert=True
            )
        except Exception as e:
            print(f"Error inserting player {player.id}: {e}")


if __name__ == "__main__":
    db = dbconn.conn()
    start = time.time()
    players = db.get_collection("Player").find().sort("_id")
    loaded_players = []
    total = db.get_collection("Player").count_documents({})
    count = 0
    threads: list[Thread] = []

    print("Migrating players to atomic players...")
    for player in list(players):
        if not player.get("data"):
            continue

        try:
            loaded_player = jsonpickle.decode(player["data"])
        except Exception as e:
            print(f"Error loading player {player['_id']}: {e}")
            continue
        loaded_player.id = player["_id"]
        loaded_players.append(loaded_player)
        count += 1
        print(f"Loaded {count}/{total} players", end="\r")

        if len(loaded_players) >= 1000:
            # Start a new thread for inserting the batch
            t = Thread(target=insert_players, args=(loaded_players.copy(),))
            t.start()
            threads.append(t)
            loaded_players = []

    # Insert any remaining players
    if loaded_players:
        t = Thread(target=insert_players, args=(loaded_players.copy(),))
        t.start()
        threads.append(t)

    # Wait for all insert threads to finish
    print("Waiting for insert threads to finish...")
    for t in threads:
        t.join()

    print(f"Finished in {time.time() - start:.2f} seconds.")
    # Finished in 225.36 seconds with batches of 1000

    print("Creating new indexes...")
    # Add index on total_exp, level, money descending for leaderboard
    db.get_collection("Player").create_index([("total_exp", pymongo.DESCENDING)], background=True)

    db.get_collection("Player").create_index([("level", pymongo.DESCENDING)], background=True)

    db.get_collection("Player").create_index([("money", pymongo.DESCENDING)], background=True)
    print("Done.")
    os._exit(0)
