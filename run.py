import asyncio
import inspect
import os
import queue
import sys
import time
import traceback
from threading import Thread

import aiohttp
import discord
import pymongo
import sentry_sdk

import generalconfig as gconf
from dueutil import (
    bananaguard,
    blacklist,
    dbconn,
    events,
    loader,
    permissions,
    servercounts,
    util,
)
from dueutil.game import emojis, players
from dueutil.game.configs import dueserverconfig
from dueutil.game.helpers import imagecache
from dueutil.permissions import Permission
from dueutil.tasks.votes import process_votes

sentry_sdk.init(
    gconf.other_configs.get("sentryAuth"),
    ignore_errors=["KeyboardInterrupt"],
    environment=gconf.other_configs.get("environment"),
)

MAX_RECOVERY_ATTEMPTS = 1000

STACKTRACE_FORMAT = "__Stack trace:__ ```py\n%s\n```"

stopped = False
bot_key = ""
client: discord.AutoShardedClient = None
clients = []
shard_names = []

start_time = time.time()
shard_time = 0
time_shown = False

# I'm not sure of the root cause of this error & it only happens once in months.
ERROR_OF_DEATH = "Timeout context manager should be used inside a task"

"""
BattleBanana: The most 1337 (worst) discord bot ever.
This bot is not well structured...
(c) MacDue & DeveloperAnonymous - All rights reserved
(Sections of this bot are MIT and GPL)
"""


