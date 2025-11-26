from discord import Message

_records: dict[int, list[Message]] = {}

_ratelimited_users = {}

# TODO: Make these configurable without code changes
RATELIMIT_SECONDS = 15
MESSAGE_WINDOW_SECONDS = 5
NUMBER_OF_MESSAGES = 5


def record_message(message: Message):
    """
    Record a message for banana guard monitoring.

    Returns True if the user has been ratelimited
    """
    user_id = message.author.id

    if user_id not in _records:
        _records[user_id] = []

    _records[user_id] = [
        msg
        for msg in _records[user_id]
        if (message.created_at - msg.created_at).total_seconds() <= MESSAGE_WINDOW_SECONDS
    ]
    _records[user_id].append(message)

    if len(_records[user_id]) >= NUMBER_OF_MESSAGES:
        _ratelimited_users[user_id] = message.created_at.timestamp() + RATELIMIT_SECONDS
        del _records[user_id]
        return True

    return False


def is_ratelimited(message: Message) -> bool:
    """
    Check if a user is currently ratelimited by banana guard.

    A user is ratelimited if they have triggered banana guard recently.
    """
    user_id = message.author.id

    if user_id in _ratelimited_users:
        if message.created_at.timestamp() < _ratelimited_users[user_id]:
            return True
        else:
            del _ratelimited_users[user_id]

    return False
