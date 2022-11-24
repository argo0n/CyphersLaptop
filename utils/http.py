import aiohttp
from typing import Literal

async def get(url, res_method: Literal["read", "json"]):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if res_method == "read":
                return await response.read()
            elif res_method == "json":
                return await response.json()