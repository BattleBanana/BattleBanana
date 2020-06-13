import aiohttp, asyncio
import generalconfig as gconf
import json, jsonpickle
from discord import Embed

from . import players, stats
from .stats import Stat
from dueutil import util, tasks, dbconn

import traceback

VOTE_REWARD = 25000
WE_VOTE_REWARD = 40000

@tasks.task(timeout=300)
async def process_votes():
    while not util.clients[0].is_ready():
        pass
    
    util.logger.info("Processing Votes.")

    try:
        votes = dbconn.conn()["Votes"].find()
    except Exception as exception:
        util.logger.error("Failed to fetch votes: %s", exception)
        return

    if votes is None:
        return

    client = util.clients[0]

    for vote in votes:
        if type(vote) == dict:
            vote_id = vote.get("_id")
            user_id = vote.get("user")
            isWeekend = vote.get("weekend")
            date = vote.get("date")

            player = players.find_player(user_id)
            if player is None:
                dbconn.conn()["Votes"].delete_one({'_id': vote_id})
                continue
            
            reward = WE_VOTE_REWARD if isWeekend else VOTE_REWARD
            player.money += reward
            player.save()

            client.run_task(notify_complete, user_id, vote, reward)
            
            dbconn.conn()["Votes"].delete_one({'_id': vote_id})

            embed = Embed(title="New vote", type="rich", colour=gconf.DUE_COLOUR)
            embed.add_field(name="Voter: ", value=user_id)
            embed.add_field(name="Reward: ", value=util.format_number(reward, money=True))
            embed.add_field(name="Date: ", value=date)

            util.logger.info("Processed vote for %s", user_id)
            await util.say(gconf.votes_channel, embed=embed)


async def notify_complete(user_id, vote, reward):
    client = util.clients[0]

    try:
        user = await client.fetch_user(user_id)
        await user.create_dm()

        embed = Embed(title="Vote notification", type="rich", colour=gconf.DUE_COLOUR)
        embed.set_footer(text="Thank you for voting!")
        
        embed.add_field(name="Reward: ", value=util.format_number(reward, money=True))
        embed.add_field(name="Date: ", value=vote.get("date"))

        try:
            await util.say(user, embed=embed)
        except Exception as error:
            util.logger.error("Could not notify the successful transaction to the user: %s", error)

    except Exception as error:
        util.logger.error("Could not notify vote complete %s", error)
        traceback.print_exc()