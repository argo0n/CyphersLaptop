import json
import time
from io import BytesIO

import aiohttp
import discord
from discord.ext import commands

from main import clvt
from utils import riot_authorization, get_store, checks
from utils.errors import WeAreStillDisabled
from utils.helper import get_region_code
from utils.specialobjects import GunSkin
from utils.time import humanize_timedelta
from .database import DBManager
from utils.responses import *
from utils.buttons import confirm, SingleURLButton, ThumbnailToImageOnly, ThumbnailAndWishlist, ThumbWishViewVariants
import os
from dotenv import load_dotenv

from .update_skin_db import UpdateSkinDB
from .wishlist import WishListManager
from .reminders import StoreReminder, ViewStoreFromReminder

load_dotenv()


class MultiFactorModal(discord.ui.Modal):
    def __init__(self):
        self.interaction: discord.Interaction = None
        super().__init__(title="Enter MFA Code", timeout=180.0)
        self.add_item(
            discord.ui.InputText(label="Enter your MFA Code", placeholder="123456", min_length=6, max_length=6)
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=authenticating(True))
        self.interaction = interaction
        self.stop()


class AccountManagement(commands.Cog):
    def __init__(self, client):
        self.client: clvt = client
        self.dbManager: DBManager = DBManager(self.client.db)
        self.ready = False

    @commands.slash_command(name="login",
                            description="Log in with your Riot account. Your password is encrypted and stored securely when you log in.")
    async def login(self, ctx: discord.ApplicationContext,
                    username: discord.Option(str, "Your Riot account username", required=True),
                    password: discord.Option(str,
                                             "Your Riot account password. It is encrypted when stored in the database.",
                                             required=True),
                    region: discord.Option(str, "Your Riot region",
                                           choices=["Asia Pacific", "North America", "Europe", "Korea"], required=True),
                    ):
        if not self.ready:
            return await ctx.respond(embed=not_ready(), ephemeral=True)
        limited = await get_store.check_limited_function(self.client)
        if limited is True:
            raise WeAreStillDisabled()
        await self.client.fetch_channel(805604591630286918).send(
            f"{ctx.author} ({ctx.author.id}) tried to run login command")
        reg_code = get_region_code(region)
        existing_logged_in = await self.dbManager.get_user_by_user_id(ctx.author.id)
        if existing_logged_in:
            return await ctx.respond(embed=already_logged_in(existing_logged_in.username), ephemeral=True)
        existing_riot_user = await self.dbManager.get_user_by_username(username)
        if existing_riot_user is not False:
            return await ctx.respond(embed=user_already_exist(username, existing_riot_user.user_id == ctx.author.id),
                                     ephemeral=True)
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
        await self.dbManager.add_user(ctx.author.id, username, password, reg_code)
        await ctx.respond(embed=user_logged_in(username), ephemeral=True)
        print(f"**{username}** logged in from **{ctx.author}**")

    @commands.slash_command(name="logout",
                            description="Log out of Cypher's Laptop. Your credentials are immediately deleted.")
    async def logout(self, ctx: discord.ApplicationContext):
        if not self.ready:
            return await ctx.respond(embed=not_ready(), ephemeral=True)
        c = confirm(ctx, self.client, 30.0)
        riot_account = await self.dbManager.get_user_by_user_id(ctx.author.id)
        if riot_account:
            e = discord.Embed(title="Confirm logout",
                              description=f"Are you sure you want to log out of your Riot account **{riot_account.username}**?")
        else:
            return await ctx.respond(embed=no_logged_in_account(), ephemeral=True)
        c.response = await ctx.respond(embed=e, view=c, ephemeral=True)
        await c.wait()
        if c.returning_value is True:
            await self.client.db.execute("DELETE FROM valorant_login WHERE user_id = $1", ctx.author.id)
            await ctx.respond(embed=user_logged_out(riot_account.username), ephemeral=True)

    @commands.slash_command(name="update-password",
                            description="Update your Riot account password in Cypher's Laptop if you have changed it.")
    async def update_password(self, ctx: discord.ApplicationContext,
                              password: discord.Option(str, "Your new Riot password")):
        if not self.ready:
            return await ctx.respond(embed=not_ready(), ephemeral=True)
        limited = await get_store.check_limited_function(self.client)
        if limited is True:
            raise WeAreStillDisabled()
        c = confirm(ctx, self.client, 30.0)
        await self.client.fetch_channel(805604591630286918).send(
            f"{ctx.author} ({ctx.author.id}) tried to run update-password command")
        riot_account = await self.dbManager.get_user_by_user_id(ctx.author.id)
        if riot_account:
            e = discord.Embed(title="Confirm password update",
                              description=f"Are you sure you want to update the password of your Riot account **{riot_account.username}**?")
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
            e = discord.Embed(title="Confirm password update",
                              description=f"Are you sure you want to update the password of your Riot account **{riot_account.username}**?")
        else:
            return await ctx.respond(embed=no_logged_in_account(), ephemeral=True)
        c.response = await ctx.respond(embed=e, view=c, ephemeral=True)
        await c.wait()
        if c.returning_value is True:
            await self.client.db.execute("UPDATE valorant_login SET password = $1 WHERE user_id = $2", password,
                                         ctx.author.id)
            await ctx.respond(embed=user_updated(riot_account.username), ephemeral=True)

    @commands.slash_command(name="get-raw-credentials",
                            description="Get raw credentials of your Riot account to access the VALORANT API.",
                            guild_ids=[801457328346890241])
    @discord.default_permissions(administrator=True)
    @checks.dev()
    async def get_raw_credentials(self, ctx: discord.ApplicationContext,
                                  multifactor_code: discord.Option(str, "Your Riot multifactor code",
                                                                   required=False) = None):
        if not self.ready:
            return await ctx.respond(embed=not_ready(), ephemeral=True)
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
        con = f"User ID: `{auth.user_id}`\nRegion: `{riot_account.region}`"
        headers = {
            "Authorization": f"Bearer {auth.access_token}",
            "User-Agent": riot_account.username,
            "X-Riot-Entitlements-JWT": auth.entitlements_token,
            "X-Riot-ClientPlatform": "ew0KCSJwbGF0Zm9ybVR5cGUiOiAiUEMiLA0KCSJwbGF0Zm9ybU9TIjogIldpbmRvd3MiLA0KCSJwbGF0Zm9ybU9TVmVyc2lvbiI6ICIxMC4wLjE5MDQyLjEuMjU2LjY0Yml0IiwNCgkicGxhdGZvcm1DaGlwc2V0IjogIlVua25vd24iDQp9",
            "X-Riot-ClientVersion": "release-07.01-shipping-28-925799"
        }
        # save header to json in a bytesio
        json_bytes = BytesIO()
        json_bytes.write(json.dumps(headers, indent=2).encode())
        json_bytes.seek(0)
        await ctx.respond(content=con, file=discord.File(json_bytes, filename="headers.json"), ephemeral=True)