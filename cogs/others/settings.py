import copy
import json
from typing import Optional

import discord
from discord.ext import commands

from cogs.maincommands.database import DBManager
from utils.helper import range_char_from_letter
from utils.specialobjects import UserSetting
from utils.helper import range_char

currency_embed = discord.Embed(
    title="Display Skin Price",
    description="Show the price of a skin in your preferred currency.",
    color=2829617
).set_image(url="https://cdn.discordapp.com/attachments/1046947484150284390/1055010191717978112/CLcurrency.png")
show_username_embed = discord.Embed(
    title="Display your Riot username",
    description="Show your Riot username so you know which account you're looking at, or hide it to stay private.",
    color=2829617
).set_image(url="https://cdn.discordapp.com/attachments/1046947484150284390/1055010192154165248/CLusername.png")


class SelectCurrency(discord.ui.Select):
    def __init__(self, user_setting: UserSetting):
        self.user_setting = user_setting
        self.secondary_menu = False
        self.currency_range = []
        self.all_currency_options = []

        with open('assets/currencies.json') as f:
            currencies = json.load(f)
        for currency in currencies['data']:
            currency_data = currencies['data'][currency]
            vp_per_dollar = currency_data['vp_per_dollar']
            name = currency_data['name']
            symbol = currency_data['symbol']
            emoji = currency_data['emoji']
            if vp_per_dollar == 0:
                desc = "calculated via USD"
            else:
                desc = None
            self.all_currency_options.append(discord.SelectOption(label=f"{name} ({symbol})", value=currency, description=desc or "", default=currency == user_setting.currency, emoji=emoji))

        if user_setting.currency is None:
            ph = "Select a letter range"
        else:
            self.secondary_menu = True
            self.currency_range = range_char_from_letter(user_setting.currency[0].lower())
            ph = "Select a currency"
        options = self.update_options(user_setting.currency, True)

        super().__init__(placeholder=ph, options=options, min_values=1, max_values=1)

    def update_options(self, selected_currency: Optional[str] = None, first_time=False):
        options = []
        if self.secondary_menu:
            ph = f"Select a currency starting from {self.currency_range[0].upper()} to {self.currency_range[-1].upper()}"
            options.append(discord.SelectOption(label="Back to letter ranges", value="back", emoji="<:back:1054664049020915742>"))
            options.append(discord.SelectOption(label="No currency", value="none"))
            for op in self.all_currency_options:
                a = op.label.lower()[0]
                if a in self.currency_range:
                    options.append(op)
                    if options[-1].value == selected_currency:
                        options[-1].default = True
                    else:
                        options[-1].default = False
        else:
            options = [
                discord.SelectOption(label="No currency", value="none"),
                discord.SelectOption(label="A-E", value="a-e"),
                discord.SelectOption(label="F-J", value="f-j"),
                discord.SelectOption(label="K-O", value="k-o"),
                discord.SelectOption(label="P-T", value="p-t"),
                discord.SelectOption(label="U-Z", value="u-z")
            ]
            ph = "Select a letter range"
        if not first_time:
            self.options = options
            self.placeholder = ph
        else:
            return options

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "back":
            self.secondary_menu = False
            self.currency_range = []
        elif self.values[0] == "none":
            setattr(self.view.user_setting, self.view.current_selected, None)
            await self.view.user_setting.update(interaction.client)
            self.secondary_menu = False
            self.currency_range = []
        elif "-" in self.values[0]:
            self.secondary_menu = True
            first_letter, last_letter = self.values[0].split("-")
            self.currency_range = range_char(first_letter, last_letter)
        else:
            setattr(self.view.user_setting, self.view.current_selected, self.values[0])
            await self.view.user_setting.update(interaction.client)
        self.update_options(self.values[0])
        await interaction.response.edit_message(view=self.view)
        if self.values[0] == "none":
            await interaction.followup.send("I will not show the price of your skins.", ephemeral=True)


class EnableDisable(discord.ui.Button):
    def __init__(self, user_setting: UserSetting):
        super().__init__(
            label="Enabled" if user_setting.show_username else "Disabled",
            style=discord.ButtonStyle.green if user_setting.show_username else user_setting.show_username
        )
        self.user_setting = user_setting

    async def callback(self, interaction: discord.Interaction):
        is_enabled = getattr(self.view.user_setting, self.view.current_selected)
        if is_enabled:
            setattr(self.view.user_setting, self.view.current_selected, False)
            self.update_button()
        else:
            setattr(self.view.user_setting, self.view.current_selected, True)
            await self.view.user_setting.update(interaction.client)
            self.update_button()
        await self.view.user_setting.update(interaction.client)
        self.view.update_embed()
        await interaction.response.edit_message(view=self.view, embed=self.view.embed)

    def update_button(self):
        is_enabled = getattr(self.view.user_setting, self.view.current_selected)
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
            discord.SelectOption(label="Show skin price", value="currency", description="Display the approximate price of a weapon skin.", default=True),
            discord.SelectOption(label="Show username", value="show_username", description="Show or hide your Riot username on your Store.", default=False)
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
        self.view.remove_item(self.view.button)
        self.view.remove_item(self.view.currency_select)
        self.view.current_selected = selected
        if self.view.current_selected == "currency":
            self.view.add_item(self.view.currency_select)
        else:
            self.view.add_item(self.view.button)
            self.view.button.update_button()
        self.view.update_embed()
        await interaction.response.edit_message(embed=self.view.embed, view=self.view)


class UserSettingsView(discord.ui.View):
    def __init__(self, user_setting: UserSetting):
        self.embed = currency_embed
        self.current_selected = "currency"
        self.user_setting = user_setting
        self.button = EnableDisable(self.user_setting)
        self.currency_select = SelectCurrency(self.user_setting)
        super().__init__(timeout=None)

        self.add_item(SelectSetting())
        self.add_item(self.currency_select)

    def update_embed(self):
        if self.current_selected == "currency":
            self.embed = currency_embed
        elif self.current_selected == "show_username":
            self.embed = show_username_embed
        self.embed.color = discord.Color.green() if getattr(self.user_setting, self.current_selected) else discord.Color.red()


class Settings(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.dbManager: DBManager = DBManager(self.client.db)

    @commands.slash_command(name="settings", description="Customize your User Settings in Cypher's Laptop.")
    async def settings_cmd(self, ctx):
        user_settings = await self.dbManager.fetch_user_settings(ctx.author.id)
        view = UserSettingsView(user_settings)
        view.update_embed()
        await ctx.respond(embed=view.embed, view=view)
        await view.wait()
