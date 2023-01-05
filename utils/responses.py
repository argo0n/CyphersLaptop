import json
from typing import Literal, Optional

import discord

from utils.format import comma_number
from utils.specialobjects import GunSkin


def updating_password(username, step: Literal[1, 2]):
    if step == 1:
        desc = "Verifying your credentials with Riot..."
        color = discord.Color.dark_orange()
    elif step == 2:
        desc = "Encrypting and updating your password..."
        color = discord.Color.orange()
    return discord.Embed(title=f"Updating password for {username}", description=desc, color=color)


# ------- Argument Error Responses -------

def invalid_channel():
    return discord.Embed(title="Invalid Channel", description="To ensure privacy, please use this command in direct messages only.", color=discord.Color.red())


# ------- Database Responses -------

def user_already_exist(username, is_author: bool):
    if is_author:
        description = f"You've already logged into to **{username}** on Cypher's Laptop."
    else:
        description = f"**{username}** is already logged into via another Discord account.\nIf you want to use your Riot account on this Discord account, </logout:1045213188209258519> of **{username}** on your other Discord account."
    return discord.Embed(title="User Already Exists", description=description, color=discord.Color.red())


def already_logged_in(username):
    return discord.Embed(title="Already Logged In", description=f"You are already logged in with the Riot account **{username}**.\nYou can only add one account at a time.", color=discord.Color.red())


def user_logged_in(username):
    embed = discord.Embed(title="Successfully logged in", description=f"Your Riot account, **{username}** has been successfully verified and logged in.\n\nIf you received a login MFA code, you may ignore it.", color=discord.Color.green()).set_footer(text="Your password is encrypted when stored. Not even the developer can see your password.")
    embed.add_field(name="What next?", value="• Use </store:1045171702612639836> to check your store at any time.\n• Never miss out on your store by enabling and customizing your </reminders:1046432239724015697>.\n• Check out </settings:1055460993225990174> to customize your Store, such as displaying weapon skin estimate prices!\n\nI will inform you if your <:wlGUN:1046281227142975538> **favorite skin** is in the shop! Just add your favorite skins to your </wishlist add:1046095784292130946>.")
    return embed


def user_logged_out(username):
    return discord.Embed(title="Successfully logged out", description=f"Your Riot account, **{username}** has been successfully logged out.", color=discord.Color.green())


def user_updated(username):
    return discord.Embed(title="User Credentials Updated", description=f"Your Riot account, **{username}**'s password has been successfully verified and updated.", color=discord.Color.green())


def no_logged_in_account():
    return discord.Embed(title="No Logged In Account", description="You do not have a Riot account logged in with Cypher's Laptop.\nUse </login:1045213188209258518> <username> <password> <region> to log in to your Riot account.", color=discord.Color.red())

def updated_password(username):
    return discord.Embed(title="Password Updated", description=f"The password for your Riot account **{username}** has been successfully updated.", color=discord.Color.green())

def updated_weapon_database():
    return discord.Embed(title="Weapon Skin Database Updated", description="The weapon database has been updated successfully.", color=discord.Color.green())

def skin_added_to_wishlist(skin_name):
    return discord.Embed(title="Added to Wishlist", description=f"<:DVB_True:887589686808309791> **{skin_name}** has been added to your wishlist.", color=discord.Color.green())

def skin_already_on_wishlist(skin_name):
    return discord.Embed(title="Already on Wishlist", description=f"<:DVB_False:887589731515392000> **{skin_name}** is already on your wishlist.", color=discord.Color.red())

def skin_removed_from_wishlist(skin_name):
    return discord.Embed(title="Removed from Wishlist", description=f"<:DVB_True:887589686808309791> **{skin_name}** has been removed from your wishlist.", color=discord.Color.green())

def skin_not_on_wishlist(skin_name):
    return discord.Embed(title="Skin Not on Wishlist", description=f"**{skin_name}** is not on your wishlist.", color=discord.Color.red())

def store_here(skin_in_wishlist):
    date_asstr = discord.utils.utcnow().strftime("%A, %d %B %y")
    if skin_in_wishlist:
        return (
            discord.Embed(title="Your VALORANT Store has reset! You have WISHLISTED SKINS in your store", description="Tap here to check it!", color=3092790),
            discord.Embed(title="Your <:val:1046289333344288808> VALORANT Store has reset", description="<:wlGUN:1046281227142975538> You have **WISHLISTED SKINS** in your store!", color=3092790).set_footer(text=date_asstr)
        )
    else:
        return (
            discord.Embed(title="Your VALORANT Store has reset", description="Tap here to check it!", color=3092790),
            discord.Embed(title="Your <:val:1046289333344288808> VALORANT Store has reset", description="Check out your newly refreshed <:val:1046289333344288808> Store.", color=3092790).set_footer(text=date_asstr)
        )

def no_cached_store():
    return discord.Embed(title="Daily Store Error", description="I was unable to fetch your daily VALORANT Store from our database. You can still try running </store:1045171702612639836> to check your Store.", color=discord.Color.red())


# ------- Riot Authentication Errors/Responses -------

