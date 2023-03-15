import gc
import secrets
from typing import List

from dueutil import dbconn


class PromoCode:
    def __init__(self, code, price):
        self.code: str = code
        self.price: float = price


codes: List[PromoCode] = []


def __new_code():
    return f"BATTLEBANANA_{secrets.token_hex(5).upper()}"


def generate(price, quantity=1):
    new_codes: List[PromoCode] = []

    for _ in range(quantity):
        code = __new_code()
        while exists(code):
            code = __new_code()

        new_codes.append(PromoCode(code, price))

    dbconn.conn()["Codes"].insert_many([{"code": code.code, "price": code.price} for code in new_codes])
    codes.extend(new_codes)

    gc.collect()

    return new_codes


def exists(code: str):
    return any([code == c.code for c in codes])


def redeem(code: str):
    """
    Remove the code from the database and return the price

    :param code: The code to redeem
    :return: The price of the code
    """
    for c in codes:
        if c.code == code:
            codes.remove(c)
            dbconn.conn()["Codes"].delete_one({"code": c.code})
            return c.price

    return None


def get_paged(page: int, per_page: int):
    if len(codes) == 0:
        return []

    if page * 30 >= len(codes):
        return None

    return codes[(page - 1) * per_page : page * per_page]


def _load():
    global codes
    codes = [PromoCode(c["code"], c["price"]) for c in dbconn.conn()["Codes"].find()]


_load()
