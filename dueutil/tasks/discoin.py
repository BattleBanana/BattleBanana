import asyncio

import aiohttp
from discord import Embed
from discord.ext import tasks

import generalconfig as gconf
from dueutil import util
from dueutil.game import players, stats
from dueutil.game.stats import Stat

DISCOIN_SITE = "https://discoin.dev"
DISCOIN_API = DISCOIN_SITE + "/api"
CURRENCY_CODE = "BBT"
CURRENCIES = DISCOIN_API + "/currencies"
TRANSACTIONS = DISCOIN_API + "/transactions"
PENDING_TRANSACTIONS = TRANSACTIONS + "/pending"
AUTH_HEADERS = {"Authorization": "Bearer " + gconf.other_configs["discoinKey"]}
COMPLETED = "Completed"
REFUNDED = "Refunded"
MINIMUM_PAYOUT = 1
SERVER_ERROR_STATUS = 500
POLL_INTERVAL_SECONDS = 150
JSON_CONTENT_TYPE = "application/json"


class DiscoinError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(f"Discoin answered {status}: {message}")
        self.status = status
        self.message = message

    def is_server_error(self) -> bool:
        return self.status >= SERVER_ERROR_STATUS


class CurrencyNotListedError(LookupError):
    def __init__(self, abbreviation: str):
        super().__init__(f"Discoin does not list the currency {abbreviation}")


class Currency:
    def __init__(self, currency_id: str, abbreviation: str, name: str):
        self.id = currency_id
        self.abbreviation = abbreviation
        self.name = name


currencies = []
codes = []


def receipt_url(transaction_id):
    return f"{DISCOIN_SITE}/transactions/{transaction_id}"


def source_currency_code(transaction):
    return transaction["fromCurrency"]["abbreviation"]


def destination_currency_code(transaction):
    return transaction["toCurrency"]["abbreviation"]


async def read_response(response):
    if not response.ok:
        raise DiscoinError(response.status, await read_error_message(response))

    return await response.json()


async def read_error_message(response):
    if response.content_type == JSON_CONTENT_TYPE:
        error_body = await response.json()

        return error_body["message"]

    return response.reason


async def request_discoin(method, url, **request_options):
    async with aiohttp.ClientSession(timeout=util.HTTP_TIMEOUT) as session:
        async with session.request(method, url, **request_options) as response:
            return await read_response(response)


async def update_discoin():
    raw_currencies = await request_discoin("GET", CURRENCIES)
    new_currencies = [
        Currency(raw_currency["id"], raw_currency["abbreviation"], raw_currency["name"])
        for raw_currency in raw_currencies
    ]

    global currencies, codes
    currencies = sorted(new_currencies, key=lambda currency: currency.abbreviation)
    codes = [currency.abbreviation for currency in currencies]


def find_currency_id(abbreviation):
    for currency in currencies:
        if currency.abbreviation == abbreviation:
            return currency.id

    raise CurrencyNotListedError(abbreviation)


async def make_transaction(sender_id, amount, to):
    transaction_data = {
        "userId": str(sender_id),
        "fromCurrencyId": find_currency_id(CURRENCY_CODE),
        "toCurrencyId": find_currency_id(to),
        "amount": amount,
    }

    return await request_discoin("POST", TRANSACTIONS, json=transaction_data, headers=AUTH_HEADERS)


async def pending_transactions():
    query = {"currencyId": find_currency_id(CURRENCY_CODE)}

    return await request_discoin("GET", PENDING_TRANSACTIONS, params=query, headers=AUTH_HEADERS)


def transaction_url(transaction):
    return f"{TRANSACTIONS}/{transaction['id']}"


async def set_transaction_status(transaction, status):
    await request_discoin("PATCH", transaction_url(transaction), json={"status": status}, headers=AUTH_HEADERS)


async def mark_as_completed(transaction):
    async with aiohttp.ClientSession(timeout=util.HTTP_TIMEOUT) as session:
        async with session.patch(
            transaction_url(transaction), json={"status": COMPLETED}, headers=AUTH_HEADERS
        ) as response:
            return response.ok


async def refund_transaction(transaction):
    await set_transaction_status(transaction, REFUNDED)
    util.logger.warning("Reversed transaction: %s", transaction["id"])


