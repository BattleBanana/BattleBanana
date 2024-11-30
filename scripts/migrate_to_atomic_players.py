from threading import Thread

import jsonpickle
import pymongo

from dueutil import dbconn


def insert_players(players_to_insert):
    for player in players_to_insert:
        print(f"Inserting player {player.id}...")
        dbconn.insert_object(player.id, player)

    del players_to_insert

import time

if __name__ == "__main__":
    db = dbconn.conn()
    start = time.time()
    players = db.get_collection("Player").find().sort("_id")
    loaded_players = []
    threads: list[Thread] = []

    for player in players:
        if not player.get("data"):
            print(f"Player {player['_id']} has no data, skipping...")
            continue

        print(f"Loading player {player['_id']}...")
        loaded_player = jsonpickle.decode(player["data"])
        loaded_player.id = player["_id"]
        loaded_players.append(loaded_player)

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
    db.get_collection("Player").create_index([
        ("total_exp", pymongo.DESCENDING)
    ], background=True)

    db.get_collection("Player").create_index([
        ("level", pymongo.DESCENDING)
    ], background=True)

    db.get_collection("Player").create_index([
        ("money", pymongo.DESCENDING)
    ], background=True)
    print("Done.")
