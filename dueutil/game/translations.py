import json
import discord

from dueutil.game.configs import dueserverconfig
from dueutil.game import game
from dueutil import util

#async def sayT(channel, player, *args, **kwargs):
#    if type(channel) is str:
#        # Guild/Channel id
#        server_id, channel_id = channel.split("/")
#        channel = util.get_guild(int(server_id)).get_channel(int(channel_id))
#    #if asyncio.get_event_loop() != clients[0].loop:
#    #    # Allows it to speak across shards
#    #    clients[0].run_task(say, *((channel,) + args), **kwargs)
#    #else:
#    try:
#        string = str(args).split(":")
#        lan = await dueserverconfig.get_language(await server_id)
#        f = json.load(open("dueutil/game/configs/localization/"+str(lan)+"/"+string[0]+"/"+string[1]+".json", "r"))
#        msg = f[string[2]]
#
#        if "{{player}}" in msg:
#                msg.replace("{{player}}", player)
# 
#        return await channel.send(msg, **kwargs)
#    except discord.Forbidden as send_error:
#        raise util.SendMessagePermMissing(send_error)