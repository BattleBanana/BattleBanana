import json
import discord

from dueutil.game.configs import dueserverconfig
from dueutil import util

async def say(ctx, path, *args, **kwargs):
    #print(args)
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
        string = str(path).split(":")
        lan = dueserverconfig.get_language(ctx.guild.id)
        try:
            f = json.load(open("dueutil/game/configs/localization/"+str(lan)+"/"+string[0]+"/"+string[1]+".json", "r"))
        except (IndexError, FileNotFoundError):
            f = json.load(open("dueutil/game/configs/localization/en-gb/"+string[0]+"/"+string[1]+".json", "r"))
        msg = f[string[2]]

        if "[CMD_KEY]" in msg:
            prefix = dueserverconfig.server_cmd_key(ctx.guild.id)
            msg = msg.replace("[CMD_KEY]", prefix)
 
        return await channel.send((msg % args), **kwargs)
    except discord.Forbidden as send_error:
        raise util.SendMessagePermMissing(send_error)


def translate(ctx, path, *args):
    #print(args)
    #print(str(args))
    string = path.split(":")
    lan = dueserverconfig.get_language(ctx.guild.id)
    try:
        f = json.load(open("dueutil/game/configs/localization/"+str(lan)+"/"+string[0]+"/"+string[1]+".json", "r"))
    except (IndexError, FileNotFoundError):
        try:
            f = json.load(open("dueutil/game/configs/localization/en/"+string[0]+"/"+string[1]+".json", "r"))
        except KeyError:
            raise util.BattleBananaException(ctx.channel, "Translation error, missing English translation")
        #TODO other translations for non commands
        #raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "util:setlanguage:ERROR"))
    msg = f[string[2]]

    if "[CMD_KEY]" in msg:
            prefix = dueserverconfig.server_cmd_key(ctx.guild.id)
            msg = msg.replace("[CMD_KEY]", prefix)
    
    return (msg % args)


#def getLocale(ctx, player, path):
#    string = path.split(":")
#    lan = dueserverconfig.get_language(ctx.guild.id)
#    try:
#        f = json.load(open("dueutil/game/configs/localization/"+str(lan)+"/"+string[0]+"/"+string[1]+".json", "r"))
#    except (IndexError, FileNotFoundError):
#        return "n/a"
#    msg = f[string[2]]
#
#    if "[PLAYER]" in msg:
#        msg = msg.replace("[PLAYER]", str(player))
#    
#    return msg