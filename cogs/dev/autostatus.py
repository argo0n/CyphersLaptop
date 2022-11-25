import discord
from discord.ext import commands, tasks

from main import clvt


class AutoStatus(commands.Cog):
    def __init__(self, client):
        self.client: clvt = client
        self.status = None

    @tasks.loop(minutes=1.0)
    async def change_status(self):
        if self.client.custom_status is False:
            try:
                await self.client.wait_until_ready()
                self.status = discord.Activity(name="your VALORANT store", type=discord.ActivityType.watching)
                um = discord.Status.online
                await self.client.change_presence(status=um, activity=self.status)
            except Exception as e:
                print(f"status task caught a error: {e}")