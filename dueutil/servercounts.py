import aiohttp
import json

import generalconfig
from . import util

config = generalconfig.other_configs

BOTS_ON_DISCORD = "https://bots.ondiscord.xyz/bot-api/bots/464601463440801792/guilds"
TOP_GG = "https://top.gg/api/bots/464601463440801792/stats"
RBL_GA = "https://discord.rovelstars.com/api/bots/464601463440801792/servers"
DISCORD_LABS = "https://bots.discordlabs.org/v2/bot/464601463440801792/stats"


async def update_server_count():
    await __post_shard_count_bod(BOTS_ON_DISCORD, config["botsOnDiscordKey"])
    await __post_shard_count_topgg(TOP_GG, config["topGGKey"])
    await __post_shard_count_discord_labs(DISCORD_LABS, config["discordLabsKey"])
    await __post_shard_count_rovel(RBL_GA, config["rovelStarsKey"])


async def __post_shard_count_rovel(site, key):
    payload = {"count": util.get_server_count()}

    await __post_server_count(site, key, payload)


async def __post_shard_count_bod(site, key):
    payload = {"guildCount": util.get_server_count()}

    await __post_server_count(site, key, payload)


async def __post_shard_count_discord_labs(site, key):
    payload = {"server_count": util.get_server_count(),
               "shard_count": util.get_shard_count()}

    await __post_server_count(site, key, payload)


async def __post_shard_count_topgg(site, key):
    payload = {"server_count": util.get_server_count(),
               "shard_count": util.get_shard_count()}

    await __post_server_count(site, key, payload)


async def __post_server_count(site, key, payload):
    headers = {"content-type": "application/json",
               "authorization": key}

    async with aiohttp.ClientSession() as session:
        async with session.post(site, data=json.dumps(payload), headers=headers) as response:
            util.logger.info("%s returned %s for the payload %s" % (site, response.status, payload))
        await session.close()