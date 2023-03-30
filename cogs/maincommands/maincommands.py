import json
import random
import time
import datetime
from io import BytesIO

import aiohttp
import discord
from discord.ext import commands

from main import clvt
from utils import riot_authorization, get_store, checks
from utils.format import print_exception
from utils.helper import get_region_code
from utils.specialobjects import GunSkin
from utils.time import humanize_timedelta
from .account_management import AccountManagement
from .database import DBManager
from utils.responses import *
from utils.buttons import confirm, SingleURLButton, ThumbnailToImageOnly, ThumbnailAndWishlist, ThumbWishViewVariants, \
    NightMarketView
import os
from dotenv import load_dotenv

from .update_skin_db import UpdateSkinDB
from .wishlist import WishListManager
from .reminders import StoreReminder, ViewStoreFromReminder

load_dotenv()


class UserGuildSelectView(discord.ui.View):
    def __init__(self, author, skin1, skin2, skin3, skin4):
        self.author = author
        self.target_user = None
        self.skin1: GunSkin = skin1
        self.skin2: GunSkin = skin2
        self.skin3: GunSkin = skin3
        self.skin4: GunSkin = skin4
        super().__init__(timeout=15 * 60)

    @discord.ui.user_select(placeholder="Select a member to prank!")
    async def select_callback(self, select, interaction):
        self.target_user = select.values[0]
        for b in self.children:
            if isinstance(b, discord.ui.Button) and "Confirm" in b.label:
                if not self.target_user.bot:
                    b.disabled = False
                else:
                    b.disabled = True
        await interaction.response.edit_message(embed=self.format_fake_store(), view=self)

    @discord.ui.button(label="Confirm", disabled=True, style=discord.ButtonStyle.green)
    async def confirm_callback(self, button, interaction: discord.Interaction):
        try:
            await interaction.client.db.execute("INSERT INTO april_fools_stores(target_user_id, creator_user_id, skin1_uuid, skin2_uuid, skin3_uuid, skin4_uuid) VALUES($1, $2, $3, $4, $5, $6)", self.target_user.id, interaction.user.id, self.skin1.uuid, self.skin2.uuid, self.skin3.uuid, self.skin4.uuid)
        except Exception as e:
            print_exception("Ignoring Exception in User Select View:", error=e)
            await interaction.response.send_message(embed=ErrorEmbed(description="I was unable to save the fake Store. Try again later."), ephemeral=True)
        else:
            self.disable_all_items()
            await interaction.response.edit_message(view=self)
            await interaction.followup.send(embed=SuccessEmbed(description=f"**{self.target_user.name}** will be pranked by your fake Store on April 1!"), ephemeral=True)


    @discord.ui.button(label="Cancel", disabled=False, style=discord.ButtonStyle.red)
    async def cancel_callback(self, button, interaction):
        self.disable_all_items()
        embed = self.format_fake_store()
        embed.description = "Cancelled. No Store was added."
        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()

    def format_fake_store(self):
        tier_data = get_tier_data()
        embed = discord.Embed(title="April Fools Prank Store", color=2829617)
        embed.set_author(name="Cypher's Laptop",
                         icon_url="https://cdn.discordapp.com/avatars/844489130822074390/ab663738f44bf18062f0a5f77cf4ebdd.png?size=32")
        if self.target_user is None:
            target_user_qualifies = False
            user_str = "\_\_\_\_\_\_\_\_\_\_"
        else:
            target_user_qualifies = True
            user_str = f"{self.target_user.name}#{self.target_user.discriminator}"
        if self.target_user:
            if self.target_user == self.author:
                description = [f"I don't know why you want to show **yourself** a fake Store, but ok.\nThis fake Store will appear when **{user_str}** runs </store:1045171702612639836> on April Fools' Day:", ""]
            elif self.target_user.bot:
                description = [f"**You cannot give bots fake Stores.**. They can't see it anyways.", ""]
                target_user_qualifies = False
            else:
                description = [f"This fake Store will appear when **{user_str}** runs </store:1045171702612639836> on April Fools' Day:", ""]
        else:
            description = [f"This fake Store will appear when **{user_str}** runs </store:1045171702612639836> on April Fools' Day:", ""]
        for skin in [self.skin1, self.skin2, self.skin3, self.skin4]:
            if skin is not None:
                tier_emoji = " "
                for tier in tier_data:
                    if tier["uuid"] == skin.contentTierUUID:
                        tier_emoji = tier["emoji"]
                cost = f"<:vp:1045605973005434940> {comma_number(skin.cost)}" if skin.cost is not None else "<:DVB_False:887589731515392000> Not on sale"
                skin_str = f"{tier_emoji} **{skin.displayName}** {cost}"
            else:
                skin_str = f"\_\_\_\_\_\_\_\_\_\_ <:vp:1045605973005434940> 0"
            description.append(skin_str)
        description.append("")
        if self.target_user is None or not target_user_qualifies:
            description.append("Select a user to prank!")
        else:
            description.append("Press **Confirm** to submit the fake Store.\nIt cannot be removed or edited once you submit it, but you can make new ones!")
        embed.description = "\n".join(description)
        return embed


