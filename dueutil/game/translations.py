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
        string = str(path).split(":")
        lan = dueserverconfig.get_language(ctx.guild.id)
        try:
            f = json.load(open("dueutil/game/configs/localization/"+str(lan)+"/"+string[0]+"/"+string[1]+".json", "r"))
            msg = f[string[2]]
        except (IndexError, FileNotFoundError, KeyError):
            #try:
            f = json.load(open("dueutil/game/configs/localization/en/"+string[0]+"/"+string[1]+".json", "r"))
            msg = f[string[2]]
            #except (IndexError, FileNotFoundError, KeyError):
                #raise util.BattleBananaException(ctx.channel, "Translation error, missing English translation")
        
        if "[CMD_KEY]" in msg:
            prefix = dueserverconfig.server_cmd_key(ctx.guild)
            msg = msg.replace("[CMD_KEY]", prefix)
 
        return await ctx.reply((msg % args), **kwargs)
    except discord.Forbidden as send_error:
        raise util.SendMessagePermMissing(send_error)


def translate(ctx, path, *args):
    #print(args)
    #print(str(args))
    if ":" not in path:
        return (path % args)
    string = path.split(":")
    lan = dueserverconfig.get_language(ctx.guild.id)
    try:
        f = json.load(open("dueutil/game/configs/localization/"+str(lan)+"/"+string[0]+"/"+string[1]+".json", "r"))
        msg = f[string[2]]
    except (IndexError, FileNotFoundError, KeyError):
        #try:
        f = json.load(open("dueutil/game/configs/localization/en/"+string[0]+"/"+string[1]+".json", "r"))
        msg = f[string[2]]
        #except (IndexError, FileNotFoundError, KeyError):
            #raise util.BattleBananaException(ctx.channel, "Translation error, missing English translation")
        #TODO other translations for non commands
        #raise util.BattleBananaException(ctx.channel, translations.translate(ctx, "util:setlanguage:ERROR"))
    
    if "[CMD_KEY]" in msg:
            prefix = dueserverconfig.server_cmd_key(ctx.guild)
            msg = msg.replace("[CMD_KEY]", prefix)
    
    return (msg % args)


def translate_help(ctx, path, *args):
    string = path.split(":")
    lan = dueserverconfig.get_language(ctx.guild.id)
    try:
        f = json.load(open("dueutil/game/configs/localization/"+str(lan)+"/"+string[0]+"/"+string[1]+".json", "r"))
    except (IndexError, FileNotFoundError, KeyError):
        try:
            f = json.load(open("dueutil/game/configs/localization/en/"+string[0]+"/"+string[1]+".json", "r"))
        except (IndexError, FileNotFoundError, KeyError):
            if "[CMD_KEY]" in path:
                prefix = dueserverconfig.server_cmd_key(ctx.guild)
                path = path.replace("[CMD_KEY]", prefix)
            return path

    if "\n\nNote" in string[2]:
        string2 = string[2].split("\n\nNote")
        msg = f[string2[0]]
        msg += "\nNote:"+string2[1]
    else:
        msg = f[string[2]]
    
    if "[CMD_KEY]" in msg:
            prefix = dueserverconfig.server_cmd_key(ctx.guild)
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