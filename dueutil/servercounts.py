import aiohttp
import json

import generalconfig
from . import util

config = generalconfig.other_configs

CARBON_BOT_DATA = "https://www.carbonitex.net/discord/data/botdata.php"

DISCORD_LIST = "https://bots.ondiscord.xyz/bot-api/bots/464601463440801792/guilds"
BOTS_ORG = "https://discordbots.org/api/bots/464601463440801792/stats"
BOTS_GG = "https://discord.bots.gg/api/v1/bots/464601463440801792/stats"
RBL_GA = "https://bots.rovelstars.ga/api/v1/bots/464601463440801792/stats"


async def update_server_count():
    await _post_shard_count_bod(DISCORD_LIST, config["discordBotsKey"])
    await _post_shard_count_dbl(BOTS_ORG, config["discordBotsOrgKey"])
    # await _post_shard_count_rovel(RBL_GA, config["rovelStarsKey"])


async def _post_shard_count_rovel(site, key):
    headers = {"Content-Type": "application/json",
               'Authorization': key}
    payload = {"guildCount": util.get_server_count()}
    async with aiohttp.ClientSession() as session:
        async with session.post(site, data=json.dumps(payload), headers=headers) as response:
            util.logger.info("%s returned %s for the payload %s" % (site, response.status, payload))
        await session.close()


async def _post_shard_count_bod(site, key):
    headers = {"Content-Type": "application/json",
               'Authorization': key}
    payload = {"guildCount": util.get_server_count()}
    async with aiohttp.ClientSession() as session:
        async with session.post(site, data=json.dumps(payload), headers=headers) as response:
            util.logger.info("%s returned %s for the payload %s" % (site, response.status, payload))
        await session.close()


async def _post_shard_count_dbl(site, key):
    headers = {"content-type": "application/json",
               'authorization': key}
    payload = {"server_count": util.get_server_count(),
               "shard_count": util.get_shard_count()}
    async with aiohttp.ClientSession() as session:
        async with session.post(site, data=json.dumps(payload), headers=headers) as response:
            util.logger.info("%s returned %s for the payload %s" % (site, response.status, payload))
        await session.close()
