import json
from io import BytesIO

import aiohttp
import discord
from discord import permissions
from discord.ext import commands

from main import clvt
from utils import riot_authorization, get_store, checks
from utils.helper import get_region_code
from utils.specialobjects import GunSkin
from utils.time import humanize_timedelta
from .database import DBManager
from utils.responses import *
from utils.buttons import confirm
import os
from dotenv import load_dotenv

load_dotenv()


class MainCommands(commands.Cog):
    def __init__(self, client):
        self.client: clvt = client
        self.dbManager: DBManager = DBManager(self.client.db)
        self.ready = False

    @commands.Cog.listener()
    async def on_ready(self):
        await self.client.wait_until_ready()
        self.dbManager = DBManager(self.client.db)
        self.ready = True

    async def valorant_skin_autocomplete(self, ctx: discord.AutocompleteContext):
        if not self.ready:
            return ["Cypher's Laptop is still booting up. Try again in a few seconds!"]
        sk = await self.dbManager.get_all_skins()

        if len(ctx.value) > 0:
            results = []
            for skin in sk:
                print(ctx.value.lower(), skin.displayName.lower())
                if ctx.value.lower() in skin.displayName.lower():
                    results.append(skin.displayName)
            return results[:25]

        else:

            for i in sk:
                print(i.displayName)
            return [s.displayName for s in sk[:25]]


    @commands.slash_command(name="balance", description="Retrieves your balance")
    async def balance(self, ctx: discord.ApplicationContext,
                      multifactor_code: discord.Option(str, "Your multifactor code", required=False) = None):
        if not self.ready:
            return await ctx.respond(embed=not_ready(), ephemeral=True)

    @commands.slash_command(name="login", description="Login to your Riot Games account.")
    async def login(self, ctx: discord.ApplicationContext,
                    username: discord.Option(str, "Your Riot username", required=True),
                    password: discord.Option(str, "Your Riot password. It is encrypted when stored in the database.", required=True),
                    region: discord.Option(str, "Your Riot region",
                                           choices=["Asia Pacific", "North America", "Europe", "Korea"], required=True),
                    ):
        if not self.ready:
            return await ctx.respond(embed=not_ready(), ephemeral=True)
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
        if not self.ready:
            return await ctx.respond(embed=not_ready(), ephemeral=True)
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
        if not self.ready:
            return await ctx.respond(embed=not_ready(), ephemeral=True)
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
        if not self.ready:
            return await ctx.respond(embed=not_ready(), ephemeral=True)
        riot_account = await self.dbManager.get_user_by_user_id(ctx.author.id)
        if riot_account:
            await ctx.defer()
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
        skin_uuids, remaining = await get_store.getStore(headers, auth.user_id, riot_account.region)
        embeds = []
        embeds.append(discord.Embed(title="Your current shop resets:", description=f"In **{humanize_timedelta(seconds=remaining)}**", color=3092790))
        for uuid in skin_uuids:
            sk = await self.dbManager.get_skin_by_uuid(uuid)
            if sk is not False:
                embeds.append(skin_embed(sk))

        await ctx.respond(embeds=embeds)
        print("Store fetch successful")
        return

    @commands.slash_command(name="get-raw-credentials", description="Get raw credentials of your Riot user to communicate with the VALORANT API.")
    @discord.default_permissions(administrator=True)
    @checks.dev()
    async def get_raw_credentials(self, ctx: discord.ApplicationContext, multifactor_code: discord.Option(str, "Your Riot multifactor code", required=False) = None):
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
            "X-Riot-ClientVersion": "pbe-shipping-55-604424"
        }
        # save header to json in a bytesio
        json_bytes = BytesIO()
        json_bytes.write(json.dumps(headers, indent=2).encode())
        json_bytes.seek(0)
        await ctx.respond(content=con, file=discord.File(json_bytes, filename="headers.json"), ephemeral=True)

    @commands.slash_command(name="skin", description="Search for a VALORANT gun skin")
    async def skin(self, ctx: discord.ApplicationContext, name: discord.Option(str, description="Skin name", autocomplete=valorant_skin_autocomplete)):
        if not self.ready:
            return await ctx.respond(embed=not_ready())
        skin = await self.dbManager.get_skin_by_name(name)
        if skin:
            await ctx.respond(embed=skin_embed(skin))
        else:
            await ctx.respond(embed=skin_not_found(name))

    @commands.slash_command(name="update_skins_database", description="Updates the internal skin database ")
    @discord.default_permissions(administrator=True)
    @checks.dev()
    async def update_skins_database(self, ctx: discord.ApplicationContext,
                                    multifactor_code: discord.Option(str, "Your Riot multifactor code", required=False) = None):
        riot_account = await self.dbManager.get_user_by_user_id(0)
        if riot_account:
            await ctx.defer(ephemeral=True)
        else:
            e = no_logged_in_account()
            e.description = "In the database, add a Riot Games account with the user ID 0 to use this command. This " \
                            "account will be used to fetch data from the Riot API without using your own account. "
            return await ctx.respond(embed=e, ephemeral=True)
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
        raw_offers = await get_store.getRawOffers(headers, riot_account.region)
        #print(raw_offers)
        all_skins = await get_store.getAllSkins()
        skins = []
        for s in all_skins:
            i = GunSkin()
            i.contentTierUUID = s["contentTierUuid"]
            if i.contentTierUUID is None:
                continue
            skin = s["levels"]
            for b in skin:
                i.displayName = b["displayName"]
                i.uuid = b["uuid"].lower()
                i.displayIcon = b["displayIcon"]
                for offer in raw_offers:
                    if offer["OfferID"].lower() == b["uuid"].lower():
                        print(offer)
                        i.cost = offer["Cost"]["85ad13f7-3d1b-5128-9eb2-7cd8ee0b5741"]
                        break
                skins.append(i)
                break
        for i in skins:
            await self.client.db.execute("INSERT INTO skins(uuid, displayname, cost, displayicon, contenttieruuid) "
                                         "VALUES ($1, $2, $3, $4, $5) ON CONFLICT(uuid) DO UPDATE SET displayName = "
                                         "$2, cost = $3, displayIcon = $4, contenttieruuid = $5", i.uuid,
                                         i.displayName, i.cost, i.displayIcon, i.contentTierUUID)
        await ctx.respond(embed=updated_weapon_database())

    @commands.slash_command(name="invite", description="Invite Cypher's Laptop to your server.")
    async def invite(self, ctx: discord.ApplicationContext):
        await ctx.respond(embed=discord.Embed(title="Invite Cypher's Laptop",
                                              description=f"https://discord.com/api/oauth2/authorize?client_id={self.client.user.id}&permissions=137439266880&scope=bot%20applications.commands", color=discord.Color.gold()))
