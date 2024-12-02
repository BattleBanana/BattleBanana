"""
Global vars
"""

import json
import sys
from datetime import datetime

DUE_COLOUR = 9819069
COMMANDER_ROLE = "Banana Commander"
OPTOUT_ROLE = "Banana Optout"

# Colour defaults to colour
DUE_ROLES = ({"name": COMMANDER_ROLE}, {"name": OPTOUT_ROLE, "colour": 0})

trello_api_key = ""
trello_api_token = ""
trello_board = ""

# Silly things:
DEAD_BOT_ID = 464601463440801792
DUE_START_DATE = datetime.fromtimestamp(1531454400)

# Misc
THE_DEN = 431932271604400138
DONOR_ROLES_ID = (496056504735105054, 588946317586464769)
# Cap for all things. Quests, weapons and wagers.
THING_AMOUNT_CAP = 200

BOT_INVITE = "https://battlebanana.xyz/invite"

SUPPORTED_FILES = ["jpeg", "jpg", "png", "gif", "webp"]

VERSION = "Release 4.2.0"


def load_config_json():
    try:
        with open("battlebanana.json") as config_file:
            return json.load(config_file)
    except Exception as exception:
        sys.exit("Config error! %s" % exception)


other_configs: dict = load_config_json()

#### LOADED FROM battlebanana.json config
error_channel = other_configs.get("errorChannel")
bug_channel = other_configs.get("bugChannel")
log_channel = other_configs.get("logChannel")
feedback_channel = other_configs.get("feedbackChannel")
votes_channel = other_configs.get("votes")
discoin_channel = other_configs.get("transactions")
announcement_channel = other_configs.get("announcementsChannel")
shard_names = other_configs.get("shardNames")
vpn_config = other_configs.get("vpn", None)  # Optional
