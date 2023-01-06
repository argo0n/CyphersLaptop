import asyncio
import io
import json
import os
import random
from io import BytesIO
from urllib import parse

import aiohttp
import filetype

import discord
import datetime
from typing import Union, Tuple, Optional

import typing
from discord.ext import menus
from dotenv import load_dotenv
from captcha.image import ImageCaptcha
import time
import functools

load_dotenv('credentials.env')


class DynamicUpdater:
    def __init__(self, channel: discord.TextChannel, update_every: int = 2):
        self.update_every = update_every
        self.last_updated = 0
        self.guild = channel.guild
        self.channel = channel
        self.message: discord.Message = None

    async def wait_until_update(self):
        if time.time() - self.last_updated < self.update_every:
            await asyncio.sleep(self.update_every - (time.time() - self.last_updated))

    async def update(self, content = None, *, embed = None, view = None, force: Optional[bool] = False):
        #print("updating with content amogus")
        if time.time() - self.last_updated < self.update_every and force is not True:
            #print("awaiting")
            pass
        else:
            if self.message is None:
                self.message = await self.channel.send(content=content, embed=embed, view=view)
                self.last_updated = round(time.time())
                #print("sent new message")
            else:
                try:
                    await self.message.edit(content=content, embed=embed, view=view)
                except discord.Forbidden:
                    pass
                except discord.HTTPException:
                    try:
                        new_message = await self.channel.send(content=content, embed=embed, view=view)
                    except discord.Forbidden:
                        pass
                    else:
                        self.message = new_message
                        self.last_updated = round(time.time())
                else:
                    self.last_updated = round(time.time())


class BaseEmbed(discord.Embed):
    def __init__(self, color: Union[discord.Color, int] = 0xffcccb, timestamp: datetime.datetime = None,
                 fields: Tuple[Tuple[str, str]] = (), field_inline: Optional[bool] = False, **kwargs):
        super().__init__(color=color, timestamp=timestamp or discord.utils.utcnow(), **kwargs)
        for n, v in fields:
            self.add_field(name=n, value=v, inline=field_inline)

    @classmethod
    def default(cls, ctx, **kwargs):
        instance = cls(**kwargs)
        instance.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        return instance

    @classmethod
    def to_error(cls, title: Optional[str] = "Error",
                color: Union[discord.Color, int] = discord.Color.red(), **kwargs):
        return cls(title=title, color=color, **kwargs)

def generate_random_hash():
    hash = random.getrandbits(128)

    return("%032x" % hash)

async def upload_file_to_bunnycdn(file: typing.Union[str, bytes, os.PathLike, io.BufferedIOBase], filename: str = None, directory: str = None, storage_zone_name="nogra"):
    """Uploads a file to a BunnyCDN Storage Zone."""
    if isinstance(file, io.IOBase):
        if not (file.seekable() and file.readable()):
            raise ValueError(f"File buffer {file!r} must be seekable and readable")
        file_data = file
    elif isinstance(file, (str, os.PathLike)):
        with open(file, "rb") as fp:
            file_data = fp.read()
    else:
        file_data = file
    if filename is None:
        if isinstance(fp, str):
            _, filename = os.path.split(fp)
        else:
            filename = getattr(fp, "name", None)
    else:
        filename = filename
    mime_type = filetype.guess_mime(file_data)
    if mime_type is None:
        mime_type = "application/octet-stream"
    headers = {
        "Content-Type": mime_type,
        "AccessKey": os.getenv('bunnystoragecredentials')
    }
    base_url = f"https://storage.bunnycdn.com/{storage_zone_name}/"
    commercial_base_url = f"https://cdn.nogra.xyz/"
    if directory is not None and directory != "":
        if directory[0] == "/":
            directory = directory[1:]
        if directory[-1] == "/":
            directory = directory[:-1]
        directory += f"/{filename}"
        url = base_url + parse.quote(directory)
        commercial_url = commercial_base_url + parse.quote(directory)
    else:
        url = base_url + parse.quote(filename)
        commercial_url = commercial_base_url + parse.quote(filename)


    async with aiohttp.ClientSession() as session:
        async with session.put(url, data=file_data, headers=headers) as resp:
            resp.raise_for_status()
        return commercial_url, resp.status

async def paste(text: str):
    base_url = "https://paste.nogra.xyz"
    upload_url = f"{base_url}/documents"
    async with aiohttp.ClientSession() as session:
        async with session.post(upload_url, data=text.encode("utf-8")) as resp:
            resp.raise_for_status()
            key = await resp.json()
            key = key.get('key', None)
            return f"{base_url}/{key}"


def range_char(start, stop):
    return [i.lower() for i in (chr(n) for n in range(ord(start), ord(stop) + 1))]

def range_char_from_letter(char):
    # use range_char to get return a range from a-e, f-j, etc
    if char in range_char('a', 'e'):
        return range_char('a', 'e')
    elif char in range_char('f', 'j'):
        return range_char('f', 'j')
    elif char in range_char('k', 'o'):
        return range_char('k', 'o')
    elif char in range_char('p', 't'):
        return range_char('p', 't')
    elif char in range_char('u', 'z'):
        return range_char('u', 'z')


def get_region_code(region: str):
    if region == "Asia Pacific":
        return "ap"
    elif region == "North America":
        return "na"
    elif region == "Europe":
        return "eu"
    elif region == "Korea":
        return "ko"


def get_tier_data():
    with open("assets/contenttiers.json", "r") as f:
        c = json.loads(f.read())
        f.close()
    return c