class RequestForUserID(discord.ui.Modal):
    def __init__(self):
        self.target_user = None
        super().__init__(discord.ui.InputText(label="User ID goes here", placeholder="Enable Developer Mode to find someone's User ID"), title="Input User ID")

    async def callback(self, interaction: discord.Interaction):
        value = self.children[0].value.strip()
        try:
            us = await interaction.client.fetch_user(int(value))
        except ValueError:
            if "#" in self.children[0].value:
                await interaction.response.send_message(embed=ErrorEmbed(description="It appears you've tried to enter the full Username#Discriminator (User#1234) of a user.\nUnfortunately, due to Discord's limits, we cannot identify who this user is.\n\nWe require their User ID to identify them."), ephemeral=True)
            else:
                await interaction.response.send_message(embed=ErrorEmbed(description="It appears you didn't enter a User ID. We need a user's ID (consisting of numbers) to identify them."), ephemeral=True)
        except discord.NotFound:
            await interaction.response.send_message(embed=ErrorEmbed(description=f"I couldn't find someone with the user ID {value}."), ephemeral=True)
        else:
            await interaction.response.send_message(embed=SuccessEmbed(description=f"Found user **{us}**!"), ephemeral=True)
            self.target_user = us
        self.stop()


class UserDMSelectView(discord.ui.View):
    def __init__(self, author, skin1, skin2, skin3, skin4):
        self.author = author
        self.target_user = None
        self.skin1: GunSkin = skin1
        self.skin2: GunSkin = skin2
        self.skin3: GunSkin = skin3
        self.skin4: GunSkin = skin4
        super().__init__(timeout=15 * 60)

    @discord.ui.button(label="Enter your target's User ID", )
    async def modal_callback(self, select, interaction):
        modal = RequestForUserID()
        await interaction.response.send_modal(modal)
        await modal.wait()
        if modal.target_user is not None:
            self.target_user = modal.target_user
            for b in self.children:
                if isinstance(b, discord.ui.Button) and "Confirm" in b.label:
                    if not self.target_user.bot:
                        b.disabled = False
                    else:
                        b.disabled = True
        await interaction.edit_original_response(embed=self.format_fake_store(), view=self)

    @discord.ui.button(label="Confirm", disabled=True, style=discord.ButtonStyle.green, row=1)
    async def confirm_callback(self, button, interaction: discord.Interaction):
        try:
            await interaction.client.db.execute("INSERT INTO april_fools_stores(target_user_id, creator_user_id, skin1_uuid, skin2_uuid, skin3_uuid, skin4_uuid) VALUES($1, $2, $3, $4, $5, $6)", self.target_user.id, interaction.user.id, self.skin1.uuid, self.skin2.uuid, self.skin3.uuid, self.skin4.uuid)
        except Exception as e:
            print_exception("Ignoring Exception in User Select View:", error=e)
            await interaction.response.send_message(embed=ErrorEmbed(description="I was unable to save the fake Store. Try again later."), ephemeral=True)
        else:
            self.disable_all_items()
            await interaction.response.send_message(embed=SuccessEmbed(description=f"**{self.target_user.name}** will be pranked by your fake Store on April 1!"), ephemeral=True)
            await interaction.edit_original_response(view=self)

    @discord.ui.button(label="Cancel", disabled=False, style=discord.ButtonStyle.red, row=1)
    async def cancel_callback(self, button, interaction):
        self.disable_all_items()
        embed = self.format_fake_store()
        embed.description = "Cancelled. No Store was added."
        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()

    def format_fake_store(self):
        tier_data = get_tier_data()
        embed = discord.Embed(title="April Fools Prank Store", color=2829617)
        embed.set_author(name="Cypher's Laptop",
                         icon_url="https://cdn.discordapp.com/avatars/844489130822074390/ab663738f44bf18062f0a5f77cf4ebdd.png?size=32")
        if self.target_user is None:
            target_user_qualifies = False
            user_str = "\_\_\_\_\_\_\_\_\_\_"
        else:
            target_user_qualifies = True
            user_str = f"{self.target_user.name}#{self.target_user.discriminator}"
        if self.target_user:
            if self.target_user == self.author:
                description = [f"I don't know why you want to show **yourself** a fake Store, but ok.\nThis fake Store will appear when **{user_str}** runs </store:1045171702612639836> on April Fools' Day:", ""]
            elif self.target_user.bot:
                description = [f"**You cannot give bots fake Stores.**. They can't see it anyways.", ""]
                target_user_qualifies = False
            else:
                description = [f"This fake Store will appear when **{user_str}** runs </store:1045171702612639836> on April Fools' Day:", ""]
        else:
            description = [f"This fake Store will appear when **{user_str}** runs </store:1045171702612639836> on April Fools' Day:", ""]
        for skin in [self.skin1, self.skin2, self.skin3, self.skin4]:
            if skin is not None:
                tier_emoji = " "
                for tier in tier_data:
                    if tier["uuid"] == skin.contentTierUUID:
                        tier_emoji = tier["emoji"]
                cost = f"<:vp:1045605973005434940> {comma_number(skin.cost)}" if skin.cost is not None else "<:DVB_False:887589731515392000> Not on sale"
                skin_str = f"{tier_emoji} **{skin.displayName}** {cost}"
            else:
                skin_str = f"\_\_\_\_\_\_\_\_\_\_ <:vp:1045605973005434940> 0"
            description.append(skin_str)
        description.append("")
        if self.target_user is None or not target_user_qualifies:
            description.append("Select a user to prank!")
        else:
            description.append("Press **Confirm** to submit the fake Store.\nIt cannot be removed or edited once you submit it, but you can make new ones!")
        embed.description = "\n".join(description)
        return embed

