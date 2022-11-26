import functools
import getpass
import importlib
import io
import os
import re
import ast
import copy
import subprocess
import sys
import time
import typing
from collections import Counter

from datetime import datetime, timezone

import discord
from discord import Webhook
import asyncio
import inspect
import aiohttp
import textwrap
import traceback
import contextlib
from abc import ABC

from main import clvt
from utils import checks
from .status import Status
from .botutils import BotUtils
from .autostatus import AutoStatus
from contextlib import redirect_stdout
from discord.ext import commands, menus
from utils.buttons import confirm
from utils.format import pagify, TabularData, plural, text_to_file, get_command_name, comma_number, box
from typing import Optional, Union
from utils.context import CLVTcontext
from utils.converters import MemberUserConverter, TrueFalse



class ConfirmContinue(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=180)
        self.result = None
        self.ctx = ctx

    @discord.ui.button(label="Click to continue", style=discord.ButtonStyle.red)
    async def continue_eval(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.result = True
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction):
        return interaction.user.id == self.ctx.author.id

    async def on_timeout(self):
        self.result = False
        self.stop()


class toggledevmode(discord.ui.View):
    def __init__(self, ctx: CLVTcontext, client, enabled):
        self.context = ctx
        self.response = None
        self.result = None
        self.client = client
        self.enabled = enabled
        super().__init__(timeout=5.0)
        init_enabled = self.enabled

        async def update_message(interaction):
            self.enabled = False if self.enabled else True
            await self.client.db.execute("UPDATE devmode SET enabled = $1 WHERE user_id = $2", self.enabled, ctx.author.id)
            self.children[0].style = discord.ButtonStyle.green if self.enabled else discord.ButtonStyle.red
            self.children[0].label = "Dev Mode is enabled" if self.enabled else "Dev mode is disabled"
            await interaction.response.edit_message(view=self)


        class somebutton(discord.ui.Button):
            async def callback(self, interaction: discord.Interaction):
                await update_message(interaction)
        self.add_item(somebutton(emoji="🛠️", label = "Dev Mode is enabled" if init_enabled else "Dev mode is disabled", style=discord.ButtonStyle.green if init_enabled else discord.ButtonStyle.red))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        ctx = self.context
        author = ctx.author
        if interaction.user != author:
            await interaction.response.send_message("Only the author can interact with this message.", ephemeral=True)
            return False
        return True

    async def on_timeout(self) -> None:
        for b in self.children:
            b.disabled = True
        await self.response.edit(view=self)


class CompositeMetaClass(type(commands.Cog), type(ABC)):
    """
    This allows the metaclass used for proper type detection to
    coexist with discord.py's metaclass
    """
    pass


