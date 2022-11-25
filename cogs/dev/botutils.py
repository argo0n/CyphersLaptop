import discord
import aiohttp
from discord.ext import commands
from utils import checks

class BotUtils(commands.Cog):
    def __init__(self, client):
        self.client = client

    @checks.dev()
    @commands.group(hidden=True)
    async def set(self, ctx):
        """
        Base command for managing bot.
        """
        pass

    @checks.dev()
    @set.command(name='avatar', hidden=True, usage='<avatar>')
    async def set_avatar(self, ctx, *, url: str=None):
        """
        Sets bot's avatar.

        Supports either an image or an attachment.
        """
        if len(ctx.message.attachments) > 0:
            data = await ctx.message.attachments[0].read()
        elif url is not None:
            if url.startswith("<") and url.endswith(">"):
                url = url[1:-1]
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(url) as r:
                        data = await r.read()
                except aiohttp.InvalidURL:
                    await ctx.crossmark()
                    return await ctx.send("That URL is invalid.")
                except aiohttp.ClientError:
                    await ctx.crossmark()
                    return await ctx.send("Something went wrong while trying to get the image.")
        else:
            await ctx.crossmark()
            return await ctx.send("I need either an attachment or an image URL.")
        try:
            await ctx.bot.user.edit(avatar=data)
        except discord.HTTPException:
            await ctx.crossmark()
            return await ctx.send("Failed. Remember that you can edit my avatar up to two times a hour. The URL or attachment must be a valid image in either JPG or PNG format.", delete_after=3)
        except discord.InvalidArgument:
            await ctx.crossmark()
            return await ctx.send("JPG / PNG format only.", delete_after=3)
        else:
            await ctx.checkmark()
            await ctx.send("Profile picture updated <3")