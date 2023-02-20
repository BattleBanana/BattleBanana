import asyncio
import time
from functools import wraps
import discord

from discord.enums import ButtonStyle

from dueutil.game import stats
from . import commandextras
from . import events, util, commandtypes
from . import permissions
from .game import players, emojis
from .game.configs import dueserverconfig
from .permissions import Permission

from discord import ui

extras = commandextras
IMAGE_REQUEST_COOLDOWN = 3

"""
BattleBanana random command system.
"""


def command(**command_rules):
    """A command wrapper for command functions"""

    # TODO: Include sender, timesent, etc in details

    def check(user, called):
        return permissions.has_permission(user, called.permission)

    def is_spam_command(ctx, called, *args):
        if called.permission < Permission.SERVER_ADMIN:
            return (sum(isinstance(arg, players.Player) for arg in args)
                    < len(ctx.raw_mentions) or ctx.mention_everyone
                    or '@here' in ctx.content or '@everyone' in ctx.content)
        return False

    def get_command_details(ctx, **details):
        details["timestamp"] = ctx.created_at
        details["author"] = players.find_player(ctx.author.id)
        details["server"] = ctx.guild
        details["server_id"] = ctx.guild.id
        details["server_name"] = ctx.guild.name
        details["server_name_clean"] = util.ultra_escape_string(ctx.guild.name)
        details["author_name"] = ctx.author.name
        details["author_name_clean"] = util.ultra_escape_string(ctx.author.name)
        details["channel"] = ctx.channel
        details["channel_name"] = ctx.channel.name
        details["channel_name_clean"] = util.ultra_escape_string(ctx.channel.name)
        return details

    def wrap(command_func):

        @wraps(command_func)
        async def wrapped_command(ctx, prefix, _, args, **details):
            name = command_func.__name__
            player = players.find_player(ctx.author.id)
            if player is None and wrapped_command.permission > Permission.DISCORD_USER:
                return await util.reply(ctx, f"Please run `{prefix}createaccount` if you want to use BattleBanana.")

            # Player has admin perms
            is_admin = permissions.has_permission(ctx.author, Permission.SERVER_ADMIN)
            if not is_admin and dueserverconfig.mute_level(ctx.channel) == 1:
                return True
            # Blacklist/whitelist
            command_whitelist = dueserverconfig.whitelisted_commands(ctx.channel)
            if command_whitelist is not None and not is_admin and name not in command_whitelist:
                if "is_blacklist" not in command_whitelist:
                    await util.reply(ctx, (":anger: That command is not whitelisted in this channel!\n"
                                           + " You can only use the following commands: ``"
                                           + ', '.join(command_whitelist) + "``."))
                else:
                    await util.reply(ctx, ":anger: That command is blacklisted in this channel!")
                return True
            # Do they have the perms for the command
            if check(ctx.author, wrapped_command):
                # Check args
                args_pattern = command_rules.get('args_pattern', "")
                # Send a copy of args to avoid possible issues.
                command_args = await determine_args(args_pattern, args.copy(), wrapped_command, ctx)
                if command_args is False:
                    # React ?
                    if not has_my_variant(name) or len(ctx.raw_mentions) > 0:
                        # Could not be a mistype for a personal my command
                        await ctx.add_reaction(emojis.QUESTION_REACT)
                        await util.reply(ctx, f":question: Wrong syntax was used, please run `{prefix}help {name}` for help.")
                    else:
                        # May have meant to call a personal command
                        personal_command_name = "my" + name
                        await events.command_event[personal_command_name](ctx, prefix, _, args, **details)
                elif not is_spam_command(ctx, wrapped_command, *args):
                    stats.increment_stat(stats.Stat.COMMANDS_USED)

                    # Run command
                    details["cmd_key"] = prefix
                    details["command_name"] = name
                    if name not in ("eval", "evaluate"):
                        await command_func(ctx, *command_args, **get_command_details(ctx, **details))
                    else:
                        key = dueserverconfig.server_cmd_key(ctx.guild)
                        command_string = ctx.content.replace(key, '', 1).replace(name, '').strip()
                        await command_func(ctx, command_string, **get_command_details(ctx, **details))
                else:
                    raise util.BattleBananaException(ctx.channel, "Please don't include spam mentions in commands.")
            else:
                # React X
                if not (permissions.has_permission(ctx.author, Permission.PLAYER) or permissions.has_special_permission(
                        ctx.author, Permission.BANNED)):
                    local_optout = not player.is_playing(ctx.author, local=True)
                    if local_optout:
                        await util.reply(ctx, "You are opted out. Use ``%soptinhere``!" % prefix)
                    else:
                        await util.reply(ctx, "You are opted out. Use ``%soptin``!" % prefix)
                else:
                    await ctx.add_reaction(emojis.CROSS_REACT)
            return True

        wrapped_command.is_hidden = command_rules.get('hidden', False)
        wrapped_command.permission = command_rules.get('permission', Permission.PLAYER)
        wrapped_command.aliases = tuple(command_rules.get('aliases', ()))
        # Add myX to X aliases
        if command_func.__name__.startswith("my"):
            wrapped_command.aliases += command_func.__name__[2:],

        events.register_command(wrapped_command)

        return wrapped_command

    return wrap


