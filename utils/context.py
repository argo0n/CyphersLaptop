import discord
import contextlib
import asyncio
from typing import Iterable, List, Optional
from discord.ext import commands
from utils.format import box

class DVVTcontext(commands.Context):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def checkmark(self):
        with contextlib.suppress(discord.HTTPException):
            await self.message.add_reaction("<:DVB_checkmark:955345523139805214>")

    async def crossmark(self):
        with contextlib.suppress(discord.HTTPException):
            await self.message.add_reaction("<:DVB_crossmark:955345521151737896>")

    async def send_interactive(
        self, messages: Iterable[str], box_lang: str = None, timeout: int = 15
    ) -> List[discord.Message]:
        messages = tuple(messages)
        ret = []

        for idx, page in enumerate(messages, 1):
            page = box(page, lang=box_lang) if box_lang is not None else page
            msg = await self.send(page)
            ret.append(msg)
            n_remaining = len(messages) - idx
            if n_remaining > 0:
                if n_remaining == 1:
                    plural = ""
                    is_are = "is"
                else:
                    plural = "s"
                    is_are = "are"
                query = await self.send("There {} still {} message{} remaining. Type `more` to continue.".format(is_are, n_remaining, plural))
                def check(message):
                    return message.author == self.author and message.channel == self.channel and message.content.lower() == 'more'
                try:
                    resp = await self.bot.wait_for("message", check=check, timeout=timeout)
                except asyncio.TimeoutError:
                    with contextlib.suppress(discord.HTTPException):
                        await query.delete()
                    break
                else:
                    try:
                        await self.channel.delete_messages((query, resp))
                    except (discord.HTTPException, AttributeError):
                        with contextlib.suppress(discord.HTTPException):
                            await query.delete()
        return ret

    async def help(self, command = None):
        """
        Sends help message for the invoked command if a command isn't specified.
        """
        invoke = command if command is not None else self.command
        await self.send_help(invoke)

    async def maybe_reply(self, content=None, mention_author=False, **kwargs):
        """
        Replies if there is a message in between the command invoker and the bot's message.
        """
        await asyncio.sleep(0.05)
        with contextlib.suppress(discord.HTTPException):
            if getattr(self.channel,"last_message", False) != self.message:
                return await self.reply(content, mention_author=mention_author, **kwargs)
        return await self.send(content, **kwargs)

    async def confirmation(self, message, *, cancel_message = None, timeout=15, delete_after=True, delete_delay=0):
        """
        An interactive reaction confirmation dialog.
        """
        msg = await self.send(message)
        confirm = None
        def check(payload):
            nonlocal confirm 
            if payload.message_id != msg.id or payload.user_id != self.message.author.id:
                return False
            emoji = str(payload.emoji)
            if emoji == '<:DVB_checkmark:955345523139805214>':
                confirm = True
                return True
            elif emoji == '<:DVB_crossmark:955345521151737896>':
                confirm = False
                return True
            return False

        for emoji in ['<:DVB_checkmark:955345523139805214>','<:DVB_crossmark:955345521151737896>']:
            await msg.add_reaction(emoji)
        try:
            await self.bot.wait_for('raw_reaction_add', check=check, timeout=timeout)
        except asyncio.TimeoutError:
            confirm = None
        if confirm is False and cancel_message:
            await msg.clear_reactions()
            await msg.edit(content=cancel_message, delete_after=delete_delay)
            return confirm
        if delete_after:
            if confirm:
                await msg.delete(delay=0)
            else:
                await msg.clear_reactions()
                await self.crossmark()
                await msg.delete(delay=delete_delay)
        return confirm

    async def confirm(self, content: str, delete_after: Optional[bool] = False, **kwargs) -> Optional[bool]:
        from utils.buttons import ConfirmView
        return await ConfirmView(self, delete_after).send(content, **kwargs)

    async def send_error(self, error = None):
        """
        Sends the error message, and deletes it after 10 seconds.
        """
        if error is None:
            return await self.send('Oops! something went wrong')
        return await self.send('Oops! something went wrong, \n{error}'.format(error=error), allowed_mentions=discord.AllowedMentions(roles=False, users=False), delete_after=10)

    async def is_bot_dev(self):
        """
        Checks if the invoking user is a bot developer.
        """
        return True if (await self.bot.db.fetchrow("SELECT * FROM devmode WHERE user_id = $1", self.message.author.id)) else False

    @property
    def color(self):
        """
        Returns bot's custom color if author's color is default one.
        """
        if self.bot.user_color:
            if self.author.color != discord.Color.default():
                return self.author.color
        return self.bot.embed_color

    @property
    def clean_prefix(self) -> str:
        """
        Returns guilds prefix, even if the command was invoked by mention.
        """
        return self.bot.get_guild_prefix(self.guild)