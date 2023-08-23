from discord.ext import commands


class ArgumentBaseError(commands.UserInputError):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

class WeAreStillDisabled(ValueError):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)