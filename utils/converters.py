from discord.ext import commands

from utils.errors import ArgumentBaseError
from utils.format import stringnum_toint


class TrueFalse(commands.Converter):
    """
    A basic true false converter.
    'yes', 'y', 'yeah', 'true' for True
    and 'no', 'n', 'nah', 'false' for False.
    """
    async def convert(self, ctx, argument):
        if argument.lower() in ('yes', 'y', 'yeah', 'true'):
            return True
        elif argument.lower() in ('no', 'n', 'nah', 'false'):
            return False
        return False


class BetterInt(commands.Converter):
    async def convert(self, ctx, argument:str):
        try:
            number: int = stringnum_toint(argument)
        except Exception as e:
            raise e
        if number is None:
            raise ArgumentBaseError(message=f"`{argument}` is not a valid number. Accepted formats are `123`, `1m`, `1k`, `3e6`.")
        return number

class MemberUserConverter(commands.Converter):
    """
    A converter that checks if a given argument is a member or not, if it's not a member
    it'll check if it's a user or not, if not it'll raise an error.
    """
    async def convert(self, ctx, argument):
        try:
            user = await commands.MemberConverter().convert(ctx, argument)
        except commands.MemberNotFound:
            try:
                user = await commands.UserConverter().convert(ctx, argument)
            except commands.UserNotFound:
                raise UserNotFound(argument)
        return user