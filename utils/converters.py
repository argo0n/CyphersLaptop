from discord.ext import commands

from utils.errors import ArgumentBaseError
from utils.format import stringnum_toint


class BetterInt(commands.Converter):
    async def convert(self, ctx, argument:str):
        try:
            number: int = stringnum_toint(argument)
        except Exception as e:
            raise e
        if number is None:
            raise ArgumentBaseError(message=f"`{argument}` is not a valid number. Accepted formats are `123`, `1m`, `1k`, `3e6`.")
        return number