def has_my_variant(command_name):
    """
    Returns if a command has a personal mycommand variant
    e.g. !info and !myinfo
    """
    return "my" + command_name.lower() in events.command_event


def replace_aliases(command_list):
    for index, given_command_name in enumerate(command_list):
        command_func = events.get_command(given_command_name)
        if command_func is None:
            continue
        command_name = command_func.__name__
        if command_name != given_command_name:
            # Fix aliases in whitelist
            command_list[index] = command_name
        if has_my_variant(command_name):
            command_list.append("my" + command_name)  # To avoid confuzzing
    return command_list


def imagecommand():
    def wrap(command_func):
        @ratelimit(slow_command=True, cooldown=IMAGE_REQUEST_COOLDOWN, error=":cold_sweat: Please don't break me!")
        @wraps(command_func)
        async def wrapped_command(ctx, *args, **kwargs):
            await util.typing(ctx.channel)
            await asyncio.ensure_future(command_func(ctx, *args, **kwargs))

        return wrapped_command

    return wrap


def ratelimit(**command_info):
    def wrap(command_func):
        @wraps(command_func)
        async def wrapped_command(ctx, *args, **details):
            player = details["author"]
            if player is None:
                return
            command_name = details["command_name"]
            if command_info.get('save', False):
                command_name += "_saved_cooldown"
            now = int(time.time())
            time_since_last_used = now - player.command_rate_limits.get(command_name, 0)
            if time_since_last_used < command_info["cooldown"]:
                error = command_info["error"]
                if "[COOLDOWN]" in error:
                    time_to_wait = command_info["cooldown"] - time_since_last_used
                    error = error.replace("[COOLDOWN]", util.display_time(time_to_wait))
                await util.reply(ctx, error)
            else:
                player.command_rate_limits[command_name] = now
                await command_func(ctx, *args, **details)

        return wrapped_command

    return wrap


DEFAULT_TIMEOUT = 10
class ConfirmInteraction(ui.View):
    def __init__(self, author = None, timeout = DEFAULT_TIMEOUT):
        self._author = author
        super().__init__(timeout=timeout)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self._author.id:
            return True

        await interaction.response.send_message('You cannot use this interaction!', ephemeral=True)

        return False

    async def start(self):
        has_timed_out = await self.wait()
        if has_timed_out:
            return "cancel"
        return self.value
    
    @ui.button(label='Confirm', style=ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: ui.Button):
        self.value = "confirm"
        await interaction.response.send_message("Gotcha! Doing it chief.", ephemeral=True)
        self.stop()

    @ui.button(label='Cancel', style=ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: ui.Button):
        self.value = "cancel"
        await interaction.response.send_message("Understood! I won't do it.", ephemeral=True)
        self.stop()

def require_cnf(warning):
    # Checks the user confirms the command.
    def wrap(command_func):
        @wraps(command_func)
        async def wrapped_command(ctx, *args, **details):
            interaction = ConfirmInteraction(ctx.author)
            message = await util.reply(ctx, f"Are you sure?! {warning}", view=interaction)

            response = await interaction.start()
            if response == "confirm":
                if args is None:
                    await command_func(ctx, *args, **details)
                else:
                    await command_func(ctx, **details)
            
            await util.delete_message(message)

        return wrapped_command

    return wrap


