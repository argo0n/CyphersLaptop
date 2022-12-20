import discord
from discord.ext import commands
from .settings import Settings
from ..maincommands.database import DBManager


class Others(Settings, commands.Cog):
    def __init__(self, client):
        self.client = client
        self.dbManager: DBManager = None

    @commands.Cog.listener()
    async def on_ready(self):
        await self.client.wait_until_ready()
        print(self.client.db)
        self.dbManager = DBManager(self.client.db)