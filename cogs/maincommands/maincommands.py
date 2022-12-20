import json
import time
from io import BytesIO

import aiohttp
import discord
from discord.ext import commands

from main import clvt
from utils import riot_authorization, get_store, checks
from utils.helper import get_region_code
from utils.specialobjects import GunSkin
from utils.time import humanize_timedelta
from .database import DBManager
from utils.responses import *
from utils.buttons import confirm, SingleURLButton, ThumbnailToImageOnly, ThumbnailAndWishlist
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

class EnterMultiFactor(discord.ui.View):
    def __init__(self):
        self.code = None
        self.modal = MultiFactorModal()
        super().__init__(timeout=180, disable_on_timeout=True)

    @discord.ui.button(label="Enter MFA Code", style=discord.ButtonStyle.green)
    async def callback(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.send_modal(self.modal)
        await self.modal.wait()
        button.disabled = True
        await interaction.message.edit(view=self)
        self.code = self.modal.children[0].value
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.message.interaction is not None:
            if interaction.message.interaction.user.id == interaction.user.id:
                return True
        await interaction.response.send_message("This is not for you!", ephemeral=True)
        return False




class MainCommands(StoreReminder, WishListManager, UpdateSkinDB, commands.Cog):
    def __init__(self, client):
        self.client: clvt = client
        self.dbManager: DBManager = DBManager(self.client.db)
        self.ready = False

    @commands.Cog.listener()
    async def on_ready(self):
        await self.client.wait_until_ready()
        self.dbManager = DBManager(self.client.db)
        self.ready = True
        self.reminder_loop.start()
        self.update_skin_db.start()
        self.client.add_view(ThumbnailAndWishlist(self.dbManager))
        self.client.add_view(ThumbnailToImageOnly())
        self.client.add_view(ViewStoreFromReminder(self.dbManager))

    async def fetch_currency_api(self):
        key = os.getenv("CURRENCY_API")
        async with aiohttp.ClientSession() as session:
            headers = {
                "apikey": key
            }
            async with session.get("https://api.freecurrencyapi.com/v1/latest", headers=headers) as resp:
                if resp.status == 200:
                    return (await resp.json())["data"]

    async def get_currencies(self):
        currency = await self.client.redis_pool.get("currency")
        if currency is None:
            currency = await self.fetch_currency_api()
            await self.client.redis_pool.set("currency", json.dumps(currency))
            await self.client.redis_pool.expire("currency", 86400)
        else:
            currency = json.loads(currency)
        return currency

    async def get_currency(self, currency_code: str):
        currency = await self.get_currencies()
        if currency_code.upper() in currency:
            return currency[currency_code.upper()]
        else:
            return None

    async def get_currency_details(self, currency_code: str):
        with open("assets/currencies.json") as f:
            currencies = json.load(f)
        a = currencies["data"].get(currency_code.upper(), None)
        if a is not None and a["vp_per_dollar"] == 0:
            a["exch"] = await self.get_currency(a["code"])
        return a

    async def valorant_skin_autocomplete(self, ctx: discord.AutocompleteContext):
        if not self.ready:
            return ["Cypher's Laptop is still booting up. Try again in a few seconds!"]
        sk = await self.dbManager.get_all_skins()

        if len(ctx.value) > 0:
            results = []
            for skin in sk:
                if ctx.value.lower() in skin.displayName.lower():
                    results.append(skin.displayName)
            return results[:25]
        else:
            return [s.displayName for s in sk[:25]]

    @commands.slash_command(name="balance", description="View your VALORANT points and Radianite balance.")
    async def balance(self, ctx: discord.ApplicationContext):
        if not self.ready:
            return await ctx.respond(embed=not_ready(), ephemeral=True)
        riot_account = await self.dbManager.get_user_by_user_id(ctx.author.id)
        if riot_account:
            await ctx.defer()
        else:
            return await ctx.respond(embed=no_logged_in_account(), ephemeral=True)
        try:
            auth = riot_authorization.RiotAuth()
            await auth.authorize(riot_account.username, riot_account.password)
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
            v = EnterMultiFactor()
            await ctx.respond(embed=multifactor_detected(), view=v)
            await v.wait()
            if v.code is None:
                return
            try:
                auth = riot_authorization.RiotAuth()
                await auth.authorize(riot_account.username, riot_account.password, multifactor_code=v.code)
            except riot_authorization.Exceptions.RiotAuthenticationError:
                await v.modal.interaction.edit_original_response(embed=authentication_error(), delete_after=30.0)
                print("Authentication error")
                return
            except riot_authorization.Exceptions.RiotRatelimitError:
                await v.modal.interaction.edit_original_response(embed=rate_limit_error(), delete_after=30.0)
                print("Rate limited")
                return
            except riot_authorization.Exceptions.RiotMultifactorError:
                await v.modal.interaction.edit_original_response(embed=multifactor_error(), delete_after=30.0)
                print("Multifactor error")
                return
            await v.modal.interaction.edit_original_response(embed=authentication_success(), delete_after=30.0)
        headers = {
            "Authorization": f"Bearer {auth.access_token}",
            "User-Agent": riot_account.username,
            "X-Riot-Entitlements-JWT": auth.entitlements_token,
            "X-Riot-ClientPlatform": "ew0KCSJwbGF0Zm9ybVR5cGUiOiAiUEMiLA0KCSJwbGF0Zm9ybU9TIjogIldpbmRvd3MiLA0KCSJwbGF0Zm9ybU9TVmVyc2lvbiI6ICIxMC4wLjE5MDQyLjEuMjU2LjY0Yml0IiwNCgkicGxhdGZvcm1DaGlwc2V0IjogIlVua25vd24iDQp9",
            "X-Riot-ClientVersion": "pbe-shipping-55-604424"
        }
        vp, rp = await get_store.getBalance(headers, auth.user_id, riot_account.region)
        embed = discord.Embed(title=f"{riot_account.username}'s Balance",
                              description=f"<:vp:1045605973005434940> {comma_number(vp)}\n<:rp:1045991796838256640> {comma_number(rp)}",
                              color=discord.Color.blurple())
        await ctx.respond(embed=embed)

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

    @commands.slash_command(name="store", description="Retrieves your VALORANT Store.")
    async def store(self, ctx: discord.ApplicationContext):
        if not self.ready:
            return await ctx.respond(embed=not_ready(), ephemeral=True)
        riot_account = await self.dbManager.get_user_by_user_id(ctx.author.id)
        if riot_account:
            await ctx.defer()
        else:
            return await ctx.respond(embed=no_logged_in_account(), ephemeral=True)
        try:
            auth = riot_authorization.RiotAuth()
            await auth.authorize(riot_account.username, riot_account.password)
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
            v = EnterMultiFactor()
            await ctx.respond(embed=multifactor_detected(), view=v)
            await v.wait()
            if v.code is None:
                return
            try:
                auth = riot_authorization.RiotAuth()
                await auth.authorize(riot_account.username, riot_account.password, multifactor_code=v.code)
            except riot_authorization.Exceptions.RiotAuthenticationError:
                await v.modal.interaction.edit_original_response(embed=authentication_error(), delete_after=30.0)
                print("Authentication error")
                return
            except riot_authorization.Exceptions.RiotRatelimitError:
                await v.modal.interaction.edit_original_response(embed=rate_limit_error(), delete_after=30.0)
                print("Rate limited")
                return
            except riot_authorization.Exceptions.RiotMultifactorError:
                await v.modal.interaction.edit_original_response(embed=multifactor_error(), delete_after=30.0)
                print("Multifactor error")
                return
            await v.modal.interaction.edit_original_response(embed=authentication_success(), delete_after=30.0)
        headers = {
            "Authorization": f"Bearer {auth.access_token}",
            "User-Agent": riot_account.username,
            "X-Riot-Entitlements-JWT": auth.entitlements_token,
            "X-Riot-ClientPlatform": "ew0KCSJwbGF0Zm9ybVR5cGUiOiAiUEMiLA0KCSJwbGF0Zm9ybU9TIjogIldpbmRvd3MiLA0KCSJwbGF0Zm9ybU9TVmVyc2lvbiI6ICIxMC4wLjE5MDQyLjEuMjU2LjY0Yml0IiwNCgkicGxhdGZvcm1DaGlwc2V0IjogIlVua25vd24iDQp9",
            "X-Riot-ClientVersion": "pbe-shipping-55-604424"
        }
        skin_uuids, remaining = await get_store.getStore(headers, auth.user_id, riot_account.region)
        user_settings = await self.dbManager.fetch_user_settings(ctx.author.id)
        usrn = riot_account.username if user_settings.show_username else ctx.author.name
        embeds = [discord.Embed(title=f"{usrn}'s <:val:1046289333344288808> VALORANT Store ",
                                description=f"Resets <t:{int(time.time()) + remaining}:R>", color=3092790)]
        currency = await self.get_currency_details(user_settings.currency)
        wishlisted_skins = await self.dbManager.get_user_wishlist(ctx.author.id)
        wishlisted = 0
        for uuid in skin_uuids:
            sk = await self.dbManager.get_skin_by_uuid(uuid)
            if sk is not False:
                if sk.uuid in wishlisted_skins:
                    wishlisted += 1
                    is_in_wishlist = True
                else:
                    is_in_wishlist = False
                embeds.append(skin_embed(sk, is_in_wishlist, currency))
        if len(embeds) > 0 and wishlisted > 0:
            embeds[0].set_footer(text=f"There are skins from your wishlist!",
                                 icon_url="https://cdn.discordapp.com/emojis/1046281227142975538.webp?size=96")

        await ctx.respond(embeds=embeds, view=ThumbnailToImageOnly())
        print("Store fetch successful")
        return

    @commands.slash_command(name="get-raw-credentials",
                            description="Get raw credentials of your Riot account to access the VALORANT API.", guild_ids=[801457328346890241])
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
            "X-Riot-ClientVersion": "pbe-shipping-55-604424"
        }
        # save header to json in a bytesio
        json_bytes = BytesIO()
        json_bytes.write(json.dumps(headers, indent=2).encode())
        json_bytes.seek(0)
        await ctx.respond(content=con, file=discord.File(json_bytes, filename="headers.json"), ephemeral=True)

    @commands.slash_command(name="skin", description="Search for a VALORANT gun skin.")
    async def skin(self, ctx: discord.ApplicationContext,
                   name: discord.Option(str, description="Skin name", autocomplete=valorant_skin_autocomplete)):
        if not self.ready:
            return await ctx.respond(embed=not_ready())
        skin = await self.dbManager.get_skin_by_name(name)
        wishlist = await self.dbManager.get_user_wishlist(ctx.author.id)
        if skin:
            view = ThumbnailAndWishlist(self.dbManager, skin, skin.uuid in wishlist)
            user_settings = await self.dbManager.fetch_user_settings(ctx.author.id)
            currency = await self.get_currency_details(user_settings.currency)
            await ctx.respond(embed=skin_embed(skin, False, currency), view=view)
        else:
            await ctx.respond(embed=skin_not_found(name))

    @checks.dev()
    @commands.slash_command(name="update_skins_database",
                            description="Manually update the internal VALORANT gun skins database.", guild_ids=[801457328346890241])
    @discord.default_permissions(administrator=True)
    async def update_skins_database(self, ctx: discord.ApplicationContext,
                                    multifactor_code: discord.Option(str, "Your Riot multifactor code",
                                                                     required=False) = None):
        riot_account = await self.dbManager.get_user_by_user_id(0)
        if riot_account:
            await ctx.defer(ephemeral=True)
        else:
            e = no_logged_in_account()
            e.description = "In the database, add a Riot account with the user ID 0 to use this command. This " \
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
        # print(raw_offers)
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
        await self.client.update_service_status("Skin Database Update", round(time.time()), None)

    @commands.slash_command(name="help", description="See all of Cypher's Laptop commands.")
    async def help(self, ctx: discord.ApplicationContext):
        await ctx.respond(embed=help_command(await self.client.is_dev(ctx.author.id)))

    @commands.slash_command(name="about", description="About Cypher's Laptop.")
    async def about(self, ctx: discord.ApplicationContext):
        embed = discord.Embed(
            title="Nothing stays hidden from Cypher. Nothing. Not even your <:val:1046289333344288808> VALORANT Store.",
            description="Cypher's Laptop helps you track your <:val:1046289333344288808> Store, to make sure you never miss out on your favorite skin.",
            color=discord.Color.blue())
        embed.add_field(name="Features",
                        value="• **Check** and **Track** your VALORANT Store with a wishlist\n• **Search** for VALORANT gun skins\n• View your <:vp:1045605973005434940> <:rp:1045991796838256640> Balance\n• Get daily reminders to check your store\n",
                        inline=False)
        embed.add_field(name="Get started",
                        value="1) Login to your Riot account through the </login:1045213188209258518> command. Your password is encrypted and stored securely.\n2) Run </store:1045171702612639836> to check your VALORANT Store!\n\nA login isn't required for seraching skins. You can log out anytime, and your credentials are deleted immediately from our storage.",
                        inline=False)
        # embed.add_field(name="\u200b", value="\u200b", inline=False)
        embed.add_field(name="Developer", value="Argon#0002", inline=True)
        embed.add_field(name="Privacy",
                        value="Passwords are encrypted with Fernet and stored in a secure database. Not even the developer can view them.", inline=True)
        embed.add_field(name="Source",
                        value="[GitHub](https://github.com/argo0n/CyphersLaptop)",
                        inline=True)
        embed.add_field(name="Thanks",
                        value="[Valorina](https://github.com/sanjaybaskaran01/Valorina), [Valemporium](https://github.com/PureAspiration/Valemporium), [ValorantClientAPI](https://github.com/HeyM1ke/ValorantClientAPI), [python-riot-auth](https://github.com/floxay/python-riot-auth), [Valorant-API](https://valorant-api.com/)",
                        inline=True)
        embed.set_footer(
            text="Cypher's Laptop is not endorsed by Riot Games and does not reflect the views or opinions of Riot Games or anyone officially involved in producing or managing Riot Games properties. Riot Games and all associated properties are trademarks or registered trademarks of Riot Games, Inc.")
        await ctx.respond(embed=embed)

    @commands.slash_command(name="invite", description="Invite Cypher's Laptop to your server!")
    async def invite(self, ctx: discord.ApplicationContext):
        embed = discord.Embed(title="Cypher's Laptop - A VALORANT Store tracking bot on Discord",
                              description="Nothing stays hidden from Cypher. Nothing. Not even your VALORANT Store.\nCypher's Laptop helps you track your VALORANT Store, to make sure you never miss out on your favorite skin.",
                              color=0x2f3136)
        embed.set_image(
            url="https://cdn.discordapp.com/attachments/805604591630286918/1045968296488480818/CyphersLaptopWideEdited.png")

        await ctx.respond(embed=embed, view=SingleURLButton(text="Click here to invite Cypher's Laptop",
                                                            link=f"https://discord.com/api/oauth2/authorize?client_id={self.client.user.id}&permissions=137439266880&scope=bot%20applications.commands"))