def authenticating(with_mfa_code: bool = False):
    if with_mfa_code:
        return discord.Embed(title="Authenticating...", description="Authenticating your Riot account with your MFA code...", color=discord.Color.orange())
    else:
        return discord.Embed(title="Authenticating...", description="Authenticating your Riot account...", color=discord.Color.orange())

def authentication_success():
    return discord.Embed(title="Success", description="Your Riot account has been successfully authenticated.", color=discord.Color.green())

def authentication_error(is_update_or_login_command: bool = False):
    if is_update_or_login_command:
        remark = ""
    else:
        remark = "\n\nIf you have updated your password, please use </update-password:1045212370944929802> <password>."
    return discord.Embed(title="Authentication Error", description=f"Make sure your **username** and **password** are correct and try again.\n\nEnsure you are using the username and password for signing in to your **Riot Account**, not your VALORANT display name or Riot ID.{remark}", color=discord.Color.red()).set_image(url="https://cdn.discordapp.com/attachments/871737314831908974/1045221258670903348/brave_YlSOdWyDbs.png")


def rate_limit_error():
    return discord.Embed(title="Rate Limited", description="Your request has been rate limited by Riot.\nYou might have tried to log in too many times, please try again in a few minutes.", color=discord.Color.red())


def multifactor_detected():
    return discord.Embed(title="Enter Multi Factor Authentication (MFA) Code", description="Your account has MFA enabled.\nA code has been sent to your email, check your email for the code and enter it below.\n\nNote that you will need enter a new multifactor code every time you check your store.", color=discord.Color.red()).set_image(url="https://cdn.discordapp.com/attachments/871737314831908974/1045223829452095558/image.png")


def multifactor_error():
    return discord.Embed(title="Multifactor Failed", description="The MFA code you entered was incorrect.\nPlease rerun the command to re-enter the code or request for a new one.\n\nNote that you will need enter a new multifactor code every time you check your store.", color=discord.Color.red())


def skin_not_found(skin_name):
    return discord.Embed(title="Skin Not Found", description=f"I could not find a skin with the name **{skin_name}**.", color=discord.Color.red())


def not_ready():
    return discord.Embed(title="Not Ready", description="Cypher's Laptop is still booting up. Try again in a few seconds!", color=discord.Color.red())


def skin_embed(
        skin: GunSkin, is_in_wishlist: bool, currency: Optional[dict] = None,
        nm_p: Optional[int] = None, nm_c: Optional[int] = None, nm_s: Optional[bool] = True
    ):
    tier_uuids = [
        {
            "uuid": "12683d76-48d7-84a3-4e09-6985794f0445",
            "name": "Select",
            "color": 0x5CA3E3,
            "emoji": "<:SE:1045730725200154754>"
        },
        {
            "uuid": "0cebb8be-46d7-c12a-d306-e9907bfc5a25",
            "name": "Deluxe",
            "color": 0x14C8AB,
            "emoji": "<:DE:1045730727259537459>"
        },
        {
            "uuid": "60bca009-4182-7998-dee7-b8a2558dc369",
            "name": "Premium",
            "color": 0xCF4F88,
            "emoji": "<:PE:1045730729671266395>"
        },
        {
            "uuid": "e046854e-406c-37f4-6607-19a9ba8426fc",
            "name": "Exclusive",
            "color": 0xFF9054,
            "emoji": "<:XE:1045730735241302016>"
        },
        {
            "uuid": "411e4a55-4e59-7757-41f0-86a53f101bb5",
            "name": "Ultra",
            "color": 0xF9D368,
            "emoji": "<:UE:1045730732691161188>"
        }
    ]
    tier = next((x for x in tier_uuids if x["uuid"] == skin.contentTierUUID), None)
    if nm_p is not None:
        cost = f"<:vp:1045605973005434940> ~~{comma_number(skin.cost)}~~ `-{nm_p}%` "
        skin.cost = nm_c
    else:
        cost = "<:vp:1045605973005434940> "
    cost += f"**{comma_number(skin.cost)}**" if skin.cost is not None else "<:DVB_False:887589731515392000> Not on sale"
    if currency is not None:
        vp_per_dollar = currency["vp_per_dollar"]
        if vp_per_dollar == 0:
            with open("assets/currencies.json") as f:
                currencies = json.load(f)
            exch = currency["exch"]
            vp_per_dollar = currencies["data"]["USD"]["vp_per_dollar"] * exch
        if currency['decimal_digits'] == 0:
            cost_rounded = int(skin.cost * vp_per_dollar)
            cost_fr = comma_number(cost_rounded)
        else:
            cost_rounded = round(skin.cost * vp_per_dollar, currency['decimal_digits'])
            #comma_number doesn't work with decimals, so we need to split the whole number and decimal and run comma_number on whole number before joining it with decimal
            cost_fr = comma_number(int(cost_rounded)) + "." + str(cost_rounded).split(".")[1]


        cost += f" *≈ {currency['symbol']} {cost_fr}*"
    if nm_s is True:
        embed = discord.Embed(title=skin.displayName, description=f"{cost}")
        embed.set_thumbnail(url=skin.displayIcon)
    else:
        embed = discord.Embed().set_image(url="https://cdn.discordapp.com/attachments/805604591630286918/1045968296488480818/CyphersLaptopWideEdited.png")
    if tier is not None:
        embed.color = tier["color"]
        if nm_s is True:
            embed.description += f"\n{tier['emoji']} {tier['name']}"
    if is_in_wishlist:
        embed.set_footer(text="This skin is in your wishlist!", icon_url="https://cdn.discordapp.com/emojis/1046281227142975538.webp?size=96&quality=lossless")
        embed.color = 0xDD2F45
    return embed

