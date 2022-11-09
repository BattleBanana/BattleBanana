import aiohttp
import json
from discord import Embed

import generalconfig as gconf
from dueutil import util, tasks
from . import players, stats
from .stats import Stat

# A quick discoin implementation.

DISCOIN = "https://discoin.zws.im"
DISCOINDASH = "https://dash.discoin.zws.im/#/transactions"
CURRENCY_CODE = "BBT"
# Endpoints
TRANSACTIONS = DISCOIN + "/transactions"
BOTS = DISCOIN + "/bots"
FILTER = f"?filter=to.id||eq||{CURRENCY_CODE}&filter=handled||eq||false"
headers = {"Authorization": gconf.other_configs["discoinKey"], "Content-Type": "application/json"}
handled = {"handled": True}
MAX_TRANSACTION = 500000


class Currency:
    def __init__(self, code: str, name: str, bot_name: str):
        self.code = code
        self.name = name
        self.bot_name = bot_name


class Bot:
    def __init__(self, name: str, currencies):
        self.name = name

        sorted_currencies = sorted(currencies, key=lambda k: k.code)
        self.currencies = sorted_currencies


bots = []
currencies = []
codes = []


async def get_raw_bots():
    async with aiohttp.ClientSession() as session:
        async with session.get(BOTS) as response:
            return await response.json()


async def update_discoin():
    try:
        raw_bots = await get_raw_bots()
        new_bots = []
        new_currencies = []

        for raw_bot in raw_bots:
            bot_currencies = []
            bot_name = raw_bot["name"]
            for raw_currency in raw_bot["currencies"]:
                currency = Currency(raw_currency["id"], raw_currency["name"], bot_name)

                bot_currencies.append(currency)
                new_currencies.append(currency)

            new_bots.append(Bot(bot_name, bot_currencies))

        sorted_bots = sorted(new_bots, key=lambda k: k.name)

        global bots, currencies, codes
        bots = sorted_bots
        currencies = new_currencies
        codes = [currency.code for currency in currencies]
    except Exception:
        pass


async def make_transaction(sender_id, amount, to, cfrom=CURRENCY_CODE):
    transaction_data = {
        "amount": amount,
        "from": cfrom,
        "to": to,
        "user": str(sender_id)
    }

    async with aiohttp.ClientSession(conn_timeout=10) as session:
        async with session.post(TRANSACTIONS,
                                data=json.dumps(transaction_data), headers=headers) as response:
            return await response.json()


async def reverse_transaction(user, currency_from, amount, id):
    util.logger.warning("Reversed transaction: %s", id)
    await make_transaction(user, amount, currency_from)


async def unprocessed_transactions():
    async with aiohttp.ClientSession() as session:
        async with session.get(TRANSACTIONS + FILTER, headers=headers) as response:
            return await response.json()


async def mark_as_completed(transaction):
    async with aiohttp.ClientSession() as session:
        async with session.patch(url=TRANSACTIONS + "/" + transaction['id'],
                                 data=json.dumps(handled), headers=headers) as response:
            return await response.json()


@tasks.task(timeout=150)
async def process_transactions():
    try:
        if not util.clients[0].is_ready():
            return
        await update_discoin()
        util.logger.info("Processing Discoin transactions.")
        try:
            unprocessed = await unprocessed_transactions()
        except Exception as exception:
            util.logger.error("Failed to fetch Discoin transactions: %s", exception)
            return

        if unprocessed is None:
            return

        client = util.clients[0]

        for transaction in unprocessed:
            if type(transaction) == dict:
                transaction_id = transaction.get('id')
                user_id = int(transaction.get('user'))
                payout = transaction.get('payout')
                if payout is None:
                    continue
                payout = int(payout)
                amount = float(transaction.get('amount'))

                source = transaction.get('from')
                source_id = source.get('id')

                player = players.find_player(user_id)
                if player is None or payout < 1:
                    await reverse_transaction(user_id, source_id, payout, transaction_id)
                    client.run_task(notify_complete, user_id, transaction, failed=True)
                    continue

                stats.increment_stat(Stat.DISCOIN_RECEIVED, payout)
                player.money += payout
                player.save()
                client.run_task(notify_complete, user_id, transaction)

                embed = Embed(title="Discion Transaction", description="Receipt ID: [%s](%s)" % (
                    transaction["id"], f"{DISCOINDASH}/{transaction['id']}/show"),
                              type="rich", colour=gconf.DUE_COLOUR)
                embed.add_field(name="User:", value=f"{user_id}")
                embed.add_field(name="Exchange", value="%.2f %s => %s %s" % (amount, source_id, payout, CURRENCY_CODE),
                                inline=False)

                util.logger.info("Processed discoin transaction %s", transaction_id)
                await util.say(gconf.discoin_channel, embed=embed)
    except Exception as e:
        util.logging.warn(e)


async def notify_complete(user_id, transaction, failed=False):
    await mark_as_completed(transaction)
    user_id = int(user_id)
    client = util.clients[0]
    user = await client.fetch_user(user_id)
    try:
        await user.create_dm()
        embed = Embed(title="Discion Transaction", description="Receipt ID: %s" % (transaction["id"]), type="rich",
                      colour=gconf.DUE_COLOUR)
        embed.set_footer(text="Keep the receipt in case something goes wrong!")

        if not failed:
            payout = int(transaction.get('payout'))
            amount = float(transaction.get('amount'))

            source = transaction.get('from')
            source_id = source.get('id')

            embed.add_field(name="Exchange amount (%s):" % source_id,
                            value="$" + util.format_number_precise(amount))
            embed.add_field(name=f"Result amount ({CURRENCY_CODE}):",
                            value=util.format_number(payout, money=True, full_precision=True))
            embed.add_field(name="Receipt:",
                            value="%s/%s/show" % (DISCOINDASH, transaction['id']),
                            inline=False)
        elif failed:
            embed.add_field(name=":warning: Your Discoin exchange has been reversed",
                            value="To exchange to BattleBanana you must be a player and the amount has to be worth at least 1 BBT.")

        try:
            await user.send(embed=embed)
        except Exception as error:
            util.logger.error(
                f"Could not notify the {'successful' if not failed else 'failed'} transaction to the user: %s", error)

    except Exception as error:
        util.logger.error("Could not notify discoin complete %s", error)
