from urllib.parse import urlencode

import time
import inspect
import asyncio
import discord
import contextlib
from discord import ui
from typing import Optional, Any, Union, Dict, Type, Iterable
from functools import partial
import time

from cogs.maincommands.database import DBManager
from utils.context import CLVTcontext
from discord.ext import commands, pages
from utils.context import CLVTcontext
from utils.helper import BaseEmbed
from utils.responses import *
from utils.specialobjects import GunSkin, NightMarketGunSkin


accept_reasons = {
    "Approved (Future update)": "Your suggestion has been approved and will appear in a future update!\nThank you for making suggestions for Cypher's Laptop, and we can't wait to hear more of your ideas :)",
    "Approved (Now)": "Your suggestion has been approved and is appearing in this new update!\nCheck the changelogs, and thank you for making suggestions for Cypher's Laptop!"
}

reject_reasons = {
    "Spam": "Your suggestion has been denied as it has been identified as spam. Avoid making nonsensical suggestions or access to Cypher's Laptop may be restricted.",
    "Duplicate": "Your suggestion has been denied as a similar suggestion has already been made by another user. You are still welcome to make new suggestions!",
    "Off-Topic": "Your suggestion has been denied as it does not fit with the purpose of Cypher's Laptop. Make sure your suggestions are relevant to Cypher's Laptop's main functionalities!",
    "Inappropriate": "Your suggestion has been denied as it contains inappropriate or offensive content. Such material is not acceptable and will NOT be implemented in Cypher's Laptop.",
    "Technical Limitations": "Your suggestion has been denied as it is not possible to implement due to technical limitations. We do appreciate your ideas though, keep them coming!",
    "Already Planned": "Your suggestion has been denied as it is already in our development roadmap. Look out for it in a future update!",
    "Not Enough Information": "Your suggestion has been denied as it lacks necessary details for us to fully understand and implement it. Provide as much information as possible to help us evaluate your suggestion."

}
def bundle_responses_into_embeds(responses: list[tuple], base_embed: Optional[discord.Embed] = None):
    embeds = []
    if len(responses) == 0:
        embed = base_embed or discord.Embed()
        embed.description = "No responses so far."
        embeds.append(embed)
    for response_chunk in discord.utils.as_chunks(responses, 5):
        embed = base_embed or discord.Embed()
        embed.color = 2829617
        for response in response_chunk:
            embed.add_field(name=response[0], value=response[1], inline=False)
        embeds.append(embed)
    return embeds




class SingleURLButton(discord.ui.View):
    def __init__(self, link: str, text: str, emoji=None, timeout=None):
        super().__init__(timeout=timeout, disable_on_timeout=True)
        self.add_item(discord.ui.Button(label=text, url=link, emoji=emoji))

