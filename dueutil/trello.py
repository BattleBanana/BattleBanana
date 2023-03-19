"""
Some basic trello actions
"""

import aiohttp


class TrelloClient:
    """
    A very basic trello client with just the stuff I need &
    nothing extra
    """

    base_request = "https://trello.com/1/"

    def __init__(self, api_key, api_token):
        self.api_key = api_key
        self.api_token = api_token
        self.key_and_token = {"key": api_key, "token": api_token}

    async def get_boards(self):
        return await self.fetch_json("members/me/boards")

    async def get_lists(self, board_id):
        return await self.fetch_json(f"boards/{board_id}/lists")

    async def fetch_json(self, url):
        async with aiohttp.ClientSession() as session:
            async with session.get(self.base_request + url, params=self.key_and_token) as response:
                json = await response.json()
                return json

    async def get_labels(self, board_id):
        return await self.fetch_json(f"boards/{board_id}/labels")

    async def add_card(self, board_url, list_name, name, desc, labels=None):
        """
        The main thing I need. Adding cards.

        This just used the board URL and and the names of lists etc
        since that is easier to work with
        """

        description = desc

        for board in await self.get_boards():
            if board["url"] == board_url:
                lists = await self.get_lists(board["id"])

                for trello_list in lists:
                    if trello_list["name"].lower() == list_name.lower():
                        label_ids = ""

                        if labels is not None:
                            labels = list(map(str.lower, labels))
                            board_labels = await self.get_labels(board["id"])

                            label_ids_list = [label["id"] for label in board_labels if label["name"].lower() in labels]
                            if len(label_ids_list) != len(labels):
                                raise ValueError("Could not find labels")
                            label_ids = ",".join(label_ids_list)

                        args = {"name": name, "desc": description, "idList": trello_list["id"], "idLabels": label_ids}

                        card_url = "cards"

                        async with aiohttp.ClientSession() as session:
                            async with session.post(
                                self.base_request + card_url, params=self.key_and_token, data=args
                            ) as response:
                                result = await response.json()
                                if "shortUrl" in result:
                                    return result["shortUrl"]
                                raise RuntimeError("Failed to add card!")
                raise ValueError("List not found")
        raise ValueError("Board not found")
