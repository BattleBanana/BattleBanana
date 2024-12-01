import json
from datetime import datetime

import jsonpickle
import pymongo
from pymongo import MongoClient

db = None
config = {}
ASCENDING = pymongo.ASCENDING
DESCENDING = pymongo.DESCENDING


def conn():
    global db
    if db is None:
        db = MongoClient(username=config["user"], password=config["pwd"], host=config["host"]).dueutil

        return db
    else:
        return db


def insert_object(id, pickleable_object):
    if isinstance(id, str) and id.strip() == "":
        return

    if hasattr(pickleable_object, "to_mongo"):
        data = pickleable_object.to_mongo()

        conn()[type(pickleable_object).__name__].update_one(
            {"_id": id}, {"$set": data},upsert=True,
        )
    else:
        # TODO: Migrate all entities to new method of storage
        conn()[type(pickleable_object).__name__].update_one(
            {"_id": id}, {"$set": {"data": jsonpickle.encode(pickleable_object)}}, upsert=True
        )


def drop_and_insert(collection, data):
    connection = conn()
    connection.drop_collection(collection)
    connection[collection].insert_one(data)


def get_collection_for_object(object_class):
    return conn()[object_class.__name__]


def delete_objects(object_class, id_pattern):
    return conn()[object_class.__name__].delete_many({"_id": {"$regex": id_pattern}})


def delete_player(player):
    conn()["Player"].delete_one({"_id": player.id})


def update_guild_joined(count):
    month = datetime.now().strftime("%Y-%m")
    update_query = {"$inc": {"joined": 1} if count > 0 else {"left": 1}}
    conn()["GuildStats"].update_one({"_id": month}, update_query, upsert=True)


def blacklist_member(id: int, reason: str):
    conn()["Blacklist"].update_one({"_id": id}, {"$set": {"reason": reason}}, upsert=True)


def unblacklist_member(id: int):
    conn()["Blacklist"].delete_one({"_id": id})


def get_blacklist():
    return conn()["Blacklist"].find()


def _load_config():
    global config
    with open("dbconfig.json", encoding="utf-8") as config_file:
        config = json.load(config_file)


_load_config()
