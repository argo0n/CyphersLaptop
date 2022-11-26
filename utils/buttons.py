import time
import inspect
import asyncio
import discord
import contextlib
from discord import ui
from typing import Optional, Any, Union, Dict, Type, Iterable
from functools import partial
from utils.context import CLVTcontext
from discord.ext import commands
from utils.context import CLVTcontext
from utils.helper import BaseEmbed

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
        if isinstance(self.response, discord.Message):
            await interaction.response.edit_message(view=self)
        elif isinstance(self.response, discord.Interaction):
            await interaction.response.edit_message(view=self)
        self.stop()

    @discord.ui.button(label="No", style=discord.ButtonStyle.red)
    async def no(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.returning_value = False
        for b in self.children:
            if b != button:
                b.style = discord.ButtonStyle.grey
            b.disabled = True
        if isinstance(self.response, discord.Message):
            await interaction.response.edit_message(view=self)
        elif isinstance(self.response, discord.Interaction):
            await self.response.edit_original_message(view=self)
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
            await self.response.edit_original_message(view=self)



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


class ThumbnailToImage(discord.ui.View):
    def __init__(self, ctx: discord.ApplicationContext):
        self.ctx = ctx
        super().__init__(timeout=None)

    @discord.ui.button(label="Expand images", style=discord.ButtonStyle.green, emoji=discord.PartialEmoji.from_str("<:expand:1046006467091759125>"))
    async def image(self, button: discord.ui.Button, interaction: discord.Interaction):
        new_embeds = []
        for embed in interaction.message.embeds:
            if button.label == "Expand images":
                new_label = "Collapse images"
                new_emoji = discord.PartialEmoji.from_str("<:shrink:1046006464713609237>")
                if embed.thumbnail:
                    embed.set_image(url=embed.thumbnail.url)
                    embed.set_thumbnail(url=discord.Embed.Empty)
            elif button.label == "Collapse images":
                new_label = "Expand images"
                new_emoji = discord.PartialEmoji.from_str("<:expand:1046006467091759125>")
                if embed.image:
                    embed.set_thumbnail(url=embed.image.url)
                    embed.set_image(url=discord.Embed.Empty)
            new_embeds.append(embed)
        button.label = new_label
        button.emoji = new_emoji
        await interaction.response.edit_message(embeds=new_embeds, view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        ctx = self.ctx
        author = ctx.author
        if interaction.user != author:
            await interaction.response.send_message("These buttons aren't for you!", ephemeral=True)
            return False
        return True
