"""
General game stats
"""

from collections import defaultdict
from datetime import datetime
from decimal import localcontext
from enum import Enum
from typing import Dict

from bson.decimal128 import Decimal128, create_decimal128_context

from dueutil import dbconn


class Stat(Enum):
    """Enum of all the stats we track"""

    MONEY_GENERATED = "moneygenerated"
    MONEY_REMOVED = "moneyremoved"
    MONEY_CREATED = "moneycreated"
    MONEY_TRANSFERRED = "moneytransferred"
    MONEY_TAXED = "moneytaxed"
    PLAYERS_LEVELED = "playersleveled"
    NEW_PLAYERS_JOINED = "newusers"
    QUESTS_GIVEN = "questsgiven"
    QUESTS_ATTEMPTED = "questsattempted"
    IMAGES_SERVED = "imagesserved"
    DISCOIN_RECEIVED = "discoinreceived"
    COMMANDS_USED = "commandsused"


def increment_stat(dueutil_stat: Stat, increment=1, **details):
    with localcontext(create_decimal128_context()) as ctx:
        increment = Decimal128(ctx.create_decimal(increment))

    inc_update_statement = {"count": increment}
    if details.get("source"):
        current_time = datetime.now().strftime("%Y-%m")
        path = f"details.{current_time}.{details["source"]}"

        inc_update_statement[path] = increment

    dbconn.conn()["stats"].update_one({"stat": dueutil_stat.value}, {"$inc": inc_update_statement}, upsert=True)


def get_stats() -> Dict[Stat, int]:
    stats_response = dbconn.conn()["stats"].find()
    stats = dict((Stat(stat["stat"]), stat["count"]) for stat in stats_response)
    return defaultdict(int, stats)