class BattleBananaClient(discord.AutoShardedClient):
    """
    BattleBanana client
    """

    def __init__(self, **details):
        self.queue_tasks = queue.Queue()
        self.start_time = time.time()

        intents = discord.Intents.none()
        intents.emojis = True
        intents.members = True
        intents.guilds = True
        intents.guild_messages = True
        intents.message_content = True

        super().__init__(intents=intents, max_messages=None, **details)

    async def setup_hook(self):
        try:
            async_server = await asyncio.start_server(players.handle_client, "", gconf.other_configs["connectionPort"])
            server_port = async_server.sockets[0].getsockname()[
                1
            ]  # get port that the server is on, to confirm it started on 4000
            util.logger.info("Listening for data transfer requests on port %s!", server_port)
        except OSError as error:
            util.logger.error("Unable to start data transfer server: %s", error)

        asyncio.ensure_future(self.__check_task_queue(), loop=self.loop)

        process_votes.start()

    async def __check_task_queue(self):
        while True:
            try:
                task_details = self.queue_tasks.get(False)
                task = task_details["task"]
                args = task_details.get("args", ())
                kwargs = task_details.get("kwargs", {})
                if inspect.iscoroutinefunction(task):
                    await task(*args, **kwargs)
                else:
                    task(*args, **kwargs)
            except queue.Empty:
                pass
            await asyncio.sleep(5)

    def run_task(self, task, *args, **kwargs):
        """
        Runs a task from within this clients thread
        """
        self.queue_tasks.put({"task": task, "args": args, "kwargs": kwargs})

    def who_added(self, event: discord.AuditLogEntry):
        return event.target.id == self.user.id

    async def on_guild_join(self, guild: discord.Guild):
        await guild.chunk()
        server_count = util.get_server_count()
        dbconn.update_guild_joined(1)
        if server_count % 250 == 0:
            await util.say(
                gconf.announcement_channel,
                f":confetti_ball: I'm on __**{server_count} SERVERS**__ now!1!111!",
            )

        util.logger.info("Joined guild name: %s id: %s", guild.name, guild.id)
        try:
            await util.set_up_roles(guild)
        except discord.Forbidden:
            util.logger.warning("Unable to setup role for new server")
        server_stats = self.server_stats(guild)
        await util.duelogger.info(
            (
                "BattleBanana has joined the guild **"
                + util.ultra_escape_string(guild.name)
                + "**!\n"
                + "``Member count →`` "
                + str(guild.member_count)
                + "\n"
                + "``Bot members →``"
                + str(server_stats["bot_count"])
                + "\n"
                + ("**BOT SERVER**" if server_stats["bot_server"] else "")
            )
        )

        # Message to help out new guild admins.
        try:
            audit = None
            async for log in guild.audit_logs(action=discord.AuditLogAction.bot_add):
                if log.target.user == self.user:
                    audit = log
                    break

            await audit.user.send(
                ":wave: __Thanks for adding me!__\n"
                + "If you would like to customize me to fit your "
                + "guild take a quick look at the admins "
                + "guide at <https://battlebanana.xyz/howto/#adming>.\n"
                + "It shows how to change the command prefix here and set which "
                + "channels I or my commands can be used in (along with a bunch of other stuff)."
            )
        except (discord.Forbidden, AttributeError):
            for channel in guild.channels:
                if isinstance(channel, discord.TextChannel) and channel.permissions_for(guild.me).send_messages:
                    try:
                        await channel.send(
                            ":wave: __Thanks for adding me!__\n"
                            + "If you would like to customize me to fit your "
                            + "guild take a quick look at the admins "
                            + "guide at <https://battlebanana.xyz/howto/#adming>.\n"
                            + "It shows how to change the command prefix here, and set which "
                            + "channels I or my commands can be used in (along with a bunch of other stuff)."
                        )
                        break
                    except discord.Forbidden:
                        continue
        except Exception as error:
            util.logger.warning("Unable to send on join message: %s", error)

        # Update stats
        await servercounts.update_server_count()

    @staticmethod
    def server_stats(guild: discord.Guild):
        member_count = len(guild.members)
        bot_count = sum(member.bot for member in guild.members)
        bot_percent = int((bot_count / member_count) * 100)
        bot_server = bot_percent > 70
        return {
            "member_count": member_count,
            "bot_percent": bot_percent,
            "bot_count": bot_count,
            "bot_server": bot_server,
        }

    async def on_error(self, _, *args):
        ctx = args[0] if len(args) == 1 else None
        ctx_is_message = isinstance(ctx, discord.Message)
        error = sys.exc_info()[1]
        if ctx is None:
            await util.duelogger.error(
                "**BattleBanana experienced an error!**\n" + STACKTRACE_FORMAT % (traceback.format_exc())
            )
            util.logger.error("None message/command error: %s", error)
        elif isinstance(error, util.BattleBananaException):
            # A normal battlebanana user error
            try:
                if error.channel is not None:
                    await util.say(error.channel, error.get_message())
                else:
                    await util.say(ctx.channel, error.get_message())
            except util.SendMessagePermMissing:
                util.logger.warning("Unable to send Exception message")
            return
        elif isinstance(error, util.DueReloadException):
            loader.reload_modules()
            await util.say(error.channel, loader.get_loaded_modules())
            return
        elif isinstance(error, discord.Forbidden):
            if ctx_is_message:
                channel = ctx.channel
                if isinstance(error, util.SendMessagePermMissing):
                    util.logger.warning(
                        "Missing send permissions in channel %s (%s)",
                        channel.name,
                        channel.id,
                    )
                else:
                    try:
                        # Attempt to warn user
                        perms = ctx.channel.permissions_for(ctx.guild.me)
                        await util.say(
                            ctx.channel,
                            "The action could not be performed as I'm **missing permissions**! "
                            + "Make sure I have the following permissions:\n"
                            + "- Manage Roles "
                            + f"{emojis.CHECK_REACT if perms.manage_roles else emojis.CROSS_REACT};\n"
                            + "- Manage messages "
                            + f"{emojis.CHECK_REACT if perms.manage_messages else emojis.CROSS_REACT};\n"
                            + "- Embed links "
                            + f"{emojis.CHECK_REACT if perms.embed_links else emojis.CROSS_REACT};\n"
                            + "- Attach files "
                            + f"{emojis.CHECK_REACT if perms.attach_files else emojis.CROSS_REACT};\n"
                            + "- Read Message History "
                            + f"{emojis.CHECK_REACT if perms.read_message_history else emojis.CROSS_REACT};\n"
                            + "- Use external emojis "
                            + f"{emojis.CHECK_REACT if perms.external_emojis else emojis.CROSS_REACT};\n"
                            + "- Add reactions "
                            + f"{emojis.CHECK_REACT if perms.add_reactions else emojis.CROSS_REACT}",
                        )
                    except util.SendMessagePermMissing:
                        pass  # They've block sending messages too.
                    except discord.Forbidden:
                        pass
                return
        elif isinstance(error, discord.HTTPException):
            util.logger.error("Discord HTTP error: %s", error)
            if ctx_is_message:
                trigger_message = discord.Embed(title="Trigger", type="rich", color=gconf.DUE_COLOUR)
                trigger_message.add_field(name="Message", value=ctx.author.mention + ":\n" + ctx.content)
                await util.duelogger.error(
                    ("**Message/command triggred error!**\n" + STACKTRACE_FORMAT % (traceback.format_exc()[-1500:])),
                    embed=trigger_message,
                )
        elif isinstance(error, discord.DiscordServerError):
            util.logger.error("Discord Server error: %s", error)
            if ctx_is_message:
                trigger_message = discord.Embed(title="Trigger", type="rich", color=gconf.DUE_COLOUR)
                trigger_message.add_field(name="Message", value=ctx.author.mention + ":\n" + ctx.content)
                await util.duelogger.error(
                    ("**Message/command triggred error!**\n" + STACKTRACE_FORMAT % (traceback.format_exc()[-1500:])),
                    embed=trigger_message,
                )
            return
        elif isinstance(error, (aiohttp.ClientResponseError, aiohttp.ClientOSError)):
            if ctx_is_message:
                util.logger.error("%s: ctx from %s: %s", error, ctx.author.id, ctx.content)
            else:
                util.logger.error(error)
        elif isinstance(error, RuntimeError) and ERROR_OF_DEATH in str(error):
            util.logger.critical(
                "Something went very wrong and the error of death came for us: %s",
                error,
            )
            os._exit(1)
        elif isinstance(
            error,
            (OSError, aiohttp.ClientConnectionError, asyncio.exceptions.TimeoutError),
        ):  # 99% of time its just network errors
            util.logger.warning(error.message)
        elif isinstance(error, pymongo.errors.ServerSelectionTimeoutError):
            await util.duelogger.error(
                "Something went wrong and we disconnected from database " + f"<@{gconf.other_configs['owner']}>"
            )
            util.logger.critical("Something went wrong and we disconnected from database")
            os._exit(1)
        elif ctx_is_message:
            await util.say(ctx.channel, ":bangbang: **Something went wrong...**")
            trigger_message = discord.Embed(title="Trigger", type="rich", color=gconf.DUE_COLOUR)
            trigger_message.add_field(name="Message", value=ctx.author.mention + ":\n" + ctx.content)
            await util.duelogger.error(
                "**Message/command triggered error!**\n" + STACKTRACE_FORMAT % (traceback.format_exc()[-1500:]),
                embed=trigger_message,
            )

        # Log exception on sentry.
        sentry_sdk.capture_exception(error)
        traceback.print_exc()

    async def on_message(self, message: discord.Message):
        if (
            not self.is_ready()
            or message.author == self.user
            or message.author.bot
            or isinstance(message.channel, discord.abc.PrivateChannel)
            or blacklist.exists(message.author.id)
        ):
            return

        if bananaguard.is_ratelimited(message.author.id):
            return

        if bananaguard.record_message(message):
            await util.say(message.channel, ":no_entry: You are being rate limited. Please slow down.")
            return

        owner = message.author
        if owner.id == config["owner"] and not permissions.has_permission(owner, Permission.BANANA_OWNER):
            permissions.give_permission(owner, Permission.BANANA_OWNER)

        # what are you doing daughter - dev
        # fixing mac's shitty slow regex parser - me, theel
        message.content = (
            message.content.replace(f"<@!{self.user.id}>", dueserverconfig.server_cmd_key(message.guild), 1)
            if message.content.startswith(f"<@!{self.user.id}>")
            else message.content
        )
        message.content = (
            message.content.replace(f"<@{self.user.id}>", dueserverconfig.server_cmd_key(message.guild), 1)
            if message.content.startswith(f"<@{self.user.id}>")
            else message.content
        )

        await events.on_message_event(message)

    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if not self.is_ready():
            return

        member = after
        player = players.find_player(before.id)
        if player is not None:
            old_image = await player.get_avatar_url(member=before)
            new_image = await player.get_avatar_url(member=after)
            if old_image != new_image:
                imagecache.remove_cached_image(old_image)

            if member.guild.id == gconf.THE_DEN and any(role.id in gconf.DONOR_ROLES_ID for role in member.roles):
                player.donor = True
                player.save()

    async def on_guild_remove(self, guild: discord.Guild):
        if not self.is_ready() or guild is None:
            return

        for collection in dbconn.db.list_collection_names():
            if collection not in ("Player", "Topdogs"):
                dbconn.db[collection].delete_many({"_id": {"$regex": f"{guild.id}.*"}})
                dbconn.db[collection].delete_many({"_id": guild.id})
                dbconn.db[collection].delete_many({"_id": str(guild.id)})
        await util.duelogger.info(
            "BattleBanana has been removed from the guild "
            + f"**{util.ultra_escape_string(guild.name)}** ({guild.member_count} members)"
        )
        # Update stats
        dbconn.update_guild_joined(-1)
        await servercounts.update_server_count()

    async def on_ready(self):
        util.logger.info(
            "Bot (re)started after %.2fs & Shards started after %.2fs",
            time.time() - start_time,
            time.time() - shard_time,
        )
        await util.duelogger.bot(f"BattleBanana has *(re)*started\nBot version → ``{gconf.VERSION}``")

    async def on_shard_ready(self, shard_id: int):
        game = discord.Activity(
            name=f"battlebanana.xyz | shard {shard_id + 1}/{self.shard_count}",
            type=discord.ActivityType.watching,
        )
        try:
            await self.change_presence(activity=game, shard_id=shard_id)
        except Exception:
            util.logger.error("Failed to change presence")

        util.logger.info(
            "Shard %d (%s) ready",
            shard_id + 1,
            shard_names[shard_id],
        )