def night_market_closed():
    return discord.Embed(title="The VALORANT Night Market is not open!", description="Follow [@PlayVALORANT on Twitter](https://twitter.com/PlayVALORANT) for updates on future Night Markets!", color=3092790).set_footer(text="Based on previous Night Market appearances, the next Night Market might open in appr. February 2023.").set_image(url="https://cdn.discordapp.com/attachments/868454485683470397/1060407886393647155/nightmarket_e.png")


# ------- Discord Bot Setup Error Responses -------

def permission_error():
    return discord.Embed(title="Permission Error (403 Forbidden)", description="Permissions in this server channel do not allow messages to be sent.\nA server admin will need to allow message sending for Cypher's Laptop in channel permission settings.", color=discord.Color.dark_red())

def reminder_disabled(reason: Literal["no_account", "mfa_enabled", "authorization_failed", "rate_limit"]) -> list[discord.Embed]:
    responses = {
        "no_account": "You do not have a Riot account logged in to Cypher's Laptop.",
        "mfa_enabled": "**You have Multi-factor Authentication (MFA) enabled for your Riot account.**\nFor your convenience, I am unable to provide you your daily Store if MFA is enabled.\nYou can continue using the </store:1045171702612639836> command to check your daily Store.",
        "authorization_failed": "Cypher's Laptop was unable to login to your Riot account.\nIf you recently changed your Riot account's password, update it in Cypher's Laptop with </update-password:1045212370944929802>."
    }
    embeds = []
    if reason == "authorization_failed":
        embeds.append(authentication_error())
    reason = responses.get(reason, "A reason was not specified.")
    embeds.append(discord.Embed(title="Your Daily VALORANT Store Reminder has been disabled", description=reason, color=discord.Color.red()))
    return embeds


# ------- Unknown Error (Unhandled exception) -------

def unknown_error():
    return discord.Embed(title="An Error Occurred", description="An unknown error occurred. This issue has been raised and will be fixed as soon as possible.\nIf this issue persists, please submit a request in the [Valemporium support server](https://discord.gg/ejvddZr4Dw)", color=discord.Color.dark_red())


# ------- Informational Responses -------

def help_command(is_dev):
    embed = discord.Embed(title="Cypher's Laptop - Help", description="All available commands and important command arguments", color=discord.Color.blue())
    embed.add_field(name="</store:1045171702612639836>", value="Retrieves your VALORANT store.", inline=True)
    embed.add_field(name="</reminders:1046432239724015697>", value="Configure your Store reminders!", inline=True)
    embed.add_field(name="</invite:1045732151506767974>", value="Invite Cypher's Laptop to your server!", inline=True)
    embed.add_field(name="</balance:1045213188209258517>", value="View your <:vp:1045605973005434940> Balance.", inline=True)
    embed.add_field(name="</wishlist show:1046095784292130946>", value="View your skin wishlist.", inline=True)
    embed.add_field(name="</wishlist add:1046095784292130946> <skin name>", value="uAdd a skin to your wishlist.", inline=True)
    embed.add_field(name="</wishlist remove:1046095784292130946>", value="Remove a skin from your wishlist.", inline=True)
    embed.add_field(name="</skin:1045732151506767973>", value="Search for a VALORANT gun skin.", inline=True)
    embed.add_field(name="</login:1045213188209258518>", value="Log in to Cypher's Laptop with your Riot account. \nYour password is encrypted and stored securely when you log in.", inline=False)
    embed.add_field(name="</logout:1045213188209258519>", value="Log out of Cypher's Laptop.\nYour credentials are immediately deleted from the database once you log out.", inline=True)
    embed.add_field(name="</update-password:1045212370944929802>", value="Update your Riot account password in Cypher's Laptop if you have changed it.", inline=True)
    embed.add_field(name="</settings:1055460993225990174>", value="Tweak your settings to customize your Cypher's Laptop experience.", inline=True)
    if is_dev:
        embed.add_field(name="DEVELOPER", value="\u200b", inline=False)
        embed.add_field(name="</update-skins-database:1045634432268255303>", value="Manually update the internal VALORANT gun skins database.", inline=True)
        embed.add_field(name="</get-raw-credentials:1045622620500000821>", value="Get raw credentials of your Riot account to communicate with the VALORANT API for testing.", inline=True)
    embed.set_thumbnail(url="https://cdn.discordapp.com/avatars/844489130822074390/bfe9b52d135dce826739ba0adbe31cfd.png?size=1024")
    return embed


