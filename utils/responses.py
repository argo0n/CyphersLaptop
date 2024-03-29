import json
from typing import Literal, Optional

import aiohttp
import discord

from utils.format import comma_number
from utils.helper import get_tier_data
from utils.specialobjects import GunSkin, Accessory, Buddy, PlayerTitle, PlayerCard, Spray


class ErrorEmbed(discord.Embed):
    def __init__(self, description: str, title: str = "Error", color: discord.Color = discord.Color.red(), *args, **kwargs):
        super().__init__(title=title, description=description, color=color, *args, **kwargs)

class SuccessEmbed(discord.Embed):
    def __init__(self, description: str, title: str = "Success", color: discord.Color = discord.Color.green(), *args, **kwargs):
        super().__init__(title=title, description=description, color=color, *args, **kwargs)


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
    return ErrorEmbed(title="Invalid Channel", description="To ensure privacy, please use this command in direct messages only.")


# ------- Database Responses -------

def user_already_exist(username, is_author: bool):
    if is_author:
        description = f"You've already logged into to **{username}** on Cypher's Laptop."
    else:
        description = f"**{username}** is already logged into via another Discord account.\nIf you want to use your Riot account on this Discord account, </logout:1045213188209258519> of **{username}** on your other Discord account."
    return ErrorEmbed(title="User Already Exists", description=description)


def already_logged_in(username):
    return ErrorEmbed(title="Already Logged In", description=f"You are already logged in with the Riot account **{username}**.\nYou can only add one account at a time.")


def user_logged_in(username):
    embed = SuccessEmbed(
        title="Successfully logged in", description=f"Your Riot account, **{username}** has been successfully verified and logged in.\n\nIf you received a login MFA code, you may ignore it."
    ).set_footer(text="Your password is encrypted when stored. Even the developer cannot see your password.")
    embed.add_field(name="What next?", value="• Use </store:1045171702612639836> to check your store at any time.\n• Never miss out on your store by enabling and customizing your </reminders:1046432239724015697>.\n• Check out </settings:1055460993225990174> to customize your Store, such as displaying weapon skin estimate prices!\n\nI will inform you if your <:wlGUN:1046281227142975538> **favorite skin** is in the shop! Just add your favorite skins to your </wishlist add:1046095784292130946>.")
    return embed


def user_logged_out(username):
    return SuccessEmbed(title="Successfully logged out", description=f"Your Riot account, **{username}** has been successfully logged out.")


def user_updated(username):
    return SuccessEmbed(title="User Credentials Updated", description=f"Your Riot account, **{username}**'s password has been successfully verified and updated.")


def no_logged_in_account():
    return ErrorEmbed(title="No Logged In Account", description="You do not have a Riot account logged in with Cypher's Laptop.\nUse </login:1045213188209258518> to log in to your Riot account.")


def updated_password(username):
    return SuccessEmbed(title="Password Updated", description=f"The password for your Riot account **{username}** has been successfully updated.")


def updated_weapon_database():
    return SuccessEmbed(description="The weapon database has been updated successfully.")


def skin_added_to_wishlist(skin_name):
    return SuccessEmbed(title="Added to Wishlist", description=f"<:DVB_True:887589686808309791> **{skin_name}** has been added to your wishlist.")


def skin_already_on_wishlist(skin_name):
    return ErrorEmbed(title="Already on Wishlist", description=f"<:DVB_False:887589731515392000> **{skin_name}** is already on your wishlist.")


def skin_removed_from_wishlist(skin_name):
    return SuccessEmbed(title="Removed from Wishlist", description=f"<:DVB_True:887589686808309791> **{skin_name}** has been removed from your wishlist.")


def skin_not_on_wishlist(skin_name):
    return ErrorEmbed(title="Skin Not on Wishlist", description=f"**{skin_name}** is not on your wishlist.")


def message_delete_success():
    return SuccessEmbed(title="Success", description="Message deleted.")


def store_here(skin_in_wishlist):
    date_asstr = discord.utils.utcnow().strftime("%A, %d %B %y")
    if skin_in_wishlist:
        return (
            discord.Embed(title="Your VALORANT Store has reset! You have WISHLISTED SKINS in your store", description="Tap here to check it!", color=2829617),
            discord.Embed(title="Your <:val:1046289333344288808> VALORANT Store has reset", description="<:wlGUN:1046281227142975538> You have **WISHLISTED SKINS** in your store!", color=2829617).set_footer(text=date_asstr)
        )
    else:
        return (
            discord.Embed(title="Your VALORANT Store has reset", description="Tap here to check it!", color=2829617),
            discord.Embed(title="Your <:val:1046289333344288808> VALORANT Store has reset", description="Check out your newly refreshed <:val:1046289333344288808> Store.", color=2829617).set_footer(text=date_asstr)
        )