class Developer(AutoStatus, BotUtils, Status, commands.Cog, name='dev', command_attrs=dict(hidden=True), metaclass=CompositeMetaClass):
    """
    This module contains various development focused commands.
    """
    def __init__(self, client):
        self.change_status.start()
        self.client: clvt = client
        self.sessions = set()
        self.view_added = False

    async def run_process(self, command):
        try:
            process = await asyncio.create_subprocess_shell(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            result = await process.communicate()
        except NotImplementedError:
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            result = await self.client.loop.run_in_executor(None, process.communicate)

        return [output.decode() for output in result]

    def cleanup_code(self, content):
        """Automatically removes code blocks from the code."""
        if content.startswith('```') and content.endswith('```'):
            return '\n'.join(content.split('\n')[1:-1])
        return content.strip('` \n')

    def get_syntax_error(self, e):
        if e.text is None:
            return f'```py\n{e.__class__.__name__}: {e}\n```'
        return f'```py\n{e.text}{"^":>{e.offset}}\n{e.__class__.__name__}: {e}```'

    def sanitize_output(self, input_: str) -> str:
        """Hides the bot's token from a string."""
        token = self.client.http.token
        return re.sub(re.escape(token), "[TOKEN]", input_, re.I)

    @staticmethod
    def async_compile(source, filename, mode):
        return compile(source, filename, mode, flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT, optimize=0)

    @staticmethod
    def get_pages(msg: str):
        """Pagify the given message for output to the user."""
        return pagify(msg, delims=["\n", " "], priority=True, shorten_by=10)

    @staticmethod
    def get_sql(msg: str):
        return pagify(msg, delims=["\n", " "], priority=True, shorten_by=10, box_lang='py')

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.view_added:
            self.view_added = True

    @checks.dev()
    @commands.command(hidden=True, usage='[silently]')
    async def shutdown(self, ctx, silently: TrueFalse = False):
        """
        Shuts down the bot.

        The bot will send a shutdown message, you can pass true to skip that.
        """
        try:
            await ctx.checkmark()
            if not silently:
                await ctx.send("Shutting down...")
            if silently:
                with contextlib.suppress(discord.HTTPException):
                    await ctx.message.delete()
            await self.client.shutdown()
        except Exception as e:
            await ctx.send("Error while disconnecting",delete_after=3)
            await ctx.author.send(f"An unexpected error has occured.\n```py\n{type(e).__name__} - {e}```")
            await ctx.message.delete(delay=3)

    @checks.dev()
    @commands.command(pass_context=True, hidden=True, name='eval', usage="<content>")
    async def _eval(self, ctx, silent: Optional[typing.Literal['silent', 'Silent']] = None, *, body: str=None):
        """
        Evaluate a code directly from your discord.

        The bot will always respond with the return value of the code.
        If the return value of the code is a coroutine, it will be awaited,
        and the result of that will be the bot's response.

        The code can be within a codeblock, inline code or neither, as long
        as they are not mixed and they are formatted correctly.
        """
        env = {
            'client': self.client,
            'ctx': ctx,
            'channel': ctx.channel,
            'author': ctx.author,
            'guild': ctx.guild,
            'message': ctx.message,
            'suppress': contextlib.suppress,
            'time': time,
            'asyncio': asyncio,
            'aiohttp': aiohttp,
        }
        env.update(globals())
        if body is None:
            return await ctx.send("I need something to evaluate.")

        body = self.cleanup_code(body)
        stdout = io.StringIO()
        to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'
        dangerous_keywords = ['delete', 'getenv']
        dangerous_line, dangerous_word = None, None
        for line in to_compile.split('\n'):
            for keyword in dangerous_keywords:
                if keyword in line:
                    dangerous_line, dangerous_word = line, keyword
                    view = ConfirmContinue(ctx)
                    embed = discord.Embed(title=f"Dangerous keyword detected - `{dangerous_word}`",
                                          description=f"{box(dangerous_line, lang='py')}",
                                          color=self.client.embed_color)
                    embed.set_footer(text="Click the button 'Click to continue' to evaluate this expression.")
                    warning = await ctx.send(embed=embed, view=view)
                    await view.wait()
                    await warning.delete()
                    if not view.result is True:
                        return
        if silent is not None:
            with contextlib.suppress(discord.HTTPException):
                await ctx.message.delete()
        try:
            exec(to_compile, env)
        except SyntaxError as e:
            await ctx.crossmark()
            return await ctx.send(f'```py\n{e.__class__.__name__}: {e}\n```')

        func = env['func']
        ret = None
        try:
            with redirect_stdout(stdout):
                ret = await func()
        except:
            await ctx.crossmark()
            to_print = "{}{}".format(stdout.getvalue(), traceback.format_exc())
        else:
            to_print = stdout.getvalue()
            await ctx.checkmark()

        if ret is not None:
            msg = "{}{}".format(to_print, ret)
        else:
            msg = to_print
        msg = self.sanitize_output(msg)
        await ctx.send_interactive(self.get_pages(msg), box_lang="py")

    @checks.dev()
    @commands.command(name='repl', hidden=True)
    async def repl(self, ctx):
        """
        Launches an interactive REPL session.

        The code can be within a codeblock, inline code or neither, as long
        as they are not mixed and they are formatted correctly.
        """
        variables = {
            'ctx': ctx,
            'client': self.client,
            'message': ctx.message,
            'guild': ctx.guild,
            'channel': ctx.channel,
            'author': ctx.author,
            'asyncio': asyncio,
            'aiohttp': aiohttp,
            'suppress': contextlib.suppress,
            '_': None,
        }

        if ctx.channel.id in self.sessions:
            await ctx.send('Already running a REPL session in this channel. Exit it with `quit`.')
            return
        self.sessions.add(ctx.channel.id)
        await ctx.send('Enter code to execute or evaluate. `exit()` or `quit` to exit.')
        await ctx.message.add_reaction('<a:DVB_typing:955345484648710154>')
        def check(m):
            return m.author.id == ctx.author.id and \
                   m.channel.id == ctx.channel.id
        while True:
            try:
                response = await self.client.wait_for('message', check=check, timeout=10.0 * 60.0)
            except asyncio.TimeoutError:
                await ctx.message.clear_reaction('<a:DVB_typing:955345484648710154>')
                await ctx.checkmark()
                await ctx.send('Exiting REPL session.')
                self.sessions.remove(ctx.channel.id)
                break

            cleaned = self.cleanup_code(response.content)

            if cleaned in ('quit', 'exit', 'exit()'):
                await ctx.message.clear_reaction('<a:DVB_typing:955345484648710154>')
                await ctx.checkmark()
                await ctx.send('Exiting.')
                self.sessions.remove(ctx.channel.id)
                return

            executor = exec
            if cleaned.count('\n') == 0:
                try:
                    code = self.async_compile(cleaned, '<repl session>', 'eval')
                except SyntaxError:
                    pass
                else:
                    executor = eval
            if executor is exec:
                try:
                    code = self.async_compile(cleaned, '<repl session>', 'exec')
                except SyntaxError as e:
                    await ctx.send(self.get_syntax_error(e))
                    continue
            variables['message'] = response
            fmt = None
            stdout = io.StringIO()
            try:
                with redirect_stdout(stdout):
                    result = executor(code, variables)
                    if inspect.isawaitable(result):
                        result = await result
            except:
                value = stdout.getvalue()
                fmt = "{}{}".format(value, traceback.format_exc())
            else:
                value = stdout.getvalue()
                if result is not None:
                    fmt = "{}{}".format(value, result)
                    variables['_'] = result
                elif value:
                    fmt = "{}".format(value)
            try:
                if fmt is not None:
                    msg = self.sanitize_output(fmt)
                    await ctx.send_interactive(self.get_pages(msg), box_lang="py")
            except discord.Forbidden:
                pass
            except discord.HTTPException as e:
                await ctx.send(f'Unexpected error: `{e}`')

    @checks.dev()
    @commands.group(name='sql', invoke_without_command=True, hidden=True)
    async def sql(self, ctx, *, query: str = None):
        """
        Evaluate a SQL query directly from your discord.
        """
        if query is None:
            return await ctx.send('Query is a required argument.')
        query = self.cleanup_code(query)
        multistatement = query.count(';') > 1
        if query.lower().startswith('select') and not multistatement:
            strategy = self.client.db.fetch
        else:
            multistatement = True
            strategy = self.client.db.execute
        try:
            start = time.perf_counter()
            results = await strategy(query)
            time_taken = (time.perf_counter() - start) * 1000.0
        except Exception:
            return await ctx.send(f'```py\n{traceback.format_exc()}\n```')
        rows = len(results)
        if multistatement or rows == 0:
            return await ctx.send(f'`{time_taken:.2f}ms: {results}`')
        headers = list(results[0].keys())
        table = TabularData()
        table.set_columns(headers)
        table.add_rows(list(r.values()) for r in results)
        render = table.render()
        msg = f'{render}\n*Returned {plural(len(results)):row} in {time_taken:.2f}ms*'
        if len(headers) > 2:
            return await ctx.send(file=text_to_file(msg, "sql.txt"))
        await ctx.send_interactive(self.get_sql(msg))

    @checks.dev()
    @sql.command(name='table', hidden=True, usage="<table>")
    async def sql_table(self, ctx, table: str = None):
        """
        Describes the table schema.
        """
        if table is None:
            return await ctx.send("Table is a required argument.")
        query = """SELECT column_name, data_type, column_default, is_nullable
                   FROM INFORMATION_SCHEMA.COLUMNS
                   WHERE table_name = $1
                """
        try:
            results = await self.client.db.fetch(query, table)
        except Exception:
            return await ctx.send(f'```py\n{traceback.format_exc()}\n```')
        headers = list(results[0].keys())
        table = TabularData()
        table.set_columns(headers)
        table.add_rows(list(r.values()) for r in results)
        render = table.render()
        msg = f'{render}'
        await ctx.send_interactive(self.get_sql(msg))

    @checks.dev()
    @commands.command(name="dsay", aliases=["decho"])
    async def d_say(self, ctx, channel: Optional[discord.TextChannel], *, message = None):
        """
        Talk as the bot.
        """
        if message is None:
            return await ctx.send("give me something to say 🤡")
        if channel is None:
            channel = ctx.channel
        if len(message) > 2000:
            return await ctx.send(f"Your message is {len(message)} characters long. It can only be 2000 characters long.")
        try:
            await channel.send(message)
            status = (1, "Sent successfully")
            await ctx.checkmark()
        except Exception as e:
            await ctx.crossmark()
            status = (0, e)

    @checks.dev()
    @commands.command(name="dreply")
    async def d_reply(self, ctx, messageID_or_messageLink:Union[int, str] = None, channel:Optional[discord.TextChannel] = None, *, message_content=None):
        """
        Replies to a specified message as the bot.
        Add --noping to disable pinging when replying.
        """
        #Getting message by message ID
        if type(messageID_or_messageLink) == int:
            if channel is None:
                channel = ctx.channel
            try:
                message = await channel.fetch_message(messageID_or_messageLink)
            except discord.NotFound:
                return await ctx.send(f"A message with that ID was not found. {'Did you forget to include a channel?' if channel==ctx.channel else ''}")
        else:
            if not (messageID_or_messageLink.startswith('http') and 'discord.com/channels/' in messageID_or_messageLink):
                return await ctx.send("You did not provide a valid message link or ID. A message link should start with `https://discord.com/channels/` or `https://canary.discord.com/channels/`.")
            split = messageID_or_messageLink.split('/')
            try:
                guild = self.client.get_guild(int(split[4]))
                channel = guild.get_channel(int(split[5]))
                message = await channel.fetch_message(int(split[6]))
            except discord.NotFound:
                return await ctx.send(f"A message with that link was not found. ")
        if message_content is None:
            return await ctx.send("give me something to say 🤡")
        if message_content.endswith('--noping'):
            ping=False
            message_content=message_content[:-8]
        else:
            ping=True
        if len(message_content) > 2000:
            return await ctx.send(f"Your message is {len(message_content)} characters long. It can only be 2000 characters long.")
        try:
            await message.reply(message_content, allowed_mentions=discord.AllowedMentions(everyone=False, users=True, roles=False, replied_user=ping))
            await ctx.checkmark()
            status = (1, "Sent successfully")
        except Exception as e:
            await ctx.crossmark()
            status = (0, e)

    @checks.dev()
    @commands.command(name="error", aliases=["raiseerror"])
    async def raise_mock_error(self, ctx, *, message=None):
        """
        Raises a ValueError for testing purposes.
        """
        await ctx.send("Mimicking an error...")
        raise ValueError(message)



    @checks.base_dev()
    @commands.command(name="devmode")
    async def devmode(self, ctx):
        result = await self.client.db.fetchrow("SELECT * FROM devmode WHERE user_id = $1", ctx.author.id)
        if result is None:
            await self.client.db.execute("INSERT INTO devmode VALUES($1, $2)", ctx.author.id, False)
            result = await self.client.db.fetchrow("SELECT * FROM devmode WHERE user_id = $1", ctx.author.id)
        is_enabled = result.get('enabled')
        view = toggledevmode(ctx, self.client, is_enabled)
        msg = await ctx.send("__**Toogle Developer mode**__", view=view)
        view.response = msg
        await view.wait()


    @checks.dev()
    @commands.command(name="bash", hidden=True, aliases=['cmd', 'terminal'])
    async def bash(self, ctx, *, cmd):
        cmds = cmd.splitlines()
        front_of_cmd = f"{getpass.getuser()}@{os.getcwd()}:~$ "
        if len(cmds) > 0:
            content = front_of_cmd
            basemsg = await ctx.send(f"```\n{content}\n```")
            now = time.perf_counter()
            for index, cmd in enumerate(cmds):
                content += f"{cmd}\n\n"
                await basemsg.edit(content="```\n" + content + "\n```")
                stdout, stderr = await self.run_process(cmd)
                content += f"{stdout}\n\n{front_of_cmd}"
                await basemsg.edit(content="```\n" + content + "\n```")
            content += f"\n\nCompleted in {round((time.perf_counter() - now) * 1000, 3)}ms"
            await basemsg.edit(content="```\n" + content + "\n```")