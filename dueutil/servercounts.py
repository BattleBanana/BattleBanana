import json

import generalconfig
from . import util

config = generalconfig.other_configs

CARBON_BOT_DATA = "https://www.carbonitex.net/discord/data/botdata.php"

DISCORD_LIST = "https://bots.ondiscord.xyz/bot-api/bots/464601463440801792/guilds"
BOTS_ORG = "https://discordbots.org/api/bots/464601463440801792/stats"
BOTS_GG = "https://discord.bots.gg/api/v1/bots/464601463440801792/stats"


async def update_server_count(shard):

    # await _carbon_server(shard)
    await _post_shard_count_bod(shard, DISCORD_LIST, config["discordBotsKey"])
    await _post_shard_count_dbl(shard, BOTS_ORG, config["discordBotsOrgKey"])
    #await _post_shard_count_dbgg(shard, BOTS_GG, config["discordBotsGGKey"])



async def _carbon_server(shard):

    headers = {"content-type": "application/json"}
    total_server_count = util.get_server_count()
    carbon_payload = {"key": config["carbonKey"], "servercount": total_server_count}
    async with shard.session.post(CARBON_BOT_DATA, data=json.dumps(carbon_payload), headers=headers) as response:
        util.logger.info("Carbon returned %s status for the payload %s" % (response.status, carbon_payload))


#async def _post_shard_count_dbgg(shard, site, key):
    # Seems like there is some form of standard?

#    headers = {"content-type": "application/json",
#               'authorization': key}
#    payload = {"server_count": util.get_server_count(),
#               "shard_id": shard.shard_id,
#               "shard_count": util.clients[0].shard_count}
#    async with shard.session.post(site, data=json.dumps(payload), headers=headers) as response:
#        util.logger.info(site+" returned %s for the payload %s" % (response.status, payload))


async def _post_shard_count_bod(shard, site, key):
    # Seems like there is some form of standard?

    headers = {"Content-Type": "application/json",
               'Authorization': key}
    payload = {"server_count": util.get_server_count(),
               "shard_id": shard.shard_id,
               "shard_count": util.clients[0].shard_count}
    async with shard.session.post(site, data=json.dumps(payload), headers=headers) as response:
        util.logger.info(site+" returned %s for the payload %s" % (response.status, payload))


async def _post_shard_count_dbl(shard, site, key):
    # Seems like there is some form of standard?

    headers = {"content-type": "application/json",
               'authorization': key}
    payload = {"server_count": len(shard.guilds),
               "shard_id": shard.shard_id,
               "shard_count": util.clients[0].shard_count}
    async with shard.session.post(site, data=json.dumps(payload), headers=headers) as response:
        util.logger.info(site+" returned %s for the payload %s" % (response.status, payload))
