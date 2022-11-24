import discord
from discord.ext import commands

from main import dvvt


class MainCommands(commands.Cog):
    def __init__(self, client):
        self.client: dvvt = client

    @commands.slash_command(name="store", description="Retrieve your store")
    async def store(self, ctx: discord.ApplicationContext,
                    multifactor_code: discord.Option(str, "Your multifactor code", required=False) = None
                    ):
        await ctx.respond(".", ephemeral=True)

    @commands.slash_command(name="balance", description="Retrieves your balance")
    async def balance(self, ctx: discord.ApplicationContext,
                      multifactor_code: discord.Option(str, "Your multifactor code", required=False) = None):
        await ctx.respond(".", ephemeral=True)

    @commands.slash_command(name="login", description="Login to your Riot Games account.")
    async def login(self, ctx: discord.ApplicationContext,
                    username: discord.Option(str, "Your Riot username", required=True),
                    password: discord.Option(str, "Your Riot password", required=True),
                    region: discord.Option(str, "Your Riot region",
                                           choices=["Asia Pacific", "North America", "Europe", "Korea"], required=True),
                    ):
        await ctx.respond(".", ephemeral=True)

    @commands.slash_command(name="logout", description="Logout of your Riot Games account.")
    async def logout(self, ctx: discord.ApplicationContext):
        await ctx.respond(".", ephemeral=True)

    @commands.slash_command(name="update-password", description="Update the password of your Riot account.")
    async def update_password(self, ctx: discord.ApplicationContext,
                              password: discord.Option(str, "Your new Riot password")):
        await ctx.respond(".", ephemeral=True)