class ClientThread(Thread):
    """
    Thread for a client
    """

    def __init__(self, event_loop):
        self.event_loop = event_loop
        super().__init__()

    def run(self, level=1):
        asyncio.set_event_loop(self.event_loop)

        global client
        client = BattleBananaClient(chunk_guilds_at_startup=False)
        clients.append(client)
        try:
            asyncio.run(client.start(bot_key))
        except KeyboardInterrupt:
            client.loop.run_until_complete(client.logout())
            util.logger.warning("Bot has been stopped with CTRL + C")
        except Exception as client_exception:
            util.logger.exception(client_exception, exc_info=True)
            if level < MAX_RECOVERY_ATTEMPTS:
                util.logger.warning("Bot recovery attempted")
                self.event_loop = asyncio.new_event_loop()
                self.run(level + 1)
            else:
                util.logger.critical("FATAL ERROR: Recovery failed")
        finally:
            util.logger.critical("Bot is down & needs restarting!")
            # Should restart bot
            os._exit(1)


def run_bb():
    if not os.path.exists("assets/imagecache/"):
        os.makedirs("assets/imagecache/")
    loader.load_modules(packages=loader.GAME)
    if not stopped:
        loader.load_modules(packages=loader.COMMANDS)

        util.logger.info("Modules loaded after %.2fs", time.time() - start_time)
        global shard_time
        shard_time = time.time()

        client_thread = ClientThread(asyncio.new_event_loop())
        client_thread.start()

        while client is None:
            continue

        ### Tasks
        loop = asyncio.new_event_loop()

        try:
            loop.run_forever()
        except KeyboardInterrupt:
            util.logger.warning("Bot has been stopped with CTRL + C")
            os._exit(0)
        except Exception as client_exception:
            util.logger.exception(client_exception, exc_info=True)
            util.logger.critical("FATAL ERROR: Bot has crashed!")
            os._exit(1)


if __name__ == "__main__":
    config = gconf.other_configs
    bot_key = config["botToken"]
    shard_names = config["shardNames"]
    util.load(clients)
    asyncio.set_event_loop(asyncio.new_event_loop())
    run_bb()
