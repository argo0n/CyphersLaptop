import copy
import time
from datetime import timedelta, datetime

import discord
from discord.ext import commands, tasks


from cogs.maincommands.database import DBManager
from main import clvt
from utils.buttons import ThumbnailToImageOnly, EnterMultiFactor
from utils.errors import WeAreStillDisabled
from utils.format import box
from utils.responses import *
from utils.specialobjects import *
from utils import get_store, riot_authorization

class ViewStoreFromDaily(discord.ui.Button):
    def __init__(self, DBManager, cog):
        self.DBManager: DBManager = DBManager
        self.cog = cog
        super().__init__(label="View Store", custom_id="view_storev1")

    async def callback(self, interaction: discord.Interaction):
        message_date = interaction.message.created_at.date()
        date_asstr = message_date.strftime("%A, %d %B %y")
        riot_account: RiotUser = await self.DBManager.get_user_by_user_id(interaction.user.id)
        if riot_account is False:
            return await interaction.response.send_message(embed=ErrorEmbed(description="You do not have a Riot Games account logged in in Cypher's Laptop."))

        skins, remaining = await self.DBManager.get_store(interaction.user.id, riot_account.username, None, None, None, message_date)
        if skins is None:
            now_date = discord.utils.utcnow().date()
            if now_date != message_date:
                return await interaction.response.send_message(embed=no_cached_store(), ephemeral=True)
            else:
                await interaction.response.defer(ephemeral=True, invisible=False)
                try:
                    auth = riot_authorization.RiotAuth()
                    await auth.authorize(riot_account.username, riot_account.password)
                except riot_authorization.Exceptions.RiotAuthenticationError:
                    await interaction.followup.send(embed=authentication_error())
                    print("Authentication error")
                    return
                except riot_authorization.Exceptions.RiotRatelimitError:
                    await interaction.followup.send(embed=rate_limit_error())
                    print("Rate limited")
                    return
                except riot_authorization.Exceptions.RiotMultifactorError:
                    # No multifactor provided check
                    v = EnterMultiFactor()
                    m = await interaction.followup.send(embed=multifactor_detected(), ephemeral=True, wait=True)
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
                        await interaction.followup.send(embed=authentication_error(), ephemeral=True)
                        print("Authentication error")
                        return
                    except riot_authorization.Exceptions.RiotRatelimitError:
                        b.label = "Authentication failed"
                        b.emoji = discord.PartialEmoji.from_str("<:CL_False:1075296226620223499>")
                        await m.edit(view=v)
                        await interaction.followup.send(embed=rate_limit_error(), ephemeral=True)
                        print("Rate limited")
                        return
                    except riot_authorization.Exceptions.RiotMultifactorError:
                        b.label = "Authentication failed"
                        b.emoji = discord.PartialEmoji.from_str("<:CL_False:1075296226620223499>")
                        await m.edit(view=v)
                        await interaction.followup.send(embed=multifactor_error(), ephemeral=True)
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
                    "X-Riot-ClientVersion": "release-08.09-shipping-57-2521387"
                }
                try:
                    skins, remaining = await self.DBManager.get_store(interaction.user.id, riot_account.username, headers,
                                                                           auth.user_id, riot_account.region, None)
                except KeyError:
                    error_embed = discord.Embed(title="Cypher's Laptop was unable to fetch your store.",
                                                description="Cypher's Laptop contacted the Riot Games API, and Riot Games responded but did not provide any information about your store. this might be due to an [ongoing login issue](https://status.riotgames.com/valorant?regionap&locale=en_US).\n\nNontheless, this is a known issue and the developer is monitoring it. Try again in a few minutes to check your store!",
                                                embed=discord.Color.red())
                    if interaction.response.is_done():
                        method = await interaction.followup.send
                    else:
                        method = await interaction.response.send_message
                    return method(embed=error_embed)
                print("Store fetch successful")
        wishlisted = 0
        wishlist = await self.DBManager.get_user_wishlist(interaction.user.id)
        user_settings = await self.DBManager.fetch_user_settings(interaction.user.id)
        embed_description = date_asstr if message_date != discord.utils.utcnow().date() else f"Resets <t:{int(time.time()) + remaining}:R>"
        if riot_account:
            if user_settings.show_username:
                username = f"{riot_account.username}'s"
            else:
                username = f"{interaction.user.name}'s"
        else:
            username = "Your"
        base_embed = discord.Embed(title=f"{username} <:val:1046289333344288808> VALORANT Store", description=embed_description, color=interaction.client.embed_color)
        embeds = [base_embed]
        currency = await self.cog.get_currency_details(user_settings.currency)
        for skin in skins:
            sk: GunSkin = await self.DBManager.get_skin_by_uuid(skin)
            if sk.uuid in wishlist:
                wishlisted += 1
                is_wishlist = True
            else:
                is_wishlist = False
            embeds.append(skin_embed(sk, is_wishlist, currency))
        if wishlisted > 0:
            embeds[0].set_footer(text=f"You have {wishlisted} skins wishlisted in this store!", icon_url="https://cdn.discordapp.com/emojis/1046281227142975538.webp?size=96")
        if interaction.response.is_done():
            method = interaction.followup.send
        else:
            method = interaction.response.send_message

        await method(embeds=embeds, ephemeral=True, view=ThumbnailToImageOnly())