@tasks.loop(seconds=POLL_INTERVAL_SECONDS)
async def process_transactions():
    if not util.clients[0].is_ready():
        return

    await update_discoin()
    util.logger.info("Processing Discoin transactions.")

    transactions = await pending_transactions()
    for transaction in transactions:
        await process_or_skip_transaction(transaction)


@process_transactions.error
async def restart_failed_polling(error):
    util.logger.error("Discoin polling failed, restarting in %s seconds", POLL_INTERVAL_SECONDS, exc_info=error)
    await asyncio.sleep(POLL_INTERVAL_SECONDS)
    process_transactions.restart()


async def process_or_skip_transaction(transaction):
    try:
        await process_transaction(transaction)
    except Exception:
        util.logger.exception(
            "Discoin transaction %s for user %s with payout %s failed",
            transaction["id"],
            transaction["userId"],
            transaction["payout"],
        )


async def process_transaction(transaction):
    client = util.clients[0]
    user_id = int(transaction["userId"])
    payout = int(transaction["payout"])

    player = players.find_player(user_id)
    if player is None or payout < MINIMUM_PAYOUT:
        await refund_transaction(transaction)
        client.run_task(notify_complete, user_id, transaction, failed=True)

        return

    if not await mark_as_completed(transaction):
        return

    await credit_completed_transaction(player, transaction)
    client.run_task(notify_complete, user_id, transaction)
    await log_received_transaction(user_id, transaction)


async def credit_completed_transaction(player, transaction):
    try:
        add_payout(player, int(transaction["payout"]))
    except Exception:
        await report_uncredited_transaction(transaction)
        raise


def add_payout(player, payout):
    stats.increment_stat(Stat.DISCOIN_RECEIVED, payout)
    player.money += payout
    player.save()


async def report_uncredited_transaction(transaction):
    message = "Discoin transaction %s is Completed on Discoin but user %s was not credited the payout of %s" % (
        transaction["id"],
        transaction["userId"],
        transaction["payout"],
    )
    util.logger.critical(message)
    await util.duelogger.error(message + f" <@{gconf.other_configs['owner']}>")


async def log_received_transaction(user_id, transaction):
    amount = float(transaction["amount"])
    payout = int(transaction["payout"])

    embed = Embed(
        title="Discion Transaction",
        description="Receipt ID: [%s](%s)" % (transaction["id"], receipt_url(transaction["id"])),
        type="rich",
        colour=gconf.DUE_COLOUR,
    )
    embed.add_field(name="User:", value=f"{user_id}")
    embed.add_field(
        name="Exchange",
        value="%.2f %s => %s %s" % (amount, source_currency_code(transaction), payout, CURRENCY_CODE),
        inline=False,
    )

    util.logger.info("Processed discoin transaction %s", transaction["id"])
    await util.say(gconf.discoin_channel, embed=embed)


async def notify_complete(user_id, transaction, failed=False):
    user_id = int(user_id)
    client = util.clients[0]
    user = await client.fetch_user(user_id)
    try:
        await user.create_dm()
        embed = Embed(
            title="Discion Transaction",
            description="Receipt ID: %s" % (transaction["id"]),
            type="rich",
            colour=gconf.DUE_COLOUR,
        )
        embed.set_footer(text="Keep the receipt in case something goes wrong!")

        if not failed:
            payout = int(transaction["payout"])
            amount = float(transaction["amount"])

            embed.add_field(
                name="Exchange amount (%s):" % source_currency_code(transaction),
                value="$" + util.format_number_precise(amount),
            )
            embed.add_field(
                name=f"Result amount ({CURRENCY_CODE}):",
                value=util.format_number(payout, money=True, full_precision=True),
            )
            embed.add_field(name="Receipt:", value=receipt_url(transaction["id"]), inline=False)
        else:
            embed.add_field(
                name=":warning: Your Discoin exchange has been reversed",
                value="To exchange to BattleBanana you must be a player and the amount has to be worth at least 1 BBT.",
            )

        try:
            await user.send(embed=embed)
        except Exception as error:
            util.logger.error(
                f"Could not notify the {'successful' if not failed else 'failed'} transaction to the user: %s", error
            )

    except Exception as error:
        util.logger.error("Could not notify discoin complete %s", error)
