from ... import dbconn, util
from ..helpers.misc import DueMap

muted_channels = DueMap()
command_whitelist = DueMap()
server_keys = dict()
lanaguage = dict()
DEFAULT_SERVER_KEY = "!"

"""
General config for a particular guild
"""


def update_server_config(guild, **update):
    dbconn.conn()["serverconfigs"].update({'_id': guild.id}, {"$set": update}, upsert=True)


def mute_level(channel):
    key = f"{channel.guild.id}/{channel.id}"
    if key in muted_channels:
        return muted_channels[key]
    return -1


def whitelisted_commands(channel):
    key = f"{channel.guild.id}/{channel.id}"
    if key in command_whitelist:
        return command_whitelist[key]


def set_command_whitelist(channel, command_list):
    # Todo fix blacklist
    global command_whitelist
    key = f"{channel.guild.id}/{channel.id}"
    if len(command_list) != 0:
        command_whitelist[key] = command_list
    elif key in command_whitelist:
        del command_whitelist[key]
    update_server_config(channel.guild, **{"command_whitelist": command_whitelist[channel.guild]})


def mute_channel(channel, **options):
    key = f"{channel.guild.id}/{channel.id}"
    prior_mute_level = mute_level(channel)
    new_level = options.get('mute_all', False)
    if prior_mute_level != new_level:
        muted_channels[key] = new_level
        update_server_config(channel.guild, **{"muted_channels": muted_channels[channel.guild]})
        return True
    return False


def unmute_channel(channel):
    key = f"{channel.guild.id}/{channel.id}"
    if key in muted_channels:
        del muted_channels[key]
        update_server_config(channel.guild, **{"muted_channels": muted_channels[channel.guild]})
        return True
    return False


def server_cmd_key(guild, *args):
    if len(args) == 1:
        server_keys[guild.id] = args[0]
        update_server_config(guild, **{"server_key": args[0]})
    else:
        if guild.id in server_keys:
            return server_keys[guild.id]
        else:
            return DEFAULT_SERVER_KEY


def set_language(guild, *args):
    lanaguage[guild.id] = args[0]
    update_server_config(guild, **{"language": args[0]})
    return


def get_language(guildID):
    if guildID in lanaguage:
        return lanaguage[guildID]
    else:
        return "en"


def _load():
    configs = dbconn.conn()["serverconfigs"].find()
    for config in configs:
        server_id = config["_id"]
        if "server_key" in config:
            server_keys[server_id] = config["server_key"]
        if "language" in config:
            lanaguage[server_id] = config["language"]
        if "muted_channels" in config:
            muted_channels[server_id] = config["muted_channels"]
        if "command_whitelist" in config:
            command_whitelist[server_id] = config["command_whitelist"]
    util.logger.info("%d guild keys, %d languages, %d muted channels, and %d whitelists loaded",
                     len(server_keys), len(lanaguage), len(muted_channels), len(command_whitelist))


_load()
