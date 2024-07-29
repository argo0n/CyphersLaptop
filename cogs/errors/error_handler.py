import contextlib

import discord
from datetime import datetime

from aiohttp.client_exceptions import ClientResponseError

from utils.responses import ErrorEmbed, cl_unavailable_riot_sucks
from utils.time import humanize_timedelta
from discord.ext import commands
from utils.format import print_exception
from utils.errors import ArgumentBaseError, WeAreStillDisabled
import json
import asyncio

import os
dir = os.path.join(os.getcwd(), 'main.py')

class ErrorHandler(commands.Cog):
    """
    A cog that handles all errors.
    """
    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_application_command_error(self, ctx, error):
        """
        The event triggered when an error is raised while invoking an ApplicationCommand.
        """
        handled = False
        async def send_error(*args, **kwargs):
            await ctx.respond(*args, ephemeral=True, **kwargs)

        if (cog := ctx.cog):
            if cog._get_overridden_method(cog.cog_command_error) is not None:
                handled = True
                return
        ignore = (commands.CommandNotFound)
        if isinstance(error, ignore):
            handled = True
            return
        if isinstance(error, ClientResponseError):
            await cl_unavailable_riot_sucks(ctx);
        if isinstance(error, commands.NoPrivateMessage):
            handled = True
            await send_error("Sowwi, you can't use this command in DMs :(", delete_after=10)
        elif isinstance(error, commands.CheckFailure):
            handled = True
            await send_error("Oops!, looks like you don't have enough permission to use this command.", delete_after=5)
        elif isinstance(error, commands.CommandOnCooldown):
            #enabled = await ctx.bot.db.fetchval("SELECT enabled FROM devmode WHERE user_id = $1", ctx.author.id)
            #if enabled == True:
                #return await ctx.invoke(ctx.command, *ctx.args, **ctx.kwargs)
            handled = True
            message = f"You're on cooldown. Try again in **{humanize_timedelta(seconds=error.retry_after)}**."
            if ctx.command.name == "dumbfight":
                message += "\nPeople with **Vibing Investor** will have a cooldown of only **30 minutes**!"
            if ctx.command.name == "lockgen":
                message = f"This command is currently under a global cooldown of **{humanize_timedelta(seconds=error.retry_after)}** to prevent abuse.\n"
            await send_error(message)
        elif isinstance(error, commands.MemberNotFound):
            ctx.command.reset_cooldown(ctx)
            handled = True
            await send_error("I couldn't find a member called {}.".format(error.argument))
        elif isinstance(error, commands.RoleNotFound):
            ctx.command.reset_cooldown(ctx)
            handled = True
            await send_error("I couldn't find a role called {}.".format(error.argument))
        elif isinstance(error, commands.BadUnionArgument):
            ctx.command.reset_cooldown(ctx)
            if error.converters == (discord.TextChannel, discord.VoiceChannel):
                handled = True
                await send_error("I couldn't find that channel.")
        elif isinstance(error, ArgumentBaseError):
            ctx.command.reset_cooldown(ctx)
            handled = True
            await send_error(error)
        elif isinstance(error, commands.BadArgument):
            ctx.command.reset_cooldown(ctx)
            handled = True
            await send_error(error, delete_after=10)
        elif isinstance(error, discord.ApplicationCommandInvokeError):
            error_original = error.original
            if isinstance(error_original, commands.MissingPermissions):
                handled = True
                await send_error("Oops!, looks like you don't have enough permission to use this command.", delete_after=5)
            elif isinstance(error_original, WeAreStillDisabled):
                handled = True
                embed = ErrorEmbed(title="Cypher's Laptop unavailable (for now)",
                    description="## I have no way of getting your store at the moment, as Riot Games has patched the method that I use.\n\nThat is, a method that Cypher's Laptop uses to communicate with Riot Games was intentionally blocked by them. \n\n**__All__** store checkers are **__unable__** to let you check your store.")
                embed.set_footer(text="Your action was not completed.")
                embed.add_field(name="What do I do now?", value="Cypher's Laptop will DM you if a fix has been implemented.\n\nFor now, rely on the VALORANT Game Client to check your store.\n\nI have no control of this issue; it is up to Riot Games to unblock the method used by store checkers.")
                await send_error(embed=ErrorEmbed(
                    title="Cypher's Laptop doesn't work (for now)",
                    description="A method that Cypher's Laptop uses to communicate with Riot Games doesn't work. \nAs of now, we are stlil unable to communicate with Riot.").set_footer(text="Your action was not completed."))

        if handled is not True:
            traceback_error = print_exception(f'Ignoring exception in command {ctx.command}:', error)
            if os.getenv('state') == '1':
                await ctx.send(embed=discord.Embed(description=f"```py\n{traceback_error}\n```", color=0x1E90FF))
            else:

                embed = discord.Embed(title="⚠️ Oh no!",
                                      description="Something terribly went wrong when this command was used.\n\nThe developers have been notified and it'll fixed soon.",
                                      color=discord.Color.red())
                if ctx.author.id in [650647680837484556, 321892489470410763]:
                    embed.add_field(name="Error", value=f"```prolog\n{error}\n```\n<#871737028105109574>")
                    await send_error(embed=embed)
                else:
                    embed.set_footer(text="In the meantime, do not keep running this command.")
                    await send_error(embed=embed, delete_after=10)
                guild = f"`{ctx.guild}` ({ctx.guild.id})" if ctx.guild is not None else "DMs"
                error_message = f"**Command:** `{ctx.command.name}`\n" \
                                f"**Author:** `{ctx.author}` ({ctx.author.id})\n" \
                                f"**Guild:** {guild}\n" \
                                f"**Channel:** `{ctx.channel}` ({ctx.channel.id})\n" \
                                f"```py\n" \
                                f"{traceback_error}\n" \
                                f"```"
                await self.client.error_channel.send(content=f"<@&871740422932824095> Check this out",
                                                     embed=discord.Embed(title="ApplicationCommand Error", color=0xffcccb, description=error_message,
                                                                         timestamp=discord.utils.utcnow()),
                                                     allowed_mentions=discord.AllowedMentions(roles=True))

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """
        The event triggered when an error is raised while invoking a command.
        """
        async def send_error(*args, **kwargs):
            await ctx.send(*args, allowed_mentions=discord.AllowedMentions(roles=False, users=False), **kwargs)
        if (cog := ctx.cog):
            if cog._get_overridden_method(cog.cog_command_error) is not None:
                return
        ignore = (commands.CommandNotFound)
        if isinstance(error, ignore):
            return
        if isinstance(error, commands.NoPrivateMessage):
            await send_error("Sowwi, you can't use this command in DMs :(", delete_after=10)
        elif isinstance(error, commands.CheckFailure):
            await send_error("Oops!, looks like you don't have enough permission to use this command.", delete_after=5)
        elif isinstance(error, commands.CommandOnCooldown):
            message = f"You're on cooldown. Try again in **{humanize_timedelta(seconds=error.retry_after)}**."
            if ctx.command.name == "dumbfight":
                message += "\nPeople with **Vibing Investor** will have a cooldown of only **30 minutes**!"
            if ctx.command.name == "lockgen" or ctx.command.name == 'randomcolor':
                message = f"This command is currently under a global cooldown of **{humanize_timedelta(seconds=error.retry_after)}** to prevent abuse.\n"
            await send_error(message)
        elif isinstance(error, commands.MemberNotFound):
            ctx.command.reset_cooldown(ctx)
            await send_error("I couldn't find a member called {}.".format(error.argument))
        elif isinstance(error, commands.RoleNotFound):
            ctx.command.reset_cooldown(ctx)
            await send_error("I couldn't find a role called {}.".format(error.argument))
        elif isinstance(error, commands.BadUnionArgument):
            ctx.command.reset_cooldown(ctx)
            if error.converters == (discord.TextChannel, discord.VoiceChannel):
                await send_error("I couldn't find that channel.")
        elif isinstance(error, commands.MissingRequiredArgument):
            ctx.command.reset_cooldown(ctx)
            await send_error("{} is a required argument.".format(error.param))
        elif isinstance(error, ArgumentBaseError):
            ctx.command.reset_cooldown(ctx)
            await send_error(error)
        elif isinstance(error, commands.BadArgument):
            ctx.command.reset_cooldown(ctx)
            if str(error).startswith("Converting to \"int\" failed"):
                actual_format, parameter = str(error).split('"')[1], str(error).split('"')[3]
                if actual_format == 'int':
                    actual_format = 'number'
                await send_error(f"`{parameter}` should be in the form of a **{actual_format}**.")
            else:
                await send_error(error, delete_after=10)
        elif isinstance(error, discord.errors.DiscordServerError):
            return
        else:
            traceback_error = print_exception(f'Ignoring exception in command {ctx.command}:', error)
            if os.getenv('state') == '1':
                await ctx.send(embed=discord.Embed(description=f"```py\n{traceback_error}\n```", color=0x1E90FF))
            else:
                embed = discord.Embed(title="⚠️ Oh no!", description="Something terribly went wrong when this command was used.\n\nThe developers have been notified and it'll fixed soon.", color=discord.Color.red())
                if ctx.author.id in [650647680837484556, 321892489470410763]:
                    embed.add_field(name="Error", value=f"```prolog\n{error}\n```\n<#871737028105109574>")
                    await send_error(embed=embed)
                else:
                    embed.set_footer(text="In the meantime, do not keep running this command.")
                    await send_error(embed=embed, delete_after=10)
                guild = f"`{ctx.guild.name}` ({ctx.guild.id})" if ctx.guild is not None else "DMs"
                error_message = f"**Command:** `{ctx.message.content}`\n" \
                                f"**Message ID:** `{ctx.message.id}`\n" \
                                f"**Author:** `{ctx.author}` ({ctx.author.id})\n" \
                                f"**Guild:** {guild}\n" \
                                f"**Channel:** `{ctx.channel.name}` ({ctx.channel.id})\n" \
                                f"**Jump:** [`jump`]({ctx.message.jump_url})```py\n" \
                                f"{traceback_error}\n" \
                                f"```"
                return await self.client.error_channel.send(content=f"<@&871740422932824095> Check this out",embed=discord.Embed(title="Text Command Error", color=0xffcccb, description=error_message, timestamp=discord.utils.utcnow()).set_footer(text=f"From: {ctx.guild.name}", icon_url=ctx.guild.icon.url), allowed_mentions=discord.AllowedMentions(roles=True))