class confirm(discord.ui.View):
    def __init__(self, ctx: Union[CLVTcontext, discord.ApplicationContext], client, timeout):
        self.timeout = timeout or 30
        self.context = ctx
        self.response = None
        self.client = client
        self.returning_value = None
        super().__init__(timeout=timeout)

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.green)
    async def yes(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.returning_value = True
        for b in self.children:
            if b != button:
                b.style = discord.ButtonStyle.grey
            b.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()

    @discord.ui.button(label="No", style=discord.ButtonStyle.red)
    async def no(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.returning_value = False
        for b in self.children:
            if b != button:
                b.style = discord.ButtonStyle.grey
            print(b)
            b.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        ctx = self.context
        author = ctx.author
        if interaction.user != author:
            await interaction.response.send_message("These buttons aren't for you!", ephemeral=True)
            return False
        return True

    async def on_timeout(self) -> None:
        self.returning_value = None
        for b in self.children:
            b.disabled = True
        if isinstance(self.response, discord.Message):
            await self.response.edit(view=self)
        elif isinstance(self.response, discord.Interaction):
            await self.response.edit_original_response(view=self)


class AddToWishListButton(discord.ui.Button):
    def __init__(self, db_manager: DBManager, skin: Optional[GunSkin] = None, is_in_wishlist: Optional[bool] = None):
        # skin and user id is only for initializing the button style, during execution we use data from the message
        self.db_manager = db_manager
        if is_in_wishlist is not True:
            emoji = discord.PartialEmoji.from_str("<:naWL_gun:1047023572826206288>")
            label = "Add to wishlist"
            style = discord.ButtonStyle.grey
        else:
            emoji = discord.PartialEmoji.from_str("<:wlGUN:1046281227142975538>")
            label = "Wishlisted"
            style = discord.ButtonStyle.green

        super().__init__(label=label, emoji=emoji, style=style, custom_id="add_to_wishlist_v1")

    async def callback(self, interaction: discord.Interaction):
        user = interaction.user
        skin_name = interaction.message.embeds[0].title
        skin = await self.db_manager.get_skin_by_name_or_uuid(skin_name)
        if skin is False:
            return await interaction.response.send_message(skin_not_found(skin_name), ephemeral=True)
        wishlist = await self.db_manager.get_user_wishlist(interaction.user.id)
        if skin.uuid not in wishlist:
            await self.db_manager.add_skin_to_wishlist(user.id, skin.uuid)
            add = True
            new_style = discord.ButtonStyle.green
            new_emoji = discord.PartialEmoji.from_str("<:wlGUN:1046281227142975538>")
            new_label = "Wishlisted"
        else:
            await self.db_manager.remove_skin_from_wishlist(user.id, skin.uuid)
            add = False
            new_style = discord.ButtonStyle.grey
            new_emoji = discord.PartialEmoji.from_str("<:naWL_gun:1047023572826206288>")
            new_label = "Add to wishlist"
        if interaction.message.interaction is not None:
            if interaction.user.id == interaction.message.interaction.user.id:
                self.style, self.emoji, self.label = new_style, new_emoji, new_label
                await interaction.response.edit_message(view=self.view)
        embed = skin_added_to_wishlist(skin.displayName) if add else skin_removed_from_wishlist(skin.displayName)
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)

class BaseButton(ui.Button):
    def __init__(self, *, style: discord.ButtonStyle, selected: Union[int, str], row: int,
                 label: Optional[str] = None, **kwargs: Any):
        super().__init__(style=style, label=label or selected, row=row, **kwargs)
        self.selected = selected

    async def callback(self, interaction: discord.Interaction) -> None:
        raise NotImplementedError

class BaseView(ui.View):
    def reset_timeout(self):
        self.set_timeout(time.monotonic() + self.timeout)

    def set_timeout(self, new_time):
        self._View_timeout_expiry = new_time

class CallbackView(BaseView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for b in self.children:
            self.wrap(b)

    def wrap(self, b):
        callback = b.callback
        b.callback = partial(self.handle_callback, callback, b)

    async def handle_callback(self, callback, item, interaction):
        pass

    def add_item(self, item: ui.Item) -> None:
        self.wrap(item)
        super().add_item(item)

class ViewButtonIteration(BaseView):
    def __init__(self, *args: Any, mapper: Optional[Dict[str, Any]] = None,
                 button: Optional[Type[BaseButton]] = BaseButton, style: Optional[discord.ButtonStyle] = None):
        super().__init__()
        self.mapper = mapper
        for c, button_row in enumerate(args):
            for button_col in button_row:
                if isinstance(button_col, button):
                    self.add_item(button_col)
                elif isinstance(button_col, dict):
                    self.add_item(button(style=style, row=c, **button_col))
                elif isinstance(button_col, tuple):
                    selected, button_col = button_col
                    self.add_item(button(style=style, row=c, selected=selected, **button_col))
                else:
                    self.add_item(button(style=style, row=c, selected=button_col))

class ViewAuthor(BaseView):
    def __init__(self, ctx: CLVTcontext, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.context = ctx
        self.is_command = ctx.command is not None
        self.cooldown = commands.CooldownMapping.from_cooldown(1, 10, commands.BucketType.user)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        ctx = self.context
        author = ctx.author
        if interaction.user.id == 321892489470410763:
            return True
        if interaction.user != author:
            bucket = self.cooldown.get_bucket(ctx.message)
            if not bucket.update_rate_limit():
                if self.is_command:
                    command = ctx.bot.help_command.get_command_name(ctx.command, ctx=ctx)
                    content = f"Only `{author}` can use this. If you want to use it, use `{command}`"
                else:
                    content = f"Only `{author}` can use this."
                embed = BaseEmbed.to_error(description=content)
                await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True


class NightMarketSkinReveal(discord.ui.Button):
    def __init__(self, skin: NightMarketGunSkin, seen: bool, index: int, respond_embed: discord.Embed):
        tier_uuids = get_tier_data()
        tier = next((x for x in tier_uuids if x["uuid"] == skin.contentTierUUID), None)
        self.tier_details = tier
        self.skin = skin
        self.seen = seen
        self.index = index
        self.respond_embed = respond_embed
        super().__init__(style=discord.ButtonStyle.blurple if not seen else discord.ButtonStyle.grey, label=str(index+1), emoji=tier["nm_emoji"], disabled=seen)

    async def callback(self, interaction: discord.Interaction):
        embeds = interaction.message.embeds
        embeds[self.index+1] = self.respond_embed
        self.disabled = True
        self.style = discord.ButtonStyle.grey
        await interaction.response.edit_message(embeds=embeds, view=self.view)


class NightMarketView(discord.ui.View):
    def __init__(self,
                 user: discord.User,
                 skin1: NightMarketGunSkin, skin1_embed: discord.Embed,
                 skin2: NightMarketGunSkin, skin2_embed: discord.Embed,
                 skin3: NightMarketGunSkin, skin3_embed: discord.Embed,
                 skin4: NightMarketGunSkin, skin4_embed: discord.Embed,
                 skin5: NightMarketGunSkin, skin5_embed: discord.Embed,
                 skin6: NightMarketGunSkin, skin6_embed: discord.Embed
                 ):
        super().__init__(timeout=3600, disable_on_timeout=True)
        self.user = user
        self.add_item(NightMarketSkinReveal(skin1, skin1.seen, 0, skin1_embed))
        self.add_item(NightMarketSkinReveal(skin2, skin2.seen, 1, skin2_embed))
        self.add_item(NightMarketSkinReveal(skin3, skin3.seen, 2, skin3_embed))
        self.add_item(NightMarketSkinReveal(skin4, skin4.seen, 3, skin4_embed))
        self.add_item(NightMarketSkinReveal(skin5, skin5.seen, 4, skin5_embed))
        self.add_item(NightMarketSkinReveal(skin6, skin6.seen, 5, skin6_embed))

    @discord.ui.button(style=discord.ButtonStyle.green, emoji=discord.PartialEmoji.from_str("<:expand:1080746652815593572>"), custom_id="expand_v1", row=2)
    async def image(self, button: discord.ui.Button, interaction: discord.Interaction):
        new_embeds = []
        for embed in interaction.message.embeds:
            if (type(embed.image.url) == str and "nm" in embed.image.url.lower()) or (type(embed.thumbnail.url) == str and "nm" in embed.thumbnail.url.lower()):
                new_embeds.append(embed)
                continue
            if 'expand' in button.emoji.name:
                new_emoji = discord.PartialEmoji.from_str("<:shrink:1080748791390543923>")
                if embed.thumbnail:
                    embed.set_image(url=embed.thumbnail.url)
                    embed.set_thumbnail(url=discord.Embed.Empty)
            elif 'shrink' in button.emoji.name:
                new_emoji = discord.PartialEmoji.from_str("<:expand:1080746652815593572>")
                if embed.image:
                    embed.set_thumbnail(url=embed.image.url)
                    embed.set_image(url=discord.Embed.Empty)
            new_embeds.append(embed)
        button.emoji = new_emoji
        await interaction.response.edit_message(embeds=new_embeds, view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.user.id != interaction.user.id:
            await interaction.response.send_message("These buttons aren't for you!", ephemeral=True)
            return False
        return True


class ThumbnailToImageOnly(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(style=discord.ButtonStyle.green, emoji=discord.PartialEmoji.from_str("<:expand:1080746652815593572>"), custom_id="expand_v1")
    async def image(self, button: discord.ui.Button, interaction: discord.Interaction):
        new_embeds = []
        for embed in interaction.message.embeds:
            if (type(embed.image.url) == str and "nm" in embed.image.url.lower()) or (type(embed.thumbnail.url) == str and "nm" in embed.thumbnail.url.lower()):
                new_embeds.append(embed)
                continue
            if 'expand' in button.emoji.name:
                new_emoji = discord.PartialEmoji.from_str("<:shrink:1080748791390543923>")
                if embed.thumbnail:
                    embed.set_image(url=embed.thumbnail.url)
                    embed.set_thumbnail(url=discord.Embed.Empty)
            elif 'shrink' in button.emoji.name:
                new_emoji = discord.PartialEmoji.from_str("<:expand:1080746652815593572>")
                if embed.image:
                    embed.set_thumbnail(url=embed.image.url)
                    embed.set_image(url=discord.Embed.Empty)
            new_embeds.append(embed)
        button.emoji = new_emoji
        await interaction.response.edit_message(embeds=new_embeds, view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.message.interaction is not None:
            if interaction.user.id != interaction.message.interaction.user.id:
                await interaction.response.send_message("These buttons aren't for you!", ephemeral=True)
                return False
        return True


class ThumbnailAndWishlist(discord.ui.View):
    def __init__(self, db_manager: DBManager, skin: Optional[GunSkin] = None, is_in_wishlist: Optional[bool] = None):
        self.db_manager = db_manager
        self.skin = skin
        self.is_in_wishlist = is_in_wishlist
        super().__init__(timeout=None)
        self.add_item(AddToWishListButton(db_manager=self.db_manager, skin=self.skin, is_in_wishlist=self.is_in_wishlist))

    @discord.ui.button(style=discord.ButtonStyle.green, emoji=discord.PartialEmoji.from_str("<:expand:1080746652815593572>"), custom_id="expand_v2")
    async def image(self, button: discord.ui.Button, interaction: discord.Interaction):
        new_embeds = []
        for embed in interaction.message.embeds:
            if (type(embed.image.url) == str and "nm" in embed.image.url.lower()) or (type(embed.thumbnail.url) == str and "nm" in embed.thumbnail.url.lower()):
                new_embeds.append(embed)
                continue
            if 'expand' in button.emoji.name:
                new_emoji = discord.PartialEmoji.from_str("<:shrink:1080748791390543923>")
                if embed.thumbnail:
                    embed.set_image(url=embed.thumbnail.url)
                    embed.set_thumbnail(url=discord.Embed.Empty)
            elif 'shrink' in button.emoji.name:
                new_emoji = discord.PartialEmoji.from_str("<:expand:1080746652815593572>")
                if embed.image:
                    embed.set_thumbnail(url=embed.image.url)
                    embed.set_image(url=discord.Embed.Empty)
            new_embeds.append(embed)
        button.emoji = new_emoji
        await interaction.response.edit_message(embeds=new_embeds, view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.data.get('custom_id', None) == "add_to_wishlist_v1":
            return True
        if interaction.message.interaction is not None:
            if interaction.user.id != interaction.message.interaction.user.id:
                await interaction.response.send_message("These buttons aren't for you!", ephemeral=True)
                return False
        return True


class ViewChromaVariants(discord.ui.Select):
    def __init__(self, skin):
        self.skin = skin
        if self.skin is not None:
            options = []
            if len(self.skin.chromas) > 2:
                for index, chroma in enumerate(self.skin.chromas):
                    chroma_name = chroma.get('chroma_name')
                    name = chroma.get('name')
                    uuid = chroma.get('uuid')
                    options.append(
                        discord.SelectOption(label=chroma_name, description=name, value=uuid, default=index==0)
                    )
            else:
                options.append(discord.SelectOption(label="No variants available"))
            super().__init__(placeholder="Select a chroma", options=options, disabled=len(self.skin.chromas) < 2)

    async def callback(self, interaction: discord.Interaction):
        self.view.selected_chroma = self.values[0]
        if self.view.selected_level is not None:
            bu = self.view.get_item(self.view.selected_level)
            bu.style = discord.ButtonStyle.grey
        self.view.selected_level = None
        for op in self.options:
            if op.value == self.view.selected_chroma:
                op.default = True
            else:
                op.default = False
        self.view.format_content_and_embed()
        await interaction.response.edit_message(content=self.view.content, embed=self.view.embed, view=self.view)


class ViewLevelVariants(discord.ui.Button):
    def __init__(self, level):
        super().__init__(label=level.get('levelName') or "Base Level", custom_id=level.get('uuid'), style=discord.ButtonStyle.grey)

    async def callback(self, interaction: discord.Interaction):
        if self.style == discord.ButtonStyle.blurple:
            self.view.selected_level = None
        else:
            self.view.selected_level = self.custom_id
        for i in self.view.children:
            if isinstance(i, discord.ui.Button):
                if i.custom_id == self.view.selected_level:
                    i.style = discord.ButtonStyle.blurple
                else:
                    i.style = discord.ButtonStyle.grey
        self.view.format_content_and_embed()
        await interaction.response.edit_message(content=self.view.content, embed=self.view.embed, view=self.view)


class ViewVariants(discord.ui.View):
    def __init__(self, db_manager: DBManager, skin: Optional[GunSkin] = None):
        self.db_manager = db_manager
        self.skin = skin
        self.selected_chroma = skin.chromas[0].get('uuid')
        self.selected_level = None
        self.content = None
        self.embed = None
        super().__init__(timeout=None, disable_on_timeout=True)

        self.add_item(ViewChromaVariants(self.skin))
        for level in skin.levels:
            self.add_item(ViewLevelVariants(level))

    def format_content_and_embed(self):
        if self.selected_level is not None:
            for level in self.skin.levels:
                if level.get('uuid') == self.selected_level:
                    title = self.skin.displayName
                    if level.get('levelName') is not None:
                        title += " " + level.get('levelName')
                    if (video_url := level.get('video')) is not None:
                        params = urlencode({"url": video_url, "text": title})
                        self.content = f"[{title}](https://cypherslaptop.nogra.xyz/video?{params})"
                        self.embed = None
                    elif (display_icon := level.get('displayIcon')) is not None:
                        self.embed = discord.Embed(title=title, color=2829617).set_image(url=display_icon).set_footer(text="If no image appears, select the level to reload it.")
                        self.content = None
                    else:
                        self.embed = discord.Embed(title=title, color=2829617).set_image(url="https://cdn.discordapp.com/attachments/1046947484150284390/1061895579359252531/no_image.jpg")
                        self.content = None
                    break
        else:
            if len(self.skin.chromas) < 2:
                chroma = self.skin.chromas[0]
                title = chroma.get('name')
                if chroma.get('chroma_name') and chroma.get('chroma_name') != title:
                    title += " - " + chroma.get('chroma_name')
                if self.skin.chromas[0].get('displayIcon') is None:
                    disp = self.skin.displayIcon
                else:
                    disp = self.skin.chromas[0].get('displayIcon')
                self.embed = discord.Embed(title=title, color=2829617).set_image(url=disp)
                self.content = None
                return
            for chroma in self.skin.chromas:
                if chroma.get('uuid') == self.selected_chroma:
                    title = chroma.get('name')
                    if chroma.get('chroma_name') and chroma.get('chroma_name') != title:
                        title += " - " + chroma.get('chroma_name')
                    if (video_url := chroma.get('video')) is not None:
                        params = urlencode({"url": video_url, "text": title})
                        self.content = f"[{title}](https://cypherslaptop.nogra.xyz/video?{params})"
                        self.embed = None
                    elif (display_icon := chroma.get('displayIcon')) is not None:
                        self.embed = discord.Embed(title=title, color=2829617).set_image(url=display_icon).set_footer(text="If no image appears, select the chroma to reload it.")
                        self.content = None
                    else:
                        self.embed = discord.Embed(title=title, color=2829617).set_image(
                            url="https://cdn.discordapp.com/attachments/1046947484150284390/1061895579359252531/no_image.jpg")
                        self.content = None
                    break


class ThumbWishViewVariants(discord.ui.View):
    def __init__(self, db_manager: DBManager, skin: Optional[GunSkin] = None, is_in_wishlist: Optional[bool] = None):
        self.db_manager = db_manager
        self.skin = skin
        self.is_in_wishlist = is_in_wishlist
        super().__init__(timeout=None)
        self.add_item(AddToWishListButton(db_manager=self.db_manager, skin=self.skin, is_in_wishlist=self.is_in_wishlist))

    @discord.ui.button(style=discord.ButtonStyle.green, emoji=discord.PartialEmoji.from_str("<:expand:1080746652815593572>"), custom_id="expand_v2")
    async def image(self, button: discord.ui.Button, interaction: discord.Interaction):
        new_embeds = []
        for embed in interaction.message.embeds:
            if (type(embed.image.url) == str and "nm" in embed.image.url.lower()) or (type(embed.thumbnail.url) == str and "nm" in embed.thumbnail.url.lower()):
                new_embeds.append(embed)
                continue
            if 'expand' in button.emoji.name:
                new_emoji = discord.PartialEmoji.from_str("<:shrink:1080748791390543923>")
                if embed.thumbnail:
                    embed.set_image(url=embed.thumbnail.url)
                    embed.set_thumbnail(url=discord.Embed.Empty)
            elif 'shrink' in button.emoji.name:
                new_emoji = discord.PartialEmoji.from_str("<:expand:1080746652815593572>")
                if embed.image:
                    embed.set_thumbnail(url=embed.image.url)
                    embed.set_image(url=discord.Embed.Empty)
            new_embeds.append(embed)
        button.emoji = new_emoji
        await interaction.response.edit_message(embeds=new_embeds, view=self)

    @discord.ui.button(label="View Variants", style=discord.ButtonStyle.grey, custom_id="view_variants_v1")
    async def view_variants(self, button: discord.ui.Button, interaction: discord.Interaction):
        skin_name = interaction.message.embeds[0].title
        skin = await self.db_manager.get_skin_by_name_or_uuid(skin_name)
        if skin is False:
            return await interaction.response.send_message(skin_not_found(skin_name), ephemeral=True)
        variant_view = ViewVariants(self.db_manager, skin)
        variant_view.format_content_and_embed()
        await interaction.response.send_message(variant_view.content, embed=variant_view.embed, view=variant_view)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.data.get('custom_id', None) == "add_to_wishlist_v1":
            return True
        if interaction.message.interaction is not None:
            if interaction.user.id != interaction.message.interaction.user.id:
                await interaction.response.send_message("These buttons aren't for you!", ephemeral=True)
                return False
        return True


class SuggestionUserReplyView(discord.ui.View):
    def __init__(self):
        self.interaction_message = None
        super().__init__(timeout=None)

    @discord.ui.button(label="Message", style=discord.ButtonStyle.blurple, emoji="📨", custom_id="suggest_user_message")
    async def message_suggestor(self, button: discord.ui.Button, interaction: discord.Interaction):
        suggestion_id = int(interaction.message.embeds[0].title.split("#")[-1])
        suggestion = await interaction.client.db.fetchrow("SELECT * FROM suggestions WHERE suggestion_id = $1", suggestion_id)
        if suggestion is None:
            return await interaction.response.send_message(embed=ErrorEmbed(f"A suggestion with ID `{suggestion_id}` was not found."), ephemeral=True)
        self.interaction_message = interaction.message
        await interaction.response.send_modal(SuggestionUserMessagePrompt(suggestion.get('suggestion_id'), self))


class SuggestionUserMessagePrompt(discord.ui.Modal):
    def __init__(self, suggestion_id: int, view: SuggestionUserReplyView):
        self.suggestion_id = suggestion_id
        self.view = view
        super().__init__(timeout=None, title=f"Reply to Developer")

        self.add_item(
            discord.ui.InputText(label="Response", style=discord.InputTextStyle.long, min_length=1, max_length=512,
                                 required=True, placeholder="You are only allowed to send your response once. Make sure it fits within 512 characters."))

    async def callback(self, interaction: discord.Interaction):
        suggestion = await interaction.client.db.fetchrow("SELECT * FROM suggestions WHERE suggestion_id = $1",
                                                          self.suggestion_id)
        if suggestion is None:
            return await interaction.response.send_message(
                embed=ErrorEmbed(f"A suggestion with ID `{self.suggestion_id} was not found.`"), ephemeral=True)
        try:
            suggested_user = await interaction.client.fetch_user(suggestion.get('user_id'))
        except discord.NotFound:
            return await interaction.response.send_message(embed=ErrorEmbed(
                f"I could not find the user of the suggestion `{self.suggestion_id}`.\n`{suggestion.get('user_id')}"),
                                                           ephemeral=True)
        response = self.children[0].value
        cut_text = suggestion.get('content') if len(suggestion.get('content')) < 100 else suggestion.get('content')[
                                                                                          :100] + "..."
        embed = discord.Embed(title=f"{interaction.user} has responded to your developer message", description=cut_text, color=2829617)
        embed.add_field(name=f"{interaction.user.name}#{interaction.user.discriminator}", value=response)
        try:
            c = await interaction.client.fetch_channel(1081078682153652326)
        except discord.NotFound:
            return await interaction.response.send_message(embed=ErrorEmbed(f"I could not find the place to send your response to.\nDon't worry, this is not your fault."))
        try:
            await c.send(embed=embed, view=SingleURLButton(f"https://discord.com/channels/801457328346890241/1075290139703660594/{suggestion.get('server_message_id')}", f"Suggestion #{self.suggestion_id}"))
        except discord.Forbidden:
            return await interaction.response.send_message(embed=ErrorEmbed(f"I do not have permission to send your response.\nDon't worry, this is not your fault."))
        else:
            await interaction.client.db.execute(
                "INSERT INTO suggestion_responses(suggestion_id, author_id, response, response_time) VALUES($1, $2, $3, $4)",
                self.suggestion_id, interaction.user.id, response, round(time.time()))
            await interaction.response.send_message("Your repsonse was sent successfullly.", embed=embed, ephemeral=True)
            self.view.children[0].disabled = True
            await self.view.interaction_message.edit(view=self.view)


class SuggestionDeveloperMessagePrompt(discord.ui.Modal):
    def __init__(self, suggestion_id: int, suggested_user: discord.User):
        self.suggestion_id = suggestion_id
        self.suggested_user = suggested_user
        super().__init__(timeout=None, title=f"Reply to {suggested_user.name}'s Suggestion")

        self.add_item(discord.ui.InputText(label="Response", style=discord.InputTextStyle.long, min_length=1, max_length=512, required=True))

    async def callback(self, interaction: discord.Interaction):
        suggestion = await interaction.client.db.fetchrow("SELECT * FROM suggestions WHERE suggestion_id = $1", self.suggestion_id)
        if suggestion is None:
            return await interaction.response.send_message(embed=ErrorEmbed(f"A suggestion with ID `{self.suggestion_id} was not found.`"), ephemeral=True)
        try:
            suggested_user = await interaction.client.fetch_user(suggestion.get('user_id'))
        except discord.NotFound:
            return await interaction.response.send_message(embed=ErrorEmbed(f"I could not find the user of the suggestion `{self.suggestion_id}`.\n`{suggestion.get('user_id')}"), ephemeral=True)
        response = self.children[0].value
        cut_text = suggestion.get('content') if len(suggestion.get('content')) < 100 else suggestion.get('content')[:100] + "..."
        embed = discord.Embed(title=f"A developer has responded to your suggestion #{suggestion.get('suggestion_id')}", description=cut_text, color=2829617)
        embed.add_field(name=f"{interaction.user.name}#{interaction.user.discriminator}", value=response)
        try:
            await suggested_user.send(embed=embed, view=SuggestionUserReplyView())
        except discord.Forbidden:
            return await interaction.response.send_message(embed=ErrorEmbed(f"I could not DM {suggested_user.name}#{suggested_user.discriminator}."))
        else:
            await interaction.client.db.execute("INSERT INTO suggestion_responses(suggestion_id, author_id, response, response_time) VALUES($1, $2, $3, $4)", self.suggestion_id, interaction.user.id, response, round(time.time()))
            await interaction.response.send_message("Your repsonse was sent successfullly.", embed=embed, ephemeral=True)


class ReasonDropDown(discord.ui.Select):
    def __init__(self, menu_type: str):
        if menu_type == "accept":
            self.raw_reasons = accept_reasons
        else:
            self.raw_reasons = reject_reasons
        options = [
            discord.SelectOption(label=name, value=name) for name, value in self.raw_reasons.items()
        ]
        super().__init__(placeholder="Select a reason", options=options)

    async def callback(self, interaction: discord.Interaction):
        self.view.raw_result = self.values[0]
        self.view.result = self.raw_reasons.get(self.values[0], "undefined")
        self.disabled = True
        await interaction.response.edit_message(view=self.view)
        self.view.interaction = interaction
        self.view.stop()


class ReasonView(discord.ui.View):
    def __init__(self, menu_type: str):
        self.raw_result = None
        self.result = None
        self.interaction = None
        super().__init__(timeout=30, disable_on_timeout=True)

        self.add_item(ReasonDropDown(menu_type))


class SuggestionDeveloperView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Message", style=discord.ButtonStyle.blurple, emoji="📨", custom_id="suggest_message")
    async def message_suggestor(self, button: discord.ui.Button, interaction: discord.Interaction):
        suggestion = await interaction.client.db.fetchrow("SELECT * FROM suggestions WHERE server_message_id = $1", interaction.message.id)
        if suggestion is None:
            return await interaction.response.send_message(embed=ErrorEmbed(f"A suggestion with ID `{suggestion.get('suggestion_id')}` was not found."), ephemeral=True)
        try:
            suggested_user = await interaction.client.fetch_user(suggestion.get('user_id'))
        except discord.NotFound:
            return await interaction.response.send_message(embed=ErrorEmbed(f"I could not find the user of the suggestion `{suggestion.get('suggestion_id')}`.\n`{suggestion.get('user_id')}`"), ephemeral=True)
        await interaction.response.send_modal(SuggestionDeveloperMessagePrompt(suggestion.get('suggestion_id'), suggested_user))

    @discord.ui.button(label="View Conversation", style=discord.ButtonStyle.blurple, emoji="📃", custom_id="suggest_view_convo_history")
    async def view_suggest_conversation(self, button: discord.ui.Button, interaction: discord.Interaction):
        suggestion = await interaction.client.db.fetchrow("SELECT * FROM suggestions WHERE server_message_id = $1", interaction.message.id)
        if suggestion is None:
            return await interaction.response.send_message(embed=ErrorEmbed(f"A suggestion for this message was not found."), ephemeral=True)
        suggestion_responses = await interaction.client.db.fetch("SELECT * FROM suggestion_responses WHERE suggestion_id = $1", suggestion.get('suggestion_id'))
        responses = []
        for response in suggestion_responses:
            try:
                author = await interaction.client.get_or_fetch_user(response.get('author_id'))
            except discord.NotFound:
                author = f"Unknown User - {response.get('author_id')}"
            else:
                author = f"{author.name}#{author.discriminator}"
            responses.append((f"**{author}** - <t:{response.get('response_time')}>", response.get('response')))
        embed_title = f"Suggestion #{suggestion.get('suggestion_id')}"
        embed_description = suggestion.get('response')
        pagina = pages.Paginator(
            pages=bundle_responses_into_embeds(responses, discord.Embed(title=embed_title, description=embed_description)),
            show_menu=False,
            author_check=True,
            disable_on_timeout=True,
        )
        await pagina.respond(interaction, ephemeral=True)




    @discord.ui.button(label="Accept", style=discord.ButtonStyle.green, emoji="<:CL_True:1075296198598066238>", custom_id="suggest_approve", row=2)
    async def accept_suggestion(self, button: discord.ui.Button, interaction: discord.Interaction):
        view = ReasonView("accept")
        await interaction.response.send_message(view=view, ephemeral=True)
        await view.wait()
        if view.result is None:
            return
        message = view.result
        suggestion = await interaction.client.db.fetchrow("SELECT * FROM suggestions WHERE server_message_id = $1", interaction.message.id)
        await interaction.client.db.execute("UPDATE suggestions SET approved = $1, closed = $2 WHERE suggestion_id = $3", True, True, suggestion.get('suggestion_id'))
        send_status = "User was not notified"
        embed = discord.Embed(title="Suggestion approved", description=message, color=discord.Color.green())
        embed.set_author(name="Cypher's Laptop",
                         icon_url="https://cdn.discordapp.com/avatars/844489130822074390/ab663738f44bf18062f0a5f77cf4ebdd.png?size=32")
        embed.add_field(name=f"Your suggestion #{suggestion.get('suggestion_id')}", value=suggestion.get('content'))
        try:
            user = await interaction.client.get_or_fetch_user(suggestion.get('user_id'))
        except discord.NotFound:
            send_status = f"User with ID {suggestion.get('user_id')} was not found."
        else:
            try:

                await user.send(embed=embed)
            except discord.Forbidden:
                send_status = f"**{user}**'s DMs are closed."
            else:
                send_status = f"**{user}** was successfully notified of their suggestion status."
        await interaction.followup.send(send_status, embed=embed, ephemeral=True)
        for item in self.children:
            if isinstance(item, discord.ui.Button) and item.label == "Deny":
                self.remove_item(item)
            else:
                print(type(item), item)
        button.emoji = discord.PartialEmoji.from_str("<:CL_True:1075296198598066238>") if button.label == "Accept" else discord.PartialEmoji.from_str("<:CL_False:1075296226620223499>")
        button.label = f"Accepted by {interaction.user} for: {view.raw_result}" if button.label == "Accept" else f"Denied by {interaction.user} for: {view.raw_result}"
        button.disabled = True
        interaction.message.embeds[0].color = discord.Color.green()
        await interaction.message.edit(view=self, embeds=interaction.message.embeds)



    @discord.ui.button(label="Deny", style=discord.ButtonStyle.red, emoji="<:CL_False:1075296226620223499>", custom_id="suggest_deny", row=2)
    async def deny_suggestion(self, button: discord.ui.Button, interaction: discord.Interaction):
        view = ReasonView("reject")
        await interaction.response.send_message(view=view, ephemeral=True)
        await view.wait()
        if view.result is None:
            return
        message = view.result
        suggestion = await interaction.client.db.fetchrow("SELECT * FROM suggestions WHERE server_message_id = $1",
                                                          interaction.message.id)
        await interaction.client.db.execute(
            "UPDATE suggestions SET approved = $1, closed = $2 WHERE suggestion_id = $3", False, True,
            suggestion.get('suggestion_id'))
        send_status = "User was not notified"
        embed = discord.Embed(title="Suggestion denied", description=message, color=discord.Color.red())
        embed.set_author(name="Cypher's Laptop",
                         icon_url="https://cdn.discordapp.com/avatars/844489130822074390/ab663738f44bf18062f0a5f77cf4ebdd.png?size=32")
        embed.add_field(name=f"Your suggestion #{suggestion.get('suggestion_id')}",
                        value=suggestion.get('content'))
        try:
            user = await interaction.client.get_or_fetch_user(suggestion.get('user_id'))
        except discord.NotFound:
            send_status = f"User with ID {suggestion.get('user_id')} was not found."
        else:
            try:

                await user.send(embed=embed)
            except discord.Forbidden:
                send_status = f"{user}'s DMs are closed."
            else:
                send_status = f"{user} was successfully notified of their suggestion status."
        await interaction.followup.send(send_status, embed=embed, ephemeral=True)
        for item in self.children:
            if isinstance(item, discord.ui.Button) and item.label == "Accept":
                self.remove_item(item)
            else:
                print(type(item), item)
        button.emoji = discord.PartialEmoji.from_str("<:CL_True:1075296198598066238>") if button.label == "Accept" else discord.PartialEmoji.from_str("<:CL_False:1075296226620223499>")
        button.label = f"Accepted by {interaction.user} for: {view.raw_result}" if button.label == "Accept" else f"Denied by {interaction.user} for: {view.raw_result}"
        button.disabled = True
        interaction.message.embeds[0].color = discord.Color.red()
        await interaction.message.edit(view=self)


class FAQMenu(discord.ui.Select):
    def __init__(self):

        with open('assets/faq.json', 'r') as f:
            self.faq = json.load(f)
        options = []
        for i in self.faq:
            cut_description = i.get('a')[:50] + "..." if len(i.get('a')) > 50 else i.get('a')
            op = discord.SelectOption(label=i.get('q'), value=i.get('q'), description=cut_description)
            options.append(op)
        super().__init__(custom_id="faq_menuv1", placeholder="Select a FAQ", options=options)

    async def callback(self, interaction: discord.Interaction):
        a = "Undefined"
        for i in self.faq:
            if i.get('q') == self.values[0]:
                a = i.get('a')
        embed = discord.Embed(title=self.values[0], description=a)
        embed.set_author(name="Cypher's Laptop", icon_url="https://cdn.discordapp.com/avatars/844489130822074390/ab663738f44bf18062f0a5f77cf4ebdd.png?size=32")
        for i in self.options:
            if i.value == self.values[0]:
                i.default = True
            else:
                i.default = False
        await interaction.response.edit_message(embed=embed, view=self.view)


class FAQView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(FAQMenu())