def parse(command_message):
    """A basic command parser with support for escape strings.
    I don't think one like this exists that is not in a package
    that adds a lot more stuff I don't want.
    
    This is meant to be like a shell command lite style.
    
    Supports strings in double quotes & escape strings
    (e.g. \" for a quote character)
    
    The limitations of this parser are 'fixed' in determine_args
    that can guess where quotes should be most times.
    """

    key = dueserverconfig.server_cmd_key(command_message.guild)
    command_string = command_message.content.replace(key, '', 1)
    user_mentions = command_message.raw_mentions
    escaped = False
    is_string = False
    args = []
    current_arg = ''

    def replace_mentions():
        nonlocal user_mentions, current_arg
        for mention in user_mentions:  # Replace mentions
            mention = str(mention)
            if mention in current_arg and len(current_arg) - len(mention) < 6:
                current_arg = mention
                del user_mentions[user_mentions.index(int(mention))]

    def add_arg():
        nonlocal current_arg, args
        if len(current_arg) > 0:
            replace_mentions()
            args = args + [current_arg]
            current_arg = ""

    for char_pos in range(0, len(command_string) + 1):
        current_char = command_string[char_pos] if char_pos < len(command_string) else ' '
        if char_pos < len(command_string) and (not current_char.isspace() or is_string):
            if not escaped:
                if current_char == '\\' and not (current_char.isspace() or current_char.isalpha()):
                    escaped = True
                    continue
                elif current_char == '"':
                    is_string = not is_string
                    add_arg()
                    continue
            else:
                escaped = False
            current_arg += command_string[char_pos]
        else:
            add_arg()

    if is_string:
        raise util.BattleBananaException(command_message.channel, "Unclosed string in command!")

    if len(args) > 0:
        return key, args[0], args[1:]
    else:
        return key, "", []

async def determine_args(pattern: str, args, called, ctx):
    PATTERN_MODIFIERS = ['*','?']
    if pattern is None or pattern == '':
        if len(args) == 0:
            return args
        else:
            return False
        
    #helper function
    def check_arg(pattern_index : int, arg_index : int, mod = False):# -> Tuple[bool,int] | Tuple[list,int]:
        ret_args = []
        #no mods (and bitches)
        if not mod:
            try:
                assert arg_index < len(args) #are args available?
                arg = commandtypes.parse_type(pattern[pattern_index],args[arg_index],called = called,ctx = ctx)
                if arg is False:
                    ret_args = False
                else:
                    ret_args.append(arg)
                    arg_index+=1
            except AssertionError: #error, missing compulsory args
                ret_args = False
        else:
            mod = pattern[pattern_index+1]
            #no args left to parse,skip parsing
            if arg_index >= len(args):
                pass
            elif mod == '?':
                arg = commandtypes.parse_type(pattern[pattern_index],args[arg_index],called = called,ctx = ctx)
                if arg is False:
                    ret_args = False
                else:
                    ret_args.append(arg)
                    arg_index+=1
            elif mod == '*':
                while arg_index < len(args):
                    arg = commandtypes.parse_type(pattern[pattern_index],args[arg_index],called = called,ctx = ctx)
                    if arg is False:
                        break
                    else:
                        ret_args.append(arg)
                        arg_index+=1
        return ret_args,arg_index
                        
    checked_args = []
    pattern_index = 0
    arg_index = 0
    while pattern_index < len(pattern):
        #can a modifier exist?
        if pattern_index+1 < len(pattern):
            #check arg depending on pattern type
            if pattern[pattern_index+1] in PATTERN_MODIFIERS:
                arg_val,arg_index = check_arg(pattern_index,arg_index,True)
                pattern_index+=1
            else:
                arg_val,arg_index = check_arg(pattern_index,arg_index)
        #definitely a normal pattern type
        else: 
            arg_val,arg_index = check_arg(pattern_index,arg_index)
            
        #error parsing arg
        if arg_val is False:
            return False
        checked_args.extend(arg_val)
        pattern_index+=1

    return checked_args