def no_cached_store():
    return ErrorEmbed(title="No Store found for this day", description="There was no Store fetched by Cypher's Laptop on this day; as such I am unable to show it to you.")


# ------- Riot Authentication Errors/Responses -------

def authenticating(with_mfa_code: bool = False):
    if with_mfa_code:
        return discord.Embed(title="Authenticating...", description="Authenticating your Riot account with your MFA code...", color=discord.Color.orange())
    else:
        return discord.Embed(title="Authenticating...", description="Authenticating your Riot account...", color=discord.Color.orange())


def authentication_success():
    return SuccessEmbed(description="Your Riot account has been successfully authenticated.")


def authentication_error(is_update_or_login_command: bool = False):
    if is_update_or_login_command:
        remark = ""
    else:
        remark = "\n\nIf you have updated your password, please use </update-password:1045212370944929802>."
    return ErrorEmbed(title="Authentication Error", description=f"Make sure your **username** and **password** are correct and try again.\n\nEnsure you are using the username and password for signing in to your **Riot Account**, not your VALORANT display name or Riot ID.{remark}").set_image(url="https://cdn.discordapp.com/attachments/871737314831908974/1045221258670903348/brave_YlSOdWyDbs.png")


def rate_limit_error():
    return ErrorEmbed(title="Rate Limited", description="Your request has been rate limited by Riot.\nYou might have tried to log in too many times, please try again in a few minutes.")


def multifactor_detected():
    e = ErrorEmbed(title="Multifactor Authentication unavailable", description="Cypher's Laptop is unable to access stores/night markets for accounts with **Multi Factor Authentication (MFA) enabled**.\n\nRiot Games pushed a change that, for now, __prevents__ many store checkers (including Cypher's Laptop) __from sending the email containing your MFA code to you__. As a result we cannot verify your account if it has MFA enabled.\n** **")
    e.add_field(name="Non-MFA accounts remain unaffected ✅", value="The developer of Cypher's Laptop sincerely apologises for any inconvience this might cause to you. If you'd want to continue checking your store we __recommend you disable MFA__ if it's possible for you to do so.")
    return e
    #return ErrorEmbed(title="Additional Verification Required", description="Your account has **Multi Factor Authentication (MFA) enabled**.\nRiot Games has sent a 6-digit code to your email, check your email and enter the MFA code below.")



def multifactor_error():
    return ErrorEmbed(title="Multifactor Failed", description="The MFA code you entered was incorrect.\nPlease rerun the command to re-enter the code or request for a new one.\n\nNote that you will need enter a new multifactor code every time you check your store.", color=discord.Color.red())


def skin_not_found(skin_name):
    return ErrorEmbed(title="Skin Not Found", description=f"I could not find a skin with the name **{skin_name}**.", color=discord.Color.red())

def accessory_not_found(name, type):
    if type is None:
        type = "Player Card, Player Title, Gun Buddy or Spray"
    return ErrorEmbed(title="Accessory Not Found", description=f"I could not find a {type} with the name **{name}**.")

def not_ready():
    return ErrorEmbed(title="Not Ready", description="Cypher's Laptop is still booting up. Try again in a few seconds!", color=discord.Color.red())


