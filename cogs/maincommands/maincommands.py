import discord
from discord.ext import commands

from main import clvt
from utils import riot_authorization, get_store
from utils.helper import get_region_code
from .database import DBManager
from utils.responses import *
from utils.buttons import confirm


class MainCommands(commands.Cog):
    def __init__(self, client):
        self.client: clvt = client
        self.dbManager: DBManager = DBManager(self.client.db)

    @commands.Cog.listener()
    async def on_ready(self):
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
        if riot_user is not False:
            return await ctx.respond(embed=user_already_exist(username, riot_user.user_id == ctx.author.id), ephemeral=True)
        await ctx.defer(ephemeral=True)
        try:
            auth = riot_authorization.RiotAuth()
            await auth.authorize(username, password)
        except riot_authorization.Exceptions.RiotAuthenticationError:
            await ctx.respond(embed=authentication_error(True))
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

    @commands.slash_command(name="update-password", description="If you changed your password at Riot Games, update it here.")
    async def update_password(self, ctx: discord.ApplicationContext,
                              password: discord.Option(str, "Your new Riot password")):
        c = confirm(ctx, self.client, 30.0)
        riot_account = await self.dbManager.get_user_by_user_id(ctx.author.id)
        if riot_account:
            e = discord.Embed(title="Confirm password update",
                              description=f"Are you sure you want to update the password of your Riot Games account **{riot_account.username}**?")
        else:
            return await ctx.respond(embed=no_logged_in_account(), ephemeral=True)
        c.response = await ctx.respond(embed=e, view=c, ephemeral=True)
        await c.wait()
        if c.returning_value is True:
            e = await ctx.respond(embed=updating_password(riot_account.username, 1), ephemeral=True)
            try:
                auth = riot_authorization.RiotAuth()
                await auth.authorize(riot_account.username, password)
            except riot_authorization.Exceptions.RiotAuthenticationError:
                await e.edit(embed=authentication_error(True))
                print("Authentication error")
                return
            except riot_authorization.Exceptions.RiotRatelimitError:
                await e.edit(embed=rate_limit_error())
                print("Rate limited")
                return
            except riot_authorization.Exceptions.RiotMultifactorError:
                pass
            # All other exceptions will be handled by global
            # Update password
            print("Updating account details to database...")
            await self.dbManager.update_password(riot_account.username, password)
            await e.edit(embed=user_updated(riot_account.username))
        print("Updated account details to database")
        return
        c = confirm(ctx, self.client, 30.0)
        riot_account = await self.dbManager.get_user_by_user_id(ctx.author.id)
        if riot_account:
            e = discord.Embed(title="Confirm password update", description=f"Are you sure you want to update the password of your Riot Games account **{riot_account.username}**?")
        else:
            return await ctx.respond(embed=no_logged_in_account(), ephemeral=True)
        c.response = await ctx.respond(embed=e, view=c, ephemeral=True)
        await c.wait()
        if c.returning_value is True:
            await self.client.db.execute("UPDATE valorant_login SET password = $1 WHERE user_id = $2", password, ctx.author.id)
            await ctx.respond(embed=user_updated(riot_account.username), ephemeral=True)

    @commands.slash_command(name="store", description="View your VALORANT store.")
    async def store(self, ctx: discord.ApplicationContext, multifactor_code: discord.Option(str, max_length=6, required=False) = None):
        riot_account = await self.dbManager.get_user_by_user_id(ctx.author.id)
        if riot_account:
            await ctx.defer(ephemeral=True)
        else:
            return await ctx.respond(embed=no_logged_in_account(), ephemeral=True)
        try:
            auth = riot_authorization.RiotAuth()
            await auth.authorize(riot_account.username, riot_account.password, multifactor_code=multifactor_code)
        except riot_authorization.Exceptions.RiotAuthenticationError:
            await ctx.respond(embed=authentication_error())
            print("Authentication error")
            return
        except riot_authorization.Exceptions.RiotRatelimitError:
            await ctx.respond(embed=rate_limit_error())
            print("Rate limited")
            return
        except riot_authorization.Exceptions.RiotMultifactorError:
            # No multifactor provided check
            if multifactor_code is None:
                await ctx.respond(embed=multifactor_detected())
                print("Multifactor detected")
                return
            await ctx.respond(embed=multifactor_error())
            print("Multifactor authentication error")
            return
        headers = {
            "Authorization": f"Bearer {auth.access_token}",
            "User-Agent": riot_account.username,
            "X-Riot-Entitlements-JWT": auth.entitlements_token,
            "X-Riot-ClientPlatform": "ew0KCSJwbGF0Zm9ybVR5cGUiOiAiUEMiLA0KCSJwbGF0Zm9ybU9TIjogIldpbmRvd3MiLA0KCSJwbGF0Zm9ybU9TVmVyc2lvbiI6ICIxMC4wLjE5MDQyLjEuMjU2LjY0Yml0IiwNCgkicGxhdGZvcm1DaGlwc2V0IjogIlVua25vd24iDQp9",
            "X-Riot-ClientVersion": "pbe-shipping-55-604424"
        }
        store = await get_store.getStore(headers, auth.user_id, riot_account.region)
        try:
            for item in store[0]:
                embed = discord.Embed(title=item[0], description=f"Cost: {item[1]} Valorant Points",
                                      color=discord.Color.gold())
                embed.set_thumbnail(url=item[2])
                await ctx.send(embed=embed)
        except discord.errors.Forbidden:
            await ctx.respond(embed=permission_error())
        else:
            embed = discord.Embed(title="Offer ends in", description=store[1], color=discord.Color.gold())
            await ctx.send(embed=embed)
        print("Store fetch successful")
        return

    #@commands.slash_command(name=)""