class MultiFactorModal(discord.ui.Modal):
    def __init__(self):
        self.interaction: discord.Interaction = None
        super().__init__(title="Enter MFA Code", timeout=180.0)
        self.add_item(
            discord.ui.InputText(label="Enter your MFA Code", placeholder="123456", min_length=6, max_length=6)
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        #await interaction.response.send_message(embed=authenticating(True))
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
        button.emoji = discord.PartialEmoji.from_str("<a:CL_Loading:1081263238202794196>")
        button.label = "Authenticating code..."
        button.style = discord.ButtonStyle.grey
        await interaction.message.edit(view=self)
        self.code = self.modal.children[0].value
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.message.interaction is not None:
            if interaction.message.interaction.user.id == interaction.user.id:
                return True
        await interaction.response.send_message("This is not for you!", ephemeral=True)
        return False


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

    skin_option = discord.Option(str, description="Skin name", autocomplete=valorant_skin_autocomplete)

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
        user_settings = await self.dbManager.fetch_user_settings(ctx.author.id)
        usrn = riot_account.username if user_settings.show_username else ctx.author.name
        embed = discord.Embed(title=f"{usrn}'s Balance",
                              description=f"<:vp:1045605973005434940> {comma_number(vp)}\n<:rp:1045991796838256640> {comma_number(rp)}",
                              color=discord.Color.blurple())
        await ctx.respond(embed=embed)

    @commands.slash_command(name="night-market", description="Check your VALORANT Night Market.")
    async def night_market(self, ctx: discord.ApplicationContext):
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
            m = await ctx.respond(embed=multifactor_detected(), view=v)
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
            "X-Riot-ClientVersion": "pbe-shipping-55-604424"
        }
        skins, remaining = await get_store.getNightMarket(headers, auth.user_id, riot_account.region)
        if skins is None:
            if time.time() < 1676878310:
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
                print(sk.cost)
                sk.discounted_p = discounted_p
                sk.seen = is_seen
                sk.discounted_cost = discounted_cost
                sk.seen = is_seen
                embeds.append(skin_embed(sk, is_in_wishlist, currency, discounted_p, discounted_cost, is_seen))
                print(sk.cost, discounted_cost)
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
                m = await ctx.respond(embed=multifactor_detected(), view=v)
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
                "X-Riot-ClientVersion": "pbe-shipping-55-604424"
            }
            try:
                skin_uuids, remaining = await self.dbManager.get_store(ctx.author.id, riot_account.username, headers, auth.user_id, riot_account.region)
            except KeyError:
                error_embed = discord.Embed(title="Cypher's Laptop was unable to fetch your store.", description="Cypher's Laptop contacted the Riot Games API, and Riot Games responded but did not provide any information about your store. this might be due to an [ongoing login issue](https://status.riotgames.com/valorant?regionap&locale=en_US).\n\nNontheless, this is a known issue and the developer is monitoring it. Try again in a few minutes to check your store!", embed=discord.Color.red())
                return await ctx.respond(embed=error_embed)
        date_now = discord.utils.utcnow().date()
        april_fools_day = datetime.date(2023, 4, 1)
        user_settings = await self.dbManager.fetch_user_settings(ctx.author.id)
        usrn = riot_account.username if user_settings.show_username else ctx.author.name
        if date_now == april_fools_day:
            april_fools_store = await self.client.db.fetchrow(
                "SELECT store_id, skin1_uuid, skin2_uuid, skin3_uuid, skin4_uuid FROM april_fools_stores WHERE target_user_id = $1 ORDER BY store_id LIMIT 1",
                ctx.author.id)
            if april_fools_store:
                skin_uuids = [april_fools_store.get('skin1_uuid'), april_fools_store.get('skin2_uuid'),
                              april_fools_store.get('skin3_uuid'), april_fools_store.get('skin4_uuid')]
                await self.client.db.execute("DELETE FROM april_fools_stores WHERE store_id = $1",
                                             april_fools_store.get('store_id'))
                embed_title = ''.join(random.choice([str.upper, str.lower])(char) for char in
                                      f"{usrn}'s <:val:1046289333344288808> VALORANT Store")
            else:
                embed_title = f"{usrn}'s <:val:1046289333344288808> VALORANT Store "
        else:
            embed_title = f"{usrn}'s <:val:1046289333344288808> VALORANT Store "
        user_settings = await self.dbManager.fetch_user_settings(ctx.author.id)
        usrn = riot_account.username if user_settings.show_username else ctx.author.name
        embeds = [discord.Embed(title=embed_title,
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

    @commands.slash_command(name="fakestore", description="Generate a fake VALORANT Store for your friend that shows up on April 1!")
    async def fake_store(self, ctx: discord.ApplicationContext,
                             skin1: discord.Option(str, description="1st skin",
                                                   autocomplete=valorant_skin_autocomplete),
                             skin2: discord.Option(str, description="2nd fake skin",
                                                   autocomplete=valorant_skin_autocomplete),
                             skin3: discord.Option(str, description="3rd fake skin",
                                                   autocomplete=valorant_skin_autocomplete),
                             skin4: discord.Option(str, description="4th fake skin",
                                                   autocomplete=valorant_skin_autocomplete)):
        if not self.ready:
            return await ctx.respond(embed=not_ready())
        skin1_ob = await self.dbManager.get_skin_by_name_or_uuid(skin1)
        if skin1_ob is None:
            return await ctx.respond(
                embed=discord.Embed(title="Skin not found", description=f"Skin `{skin1}` not found.",
                                    color=discord.Color.red()))
        skin2_ob = await self.dbManager.get_skin_by_name_or_uuid(skin2)
        if skin2_ob is None:
            return await ctx.respond(
                embed=discord.Embed(title="Skin not found", description=f"Skin `{skin2}` not found.",
                                    color=discord.Color.red()))
        skin3_ob = await self.dbManager.get_skin_by_name_or_uuid(skin3)
        if skin3_ob is None:
            return await ctx.respond(
                embed=discord.Embed(title="Skin not found", description=f"Skin `{skin3}` not found.",
                                    color=discord.Color.red()))
        skin4_ob = await self.dbManager.get_skin_by_name_or_uuid(skin4)
        if skin4_ob is None:
            return await ctx.respond(
                embed=discord.Embed(title="Skin not found", description=f"Skin `{skin4}` not found.",
                                    color=discord.Color.red()))

        view = UserGuildSelectView(ctx.author, skin1_ob, skin2_ob, skin3_ob, skin4_ob) if ctx.guild is not None else UserDMSelectView(ctx.author, skin1_ob, skin2_ob, skin3_ob, skin4_ob)
        await ctx.respond(embed=view.format_fake_store(), view=view, ephemeral=True)

