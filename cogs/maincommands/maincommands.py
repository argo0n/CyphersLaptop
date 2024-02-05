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
from utils.specialobjects import GunSkin, PlayerCard, PlayerTitle, Spray, Buddy
from utils.time import humanize_timedelta
from .account_management import AccountManagement
from .database import DBManager
from utils.responses import *
from utils.buttons import confirm, SingleURLButton, ThumbnailToImageOnly, ThumbnailAndWishlist, ThumbWishViewVariants, \
    NightMarketView, EnterMultiFactor
import os
from dotenv import load_dotenv

from .update_skin_db import UpdateSkinDB
from .wishlist import WishListManager
from .reminders import StoreReminder, ViewStoreFromReminder

load_dotenv()


class MainCommands(AccountManagement, StoreReminder, WishListManager, UpdateSkinDB, commands.Cog):
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
        self.client.add_view(ThumbWishViewVariants(self.dbManager))
        self.client.add_view(ThumbnailToImageOnly())
        self.client.add_view(ViewStoreFromReminder(self.dbManager, self))

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
        if currency_code is None:
            return None
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

    async def valorant_accessory_autocomplete(self, ctx: discord.AutocompleteContext):
        if not self.ready:
            return ["Cypher's Laptop is still booting up. Try again in a few seconds!"]
        ac = await self.dbManager.get_all_accessories()
        selected_type = ctx.options.get("type")
        print(selected_type)
        if selected_type == "Player Card":
            ac = [a for a in ac if isinstance(a, PlayerCard)]
        elif selected_type == "Player Title":
            ac = [a for a in ac if isinstance(a, PlayerTitle)]
        elif selected_type == "Spray":
            ac = [a for a in ac if isinstance(a, Spray)]
        elif selected_type == "Gun Buddy":
            ac = [a for a in ac if isinstance(a, Buddy)]
        else:
            print("No type filter")
        if len(ctx.value) > 0:
            results = []
            for a in ac:
                if ctx.value.lower() in a.name.lower():
                    results.append(a.name)
            return results[:25]
        else:
            return [a.name for a in ac[:25]]

    skin_option = discord.Option(str, description="Skin name", autocomplete=valorant_skin_autocomplete)

    @commands.slash_command(name="balance", description="View your VALORANT points and Radianite balance.")
    async def balance(self, ctx: discord.ApplicationContext):
        if not self.ready:
            return await ctx.respond(embed=not_ready(), ephemeral=True)
        limited = await get_store.check_limited_function(self.client)
        if limited is True:
            raise WeAreStillDisabled()
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
            await ctx.respond(embed=multifactor_detected())
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
            "X-Riot-ClientVersion": "release-07.01-shipping-28-925799"
        }
        vp, rp, kc, fa = await get_store.getBalance(headers, auth.user_id, riot_account.region)
        user_settings = await self.dbManager.fetch_user_settings(ctx.author.id)
        usrn = riot_account.username if user_settings.show_username else ctx.author.name
        embed = discord.Embed(title=f"{usrn}'s Balance", color=discord.Color.blurple())
        embed.add_field(name="VALORANT Points", value=f"<:vp:1045605973005434940> {comma_number(vp)}", inline=True)
        embed.add_field(name="Radianite Points", value=f"<:rp:1045991796838256640> {comma_number(rp)}", inline=True)
        embed.add_field(name="Kingdom Credits", value=f"<:kc:1138772116058144808> {comma_number(kc)}", inline=True)
        embed.add_field(name="Free Agents", value=f"<:fa:1138772043832250478> {comma_number(fa)}", inline=True)
        await ctx.respond(embed=embed)

    @commands.slash_command(name="night-market", description="Check your VALORANT Night Market.")
    async def night_market(self, ctx: discord.ApplicationContext):
        if not self.ready:
            return await ctx.respond(embed=not_ready(), ephemeral=True)
        limited = await get_store.check_limited_function(self.client)
        if limited is True:
            raise WeAreStillDisabled()
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
            m = await ctx.respond(embed=multifactor_detected())
            await v.wait()
            b: discord.ui.Button = v.children[0]
            if v.code is None:
                return
            try:
                auth = riot_authorization.RiotAuth()
                await auth.authorize(riot_account.username, riot_account.password, multifactor_code=v.code)
            except riot_authorization.Exceptions.RiotAuthenticationError:
                b.label = "Authentication failed"
                b.emoji = discord.PartialEmoji.from_str("<:CL_False:1075296226620223499>")
                await m.edit(view=v)
                await ctx.respond(embed=authentication_error(), delete_after=30.0)
                print("Authentication error")
                return
            except riot_authorization.Exceptions.RiotRatelimitError:
                b.label = "Authentication failed"
                b.emoji = discord.PartialEmoji.from_str("<:CL_False:1075296226620223499>")
                await m.edit(view=v)
                await ctx.respond(embed=rate_limit_error(), delete_after=30.0)
                print("Rate limited")
                return
            except riot_authorization.Exceptions.RiotMultifactorError:
                b.label = "Authentication failed"
                b.emoji = discord.PartialEmoji.from_str("<:CL_False:1075296226620223499>")
                await m.edit(view=v)
                await ctx.respond(embed=multifactor_error(), delete_after=30.0)
                print("Multifactor error")
                return
            # await v.modal.interaction.edit_original_response(embed=authentication_success(), delete_after=30.0)
            b.label = "Authentication Success"
            b.emoji = discord.PartialEmoji.from_str("<:CL_True:1075296198598066238>")
            await m.edit(view=v)
        headers = {
            "Authorization": f"Bearer {auth.access_token}",
            "User-Agent": riot_account.username,
            "X-Riot-Entitlements-JWT": auth.entitlements_token,
            "X-Riot-ClientPlatform": "ew0KCSJwbGF0Zm9ybVR5cGUiOiAiUEMiLA0KCSJwbGF0Zm9ybU9TIjogIldpbmRvd3MiLA0KCSJwbGF0Zm9ybU9TVmVyc2lvbiI6ICIxMC4wLjE5MDQyLjEuMjU2LjY0Yml0IiwNCgkicGxhdGZvcm1DaGlwc2V0IjogIlVua25vd24iDQp9",
            "X-Riot-ClientVersion": "release-07.01-shipping-28-925799"
        }
        skins, remaining = await get_store.getNightMarket(headers, auth.user_id, riot_account.region)
        if skins is None:
            if time.time() < 1680652800:
                embed = night_market_closed(True)
            else:
                embed = night_market_closed(False)
            return await ctx.respond(embed=embed, view=SingleURLButton("https://twitter.com/PlayVALORANT", "@PlayVALORANT on Twitter", emoji=discord.PartialEmoji.from_str("<:twitter:1060408863360286783>")))
        user_settings = await self.dbManager.fetch_user_settings(ctx.author.id)
        usrn = riot_account.username if user_settings.show_username else ctx.author.name
        if remaining > 432000:
            desc = f"Ends on <t:{int(time.time() + remaining)}:D>"
        else:
            desc = f"Ends in <t:{int(time.time()) + remaining}:R>"
        embeds = [discord.Embed(title=f"{usrn}'s <:val:1046289333344288808> VALORANT Night Market",
                                description=desc, color=0xf990db)]
        currency = await self.get_currency_details(user_settings.currency)
        wishlisted_skins = await self.dbManager.get_user_wishlist(ctx.author.id)
        wishlisted = 0
        nm_skins = []
        shown_embeds = []
        for uuid, org_cost, discounted_p, discounted_cost, is_seen in skins:
            sk = await self.dbManager.get_nightmarket_skin(uuid)
            if sk is not False:
                if sk.uuid in wishlisted_skins:
                    wishlisted += 1
                    is_in_wishlist = True
                else:
                    is_in_wishlist = False
                sk.discounted_p = discounted_p
                sk.seen = is_seen
                sk.discounted_cost = discounted_cost
                sk.seen = is_seen
                embeds.append(skin_embed(sk, is_in_wishlist, currency, discounted_p, discounted_cost, is_seen))
                shown_embeds.append(skin_embed(sk, is_in_wishlist, currency, discounted_p, discounted_cost, True))
                nm_skins.append(sk)
        if len(embeds) > 0 and wishlisted > 0:
            embeds[0].set_footer(text=f"There are skins from your wishlist!",
                                 icon_url="https://cdn.discordapp.com/emojis/1046281227142975538.webp?size=96")

        await ctx.respond(embeds=embeds, view=NightMarketView(
            ctx.author,
            nm_skins[0], shown_embeds[0],
            nm_skins[1], shown_embeds[1],
            nm_skins[2], shown_embeds[2],
            nm_skins[3], shown_embeds[3],
            nm_skins[4], shown_embeds[4],
            nm_skins[5], shown_embeds[5]
        ))
        print("Store fetch successful")
        return

    @commands.slash_command(name="store", description="Check your VALORANT Store.")
    async def store(self, ctx: discord.ApplicationContext):
        if not self.ready:
            return await ctx.respond(embed=not_ready(), ephemeral=True)
        limited = await get_store.check_limited_function(self.client)
        if ctx.author.id != 650647680837484556 and limited is True:
            raise WeAreStillDisabled()
        riot_account = await self.dbManager.get_user_by_user_id(ctx.author.id)
        if riot_account:
            await ctx.defer()
        else:
            return await ctx.respond(embed=no_logged_in_account(), ephemeral=True)
        # attempt to fetch store from cache first, if no record exists we'll run it again
        skin_uuids, remaining = await self.dbManager.get_store(ctx.author.id, riot_account.username, None, None, None)
        if skin_uuids is None:
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
                m = await ctx.respond(embed=multifactor_detected())
                await v.wait()
                b: discord.ui.Button = v.children[0]
                if v.code is None:
                    return
                try:
                    auth = riot_authorization.RiotAuth()
                    await auth.authorize(riot_account.username, riot_account.password, multifactor_code=v.code)
                except riot_authorization.Exceptions.RiotAuthenticationError:
                    b.label = "Authentication failed"
                    b.emoji = discord.PartialEmoji.from_str("<:CL_False:1075296226620223499>")
                    await m.edit(view=v)
                    await ctx.respond(embed=authentication_error(), delete_after=30.0)
                    print("Authentication error")
                    return
                except riot_authorization.Exceptions.RiotRatelimitError:
                    b.label = "Authentication failed"
                    b.emoji = discord.PartialEmoji.from_str("<:CL_False:1075296226620223499>")
                    await m.edit(view=v)
                    await ctx.respond(embed=rate_limit_error(), delete_after=30.0)
                    print("Rate limited")
                    return
                except riot_authorization.Exceptions.RiotMultifactorError:
                    b.label = "Authentication failed"
                    b.emoji = discord.PartialEmoji.from_str("<:CL_False:1075296226620223499>")
                    await m.edit(view=v)
                    await ctx.respond(embed=multifactor_error(), delete_after=30.0)
                    print("Multifactor error")
                    return
                #await v.modal.interaction.edit_original_response(embed=authentication_success(), delete_after=30.0)
                b.label = "Authentication Success"
                b.emoji = discord.PartialEmoji.from_str("<:CL_True:1075296198598066238>")
                await m.edit(view=v)
            headers = {
                "Authorization": f"Bearer {auth.access_token}",
                "User-Agent": riot_account.username,
                "X-Riot-Entitlements-JWT": auth.entitlements_token,
                "X-Riot-ClientPlatform": "ew0KCSJwbGF0Zm9ybVR5cGUiOiAiUEMiLA0KCSJwbGF0Zm9ybU9TIjogIldpbmRvd3MiLA0KCSJwbGF0Zm9ybU9TVmVyc2lvbiI6ICIxMC4wLjE5MDQyLjEuMjU2LjY0Yml0IiwNCgkicGxhdGZvcm1DaGlwc2V0IjogIlVua25vd24iDQp9",
                "X-Riot-ClientVersion": "release-07.01-shipping-28-925799"
            }
            try:
                skin_uuids, remaining = await self.dbManager.get_store(ctx.author.id, riot_account.username, headers, auth.user_id, riot_account.region)
            except KeyError:
                error_embed = discord.Embed(title="Cypher's Laptop was unable to fetch your store.", description="Cypher's Laptop contacted the Riot Games API, and Riot Games responded but did not provide any information about your store. this might be due to an [ongoing login issue](https://status.riotgames.com/valorant?regionap&locale=en_US).\n\nNontheless, this is a known issue and the developer is monitoring it. Try again in a few minutes to check your store!", embed=discord.Color.red())
                return await ctx.respond(embed=error_embed)
        onetimestore = await self.client.db.fetchrow("SELECT skin1_uuid, skin2_uuid, skin3_uuid, skin4_uuid FROM onetimestores WHERE user_id = $1", ctx.author.id)
        if onetimestore:
            skin_uuids = [onetimestore.get('skin1_uuid'), onetimestore.get('skin2_uuid'), onetimestore.get('skin3_uuid'), onetimestore.get('skin4_uuid')]
            await self.client.db.execute("DELETE FROM onetimestores WHERE user_id = $1", ctx.author.id)
        user_settings = await self.dbManager.fetch_user_settings(ctx.author.id)
        usrn = riot_account.username if user_settings.show_username else ctx.author.name
        embeds = [discord.Embed(title=f"{usrn}'s <:val:1046289333344288808> VALORANT Store ",
                                description=f"Resets <t:{int(time.time()) + remaining}:R>", color=self.client.embed_color)]
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

    @commands.slash_command(name="skin", description="Search for a VALORANT gun skin.")
    async def skin(self, ctx: discord.ApplicationContext,
                   name: skin_option):
        if not self.ready:
            return await ctx.respond(embed=not_ready())
        skin = await self.dbManager.get_skin_by_name_or_uuid(name)
        wishlist = await self.dbManager.get_user_wishlist(ctx.author.id)
        if skin:
            view = ThumbWishViewVariants(self.dbManager, skin, skin.uuid in wishlist)
            user_settings = await self.dbManager.fetch_user_settings(ctx.author.id)
            currency = await self.get_currency_details(user_settings.currency)
            e = skin_embed(skin, skin.uuid in wishlist, currency)
            if await self.client.is_dev(ctx.author.id):
                c = f"`{skin.uuid}`"
            else:
                c = None
            await ctx.respond(c, embed=skin_embed(skin, False, currency), view=view)
        else:
            await ctx.respond(embed=skin_not_found(name))

    accessory_option = discord.Option(str, description="Accessory name", autocomplete=valorant_accessory_autocomplete)
    acc_type_option = discord.Option(str, description="A Player Card, Title, Spray or Gun Buddy", choices=["Player Card", "Player Title", "Spray", "Gun Buddy"], required=False, name="type")

    @commands.slash_command(name="accessory", description="Search for a Gun Buddy, Spray, Player Card or Player Title.")
    async def find_accessory(self, ctx: discord.ApplicationContext, name: accessory_option, accessory_type: acc_type_option = None):
        if not self.ready:
            return await ctx.respond(embed=not_ready())
        accessory = await self.dbManager.get_accessory_by_name_or_uuid(name)
        if accessory:
            #user_settings = await self.dbManager.fetch_user_settings(ctx.author.id)
            #currency = await self.get_currency_details(user_settings.currency)
            e = await accessory_embed(accessory)
            if await self.client.is_dev(ctx.author.id):
                c = f"`{accessory.uuid}`"
            else:
                c = None
            await ctx.respond(c, embed=e)
        else:
            await ctx.respond(embed=accessory_not_found(name, accessory_type))

    @checks.dev()
    @commands.slash_command(name="update_skins_database",
                            description="Manually update the internal VALORANT gun skins database.", guild_ids=[801457328346890241])
    @discord.default_permissions(administrator=True)
    async def update_skins_database(self, ctx: discord.ApplicationContext):
        riot_account = await self.dbManager.get_user_by_user_id(0)
        if riot_account:
            await ctx.defer(ephemeral=True)
        else:
            e = no_logged_in_account()
            e.description = "In the database, add a Riot account with the user ID 0 to use this command. This " \
                            "account will be used to fetch data from the Riot API without using your own account. "
            return await ctx.respond(embed=e, ephemeral=True)
        await self.update_skin_db()
        await ctx.respond(embed=updated_weapon_database())

    @discord.default_permissions(administrator=True)
    @checks.dev()
    @commands.slash_command(name="onetimestore", description="Generate a Store that shows once for a user.", guild_ids=[801457328346890241])
    async def one_time_store(self, ctx: discord.ApplicationContext,
                             user_id: str,
                             skin1: discord.Option(str, description="Skin name", autocomplete=valorant_skin_autocomplete),
                             skin2: discord.Option(str, description="Skin name", autocomplete=valorant_skin_autocomplete),
                             skin3: discord.Option(str, description="Skin name", autocomplete=valorant_skin_autocomplete),
                             skin4: discord.Option(str, description="Skin name", autocomplete=valorant_skin_autocomplete)):
        us = await self.client.get_or_fetch_user(int(user_id))
        if us is None:
            return await ctx.respond(embed=discord.Embed(title="User not found", description=f"User with ID {user_id} not found.", color=discord.Color.red()))
        skin1_ob = await self.dbManager.get_skin_by_name_or_uuid(skin1)
        if skin1_ob is None:
            return await ctx.respond(embed=discord.Embed(title="Skin not found", description=f"Skin `{skin1}` not found.", color=discord.Color.red()))
        skin2_ob = await self.dbManager.get_skin_by_name_or_uuid(skin2)
        if skin2_ob is None:
            return await ctx.respond(embed=discord.Embed(title="Skin not found", description=f"Skin `{skin2}` not found.", color=discord.Color.red()))
        skin3_ob = await self.dbManager.get_skin_by_name_or_uuid(skin3)
        if skin3_ob is None:
            return await ctx.respond(embed=discord.Embed(title="Skin not found", description=f"Skin `{skin3}` not found.", color=discord.Color.red()))
        skin4_ob = await self.dbManager.get_skin_by_name_or_uuid(skin4)
        if skin4_ob is None:
            return await ctx.respond(embed=discord.Embed(title="Skin not found", description=f"Skin `{skin4}` not found.", color=discord.Color.red()))
        await self.dbManager.insert_onetimestore(int(user_id), skin1_ob.uuid, skin2_ob.uuid, skin3_ob.uuid, skin4_ob.uuid)
        await ctx.respond(embed=discord.Embed(title="One Time Store created", description=f"Created a One Time Store for {us.mention} with the skins `{skin1_ob.displayName}`, `{skin2_ob.displayName}`, `{skin3_ob.displayName}`, `{skin4_ob.displayName}`.", color=discord.Color.green()))




