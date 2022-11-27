import discord
from discord.ext import commands

from cogs.maincommands.database import DBManager
from main import clvt
from utils.specialobjects import ReminderConfig


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
        await interaction.response.edit_message(view=self.view)

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
            discord.SelectOption(label="Enable/Disable", value="enabled", description="Turn on or off your daily Store reminder.", default=True),
            discord.SelectOption(label="Show store immediately", value="show_immediately", description="If disabled, you'll press a button to view the store instead of seeing it immediately."),
            discord.SelectOption(label="Show as a picture", value="picture_mode", description="If enabled, your skins will be shown together in a picture.")
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


enable_disable_embed = discord.Embed(title="Enable/Disable reminders", description="Enable/disable reminders for checking your VALORANT Store after it resets.", color=3092790)
show_immediately_embed = discord.Embed(title="Show store immediately", description="When your Store reminder is sent, view your store immediately or ", color=3092790)
picture_mode_embed = discord.Embed(title="Show as a picture", description="Show your skins as a picture or as a list.", color=3092790)


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
        elif self.reminder_config == "picture_mode":
            self.embed = picture_mode_embed



class StoreReminder(commands.Cog):
    def __init__(self, client):
        self.client: clvt = client
        self.dbManager: DBManager = DBManager(self.client.db)

    @commands.slash_command(name="reminders", description="Configure your VALORANT Store reminders")
    async def reminder_cmd(self, ctx):
        user_settings = await self.dbManager.fetch_user_reminder_settings(ctx.author.id)
        view = ReminderSettingsView(user_settings)
        await ctx.respond(embed=enable_disable_embed, view=view)
        await view.wait()