class EnableDisable(discord.ui.Button):
    def __init__(self, reminder_config: ReminderConfig):
        super().__init__(
            label="Enabled" if reminder_config.enabled else "Disabled",
            style=discord.ButtonStyle.green if reminder_config.enabled else discord.ButtonStyle.red
        )
        self.reminder_config = reminder_config

    async def callback(self, interaction: discord.Interaction):
        is_enabled = getattr(self.view.reminder_config, self.view.current_selected)
        if is_enabled:
            setattr(self.view.reminder_config, self.view.current_selected, False)
            self.update_button()
        else:
            setattr(self.view.reminder_config, self.view.current_selected, True)
            await self.view.reminder_config.update(interaction.client)
            self.update_button()
        await self.view.reminder_config.update(interaction.client)
        self.view.update_embed()
        await interaction.response.edit_message(view=self.view, embed=self.view.embed)

    def update_button(self):
        is_enabled = getattr(self.view.reminder_config, self.view.current_selected)
        if is_enabled:
            self.style = discord.ButtonStyle.green
            self.label = "Enabled"
        else:
            self.style = discord.ButtonStyle.red
            self.label = "Disabled"


class SelectSetting(discord.ui.Select):
    def __init__(self):
        self.respond_interaction: discord.Interaction = None
        self.selected = None
        options = [
            discord.SelectOption(label="Enable/Disable", value="enabled", description="Turn on or off your daily Store reminder.", default=True)
        ]
        super().__init__(placeholder="Choose a setting to configure", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        selected = self.values[0]
        for i in self.options:
            if i.value == selected:
                i.default = True
            else:
                i.default = False
        self.respond_interaction = interaction
        self.view.current_selected = selected
        self.view.button.update_button()
        self.view.update_embed()
        await interaction.response.edit_message(embed=self.view.embed, view=self.view)


enable_disable_embed = discord.Embed(title="Enable/Disable reminders", description="Enable/disable reminders for checking your VALORANT Store after it resets.", color=2829617).set_image(url="https://cdn.discordapp.com/attachments/1045172059002650715/1046774650119671828/CLreminders.png")
show_immediately_embed = discord.Embed(title="Show store immediately", description="When your Store reminder is sent, view your store immediately or click a button to see your skins.\n**This feature is unavailable at the moment.**", color=2829617).set_image(url="https://cdn.discordapp.com/attachments/1045172059002650715/1046776544372195388/CLnobutton.png")
picture_mode_embed = discord.Embed(title="Show as a picture", description="Show your skins as a picture or in 4 embeds.", color=2829617).set_image(url="https://cdn.discordapp.com/attachments/1045172059002650715/1046778074521403463/CLpicture.png")


class ViewStoreFromReminder(discord.ui.View):
    def __init__(self, DBManager, cog):
        super().__init__(timeout=None)
        self.add_item(ViewStoreFromDaily(DBManager, cog))


class ReminderSettingsView(discord.ui.View):
    def __init__(self, reminder_config: ReminderConfig):
        self.embed = enable_disable_embed
        self.current_selected = "enabled"
        self.reminder_config = reminder_config
        self.button = EnableDisable(self.reminder_config)
        super().__init__(timeout=None)

        self.add_item(SelectSetting())
        self.add_item(self.button)

    def update_embed(self):
        if self.current_selected == "enabled":
            self.embed = enable_disable_embed
        elif self.current_selected == "show_immediately":
            self.embed = show_immediately_embed
        elif self.current_selected == "picture_mode":
            self.embed = picture_mode_embed
        self.embed.color = discord.Color.green() if getattr(self.reminder_config, self.current_selected) else discord.Color.red()


class StoreReminder(commands.Cog):
    def __init__(self, client):
        self.client: clvt = client
        self.dbManager: DBManager = DBManager(self.client.db)

    @commands.slash_command(name="reminders", description="Configure your VALORANT Store reminders")
    async def reminder_cmd(self, ctx):
        user_settings = await self.dbManager.fetch_user_reminder_settings(ctx.author.id)
        view = ReminderSettingsView(user_settings)
        view.update_embed()
        await ctx.respond(embed=enable_disable_embed, view=view)
        await view.wait()

    @tasks.loop(hours=24)
    async def reminder_loop(self):
        todays_date = discord.utils.utcnow().date()
        reminders = await self.dbManager.fetch_reminders()
        limited = await get_store.check_limited_function(self.client)
        if limited is True:
            return
        for reminder in reminders:
            try:
                if not reminder.enabled:
                    continue
                try:
                    user = await self.client.fetch_user(reminder.user_id)
                except discord.NotFound:
                    continue
                notif_embed, actual_embed = store_here(False)
                # if reminder.show_immediately is not True: # show a button in the message, disabled for now as it is irrelevant
                try:
                    m = await user.send(embed=notif_embed, view=ViewStoreFromReminder(self.dbManager, self))
                    await m.edit(embed=actual_embed)
                except discord.Forbidden:
                    reminder.enabled = False
                    await reminder.update(self.client)
                except Exception as e:
                    print(e)
            except Exception as e:
                await self.client.error_channel.send(f"Error while processing store for {reminder.user_id}:\n{box(str(e), lang='py')}")
        await self.client.update_service_status("Daily Store Reminder", round(time.time()))

    @reminder_loop.before_loop
    async def wait_until_reset(self):
        await self.client.wait_until_ready()
        todays_date = discord.utils.utcnow().date()
        a = await self.client.db.fetch("SELECT * FROM cached_stores WHERE store_date = $1", todays_date)
        if len(a) < 1:
            # somehow no one's store was fetched, so we won't wait until 8am the next day.
            pass
        else:
            now = discord.utils.utcnow()
            next_run = now.replace(hour=0, minute=1, second=0) + timedelta(days=1)
            await discord.utils.sleep_until(next_run)
