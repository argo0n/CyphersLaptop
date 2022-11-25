import discord
from typing import Callable, Optional
from discord.ext import commands
from utils.errors import ArgumentBaseError
from utils.format import get_command_name
from utils.context import CLVTcontext


def in_beta() -> Callable:
    async def predicate(ctx: CLVTcontext):
        if ctx.author.guild_permissions.manage_roles:
            return True
        else:
            raise ArgumentBaseError(message="This feature is still in development and is not available to the public at the moment. Be sure to check it out again soon!")
    return commands.check(predicate)

def is_not_blacklisted() -> callable:
    async def predicate(ctx: CLVTcontext):
        blacklisted_users = await ctx.bot.db.fetchrow("SELECT * FROM blacklist WHERE user_id = $1 and blacklist_active = $2", ctx.author.id, True)
        if blacklisted_users:
            if ctx.message.author.id in [321892489470410763, 650647680837484556, 515725341910892555]:
                return True
            raise ArgumentBaseError(message="You have been blacklisted from using this function.")
        return True
    return commands.check(predicate=predicate)

def base_dev() -> callable:
    async def predicate(ctx: CLVTcontext):
        if await ctx.is_bot_dev():
            return True
        else:
            raise ArgumentBaseError(message="Only developers can use this command.")
    return commands.check(predicate)

def dev() -> callable:
    async def predicate(ctx: CLVTcontext):
        enabled = await ctx.bot.db.fetchval("SELECT enabled FROM devmode WHERE user_id = $1", ctx.author.id)
        if enabled != True:
            raise ArgumentBaseError(message="Only developers can use this command. If you are a developer, turn on Developer mode.")
        return True
    return commands.check(predicate)