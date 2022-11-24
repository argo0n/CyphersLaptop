import discord
from discord.ext import commands

from main import dvvt
from utils import riot_authorization
from utils.helper import get_region_code
from .database import DBManager
from utils.responses import *
from utils.buttons import confirm


class MainCommands(commands.Cog):
    def __init__(self, client):
        self.client: dvvt = client
        self.dbManager: DBManager = DBManager(self.client.db)

    @commands.Cog.listener()
    async def on_ready(self):
        print('test')
        await self.client.wait_until_ready()
        self.dbManager = DBManager(self.client.db)

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
                    password: discord.Option(str, "Your Riot password. It is encrypted when stored in the database.", required=True),
                    region: discord.Option(str, "Your Riot region",
                                           choices=["Asia Pacific", "North America", "Europe", "Korea"], required=True),
                    ):
        reg_code = get_region_code(region)
        riot_user = await self.dbManager.get_user_by_username(username)
        if riot_user is not None:
            return await ctx.respond(embed=user_already_exist(username, riot_user.user_id == ctx.author.id), ephemeral=True)
        await ctx.defer(ephemeral=True)
        try:
            auth = riot_authorization.RiotAuth()
            await auth.authorize(username, password)
        except riot_authorization.Exceptions.RiotAuthenticationError:
            await ctx.respond(embed=authentication_error())
            print(f"**{username}** failed to authenticate from **{ctx.author}**")
            return
        except riot_authorization.Exceptions.RiotRatelimitError:
            await ctx.respond(embed=rate_limit_error())
            print(f"**{username}** ratelimited from **{ctx.author}**")
            return
        except riot_authorization.Exceptions.RiotMultifactorError:
            pass
        # All other exceptions will be handled by global
        # Add to database
        print("Adding account details to database...")
        await self.dbManager.add_user(ctx.author.id, username, password, reg_code)
        print("Account details added to database.")
        await ctx.respond(embed=user_logged_in(username), ephemeral=True)
        print(f"**{username}** logged in from **{ctx.author}**")



    @commands.slash_command(name="logout", description="Logout of your Riot Games account.")
    async def logout(self, ctx: discord.ApplicationContext):
        c = confirm(ctx, self.client, 30.0)
        riot_account = await self.dbManager.get_user_by_user_id(ctx.author.id)
        if riot_account:
            e = discord.Embed(title="Confirm logout", description=f"Are you sure you want to log out of your Riot Games account **{riot_account.username}**?")
        else:
            return await ctx.respond(embed=no_logged_in_account(), ephemeral=True)
        c.response = await ctx.respond(embed=e, view=c, ephemeral=True)
        await c.wait()
        if c.returning_value is True:
            await self.client.db.execute("DELETE FROM valorant_login WHERE user_id = $1", ctx.author.id)
            await ctx.respond(embed=user_logged_out(riot_account.username), ephemeral=True)


    @commands.slash_command(name="update-password", description="Update the password of your Riot account.")
    async def update_password(self, ctx: discord.ApplicationContext,
                              password: discord.Option(str, "Your new Riot password")):
        await ctx.respond(".", ephemeral=True)
