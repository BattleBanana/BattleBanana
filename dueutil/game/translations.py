import json
import discord

from dueutil.game.configs import dueserverconfig
from dueutil.game import game
from dueutil import util

async def say(ctx, player, args, **kwargs):
    #if type(channel) is str:
    #    # Guild/Channel id
    #    server_id, channel_id = channel.split("/")
    #    channel = util.get_guild(int(server_id)).get_channel(int(channel_id))
    #if asyncio.get_event_loop() != clients[0].loop:
    #    # Allows it to speak across shards
    #    clients[0].run_task(say, *((channel,) + args), **kwargs)
    #else:
    try:
        channel = ctx.channel
        string = str(args).split(":")
        lan = dueserverconfig.get_language(ctx.guild.id)
        f = json.load(open("dueutil/game/configs/localization/"+str(lan)+"/"+string[0]+"/"+string[1]+".json", "r"))
        msg = f[string[2]]

        if "[PLAYER]" in msg:
                msg = msg.replace("[PLAYER]", str(player))
 
        return await channel.send(msg, **kwargs)
    except discord.Forbidden as send_error:
        raise util.SendMessagePermMissing(send_error)


def getLocale(guild, player, thing):
    string = thing.split(":")
    lan = dueserverconfig.get_language(guild.id)
    f = json.load(open("dueutil/game/configs/localization/"+str(lan)+"/"+string[0]+"/"+string[1]+".json", "r"))
    msg = f[string[2]]

    if "[PLAYER]" in msg:
            msg = msg.replace("[PLAYER]", str(player))
    return msg