def skin_embed(
        skin: GunSkin, is_in_wishlist: bool, currency: Optional[dict] = None,
        nm_p: Optional[int] = None, nm_c: Optional[int] = None, nm_s: Optional[bool] = True
    ):
    tier_uuids = get_tier_data()
    tier = next((x for x in tier_uuids if x["uuid"] == skin.contentTierUUID), None)
    if nm_p is not None:
        cost = f"<:vp:1045605973005434940> ~~{comma_number(skin.cost)}~~ `-{nm_p}%` **{comma_number(nm_c)}**"
    else:
        cost = f"<:vp:1045605973005434940> **{comma_number(skin.cost)}**" if skin.cost is not None else "<:DVB_False:887589731515392000> Not on sale"
    final_price = nm_c or skin.cost
    if currency is not None and final_price is not None:
        vp_per_dollar = currency["vp_per_dollar"]
        if vp_per_dollar == 0:
            with open("assets/currencies.json") as f:
                currencies = json.load(f)
            exch = currency["exch"]
            vp_per_dollar = currencies["data"]["USD"]["vp_per_dollar"] * exch
        if currency['decimal_digits'] == 0:
            cost_rounded = int(final_price * vp_per_dollar)
            cost_fr = comma_number(cost_rounded)
        else:
            cost_rounded = round(final_price * vp_per_dollar, currency['decimal_digits'])
            # comma_number doesn't work with decimals, so we need to split the whole number
            # and decimal and run comma_number on whole number before joining it with decimal
            cost_fr = comma_number(int(cost_rounded)) + "." + str(cost_rounded).split(".")[1]

        cost += f" *≈ {currency['symbol']} {cost_fr}*"
    if nm_s is True:
        embed = discord.Embed(title=skin.displayName, description=f"{cost}")
        embed.set_thumbnail(url=skin.displayIcon or "https://cdn.discordapp.com/attachments/1046947484150284390/1061895579359252531/no_image.jpg")
    else:
        embed = discord.Embed().set_image(url=tier["nm_image"])
    if tier is not None:
        embed.color = tier["color"]
        if nm_s is True:
            embed.description += f"\n{tier['emoji']} {tier['name']}"
    if is_in_wishlist:
        embed.set_footer(text="This skin is in your wishlist!", icon_url="https://cdn.discordapp.com/emojis/1046281227142975538.webp?size=96&quality=lossless")
        embed.color = 0xDD2F45
    return embed

async def accessory_embed(accessory: Accessory):
    embed = discord.Embed(title=accessory.name, description="", color=2829617)
    theme = None
    if accessory.theme_uuid:
        async with aiohttp.ClientSession() as session:
            response = await session.get(f"https://valorant-api.com/v1/themes/{accessory.theme_uuid}")
            if response.status == 200:
                data = await response.json()
                if theme_name := data.get("data", {}).get("displayIcon"):
                    theme = theme_name


    if isinstance(accessory, Buddy):
        embed.set_author(name="Coin Buddy", icon_url="https://media.discordapp.net/attachments/805604591630286918/1138737966341165127/coin_buddy.png")
        embed.set_image(url=accessory.display_img)
    elif isinstance(accessory, Spray):
        embed.set_author(name="Spray",
                         icon_url="https://media.discordapp.net/attachments/805604591630286918/1138739114624163941/spray.png")
        embed.set_image(url=accessory.display_img)
    elif isinstance(accessory, PlayerCard):
        embed.set_author(name="Player Card")
        embed.set_image(url=accessory.wide_img)
        embed.set_thumbnail(url=accessory.display_img)
    elif isinstance(accessory, PlayerTitle):
        embed.set_author(name="Player Title")
        embed.description = accessory.display_title
    if theme:
        embed.set_footer(text=f"This is a part of \"{theme}\",")
    return embed





def night_market_closed(before_nm = False):
    if before_nm:
        return discord.Embed(title="VALORANT's Night Market will return on <t:1680652800:F>,",
                             description="until <t:1682467199:D>.", color=0xffe8b6).set_footer(
            text="From @PlayVALORANT on Twitter").set_image(
            url="https://pbs.twimg.com/media/Fse6UGUXsAo4WP0?format=jpg&name=medium")
    else:
        return discord.Embed(title="VALORANT's Night Market is not open!",
                             description="Follow [@PlayVALORANT on Twitter](https://twitter.com/PlayVALORANT) for updates on future Night Markets!",
                             color=2829617).set_footer(
            text="Based on previous Night Market appearances, the next Night Market might open in appr. February 2023.").set_image(
            url="https://cdn.discordapp.com/attachments/868454485683470397/1060407886393647155/nightmarket_e.png")



# ------- Discord Bot Setup Error Responses -------

def permission_error():
    return discord.Embed(title="Permission Error (403 Forbidden)", description="Permissions in this server channel do not allow messages to be sent.\nA server admin will need to allow message sending for Cypher's Laptop in channel permission settings.", color=discord.Color.dark_red())


def not_me_message():
    return ErrorEmbed(description="This isn't my message! I only delete messages sent by me.")


def dm_only_command():
    return ErrorEmbed(description="This command can only be used in Direct Messages.")


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


