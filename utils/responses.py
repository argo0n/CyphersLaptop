from typing import Literal

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
    return discord.Embed(title="Successfully logged in", description=f"Your Riot account, **{username}** has been successfully verified and logged in.\n\nIf you received a login MFA code, you may ignore it.", color=discord.Color.green()).set_footer(text="Your password is encrypted when stored. Not even the developer can see your password.")


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


# ------- Riot Authentication Errors/Responses -------

def authentication_error(is_update_or_login_command: bool = False):
    if is_update_or_login_command:
        remark = ""
    else:
        remark = "\n\nIf you have updated your password, please use </update-password:1045212370944929802> <password>."
    return discord.Embed(title="Authentication Error", description=f"Make sure your **username** and **password** are correct and try again.\n\nEnsure you are using the username and password for signing in to your **Riot Account**, not your VALORANT display name or Riot ID.{remark}", color=discord.Color.red()).set_image(url="https://cdn.discordapp.com/attachments/871737314831908974/1045221258670903348/brave_YlSOdWyDbs.png")


def rate_limit_error():
    return discord.Embed(title="Rate Limited", description="Your request has been rate limited by Riot.\nYou might have tried to log in too many times, please try again in a few minutes.", color=discord.Color.red())


def multifactor_detected():
    return discord.Embed(title="Enter 2 Factor Authentication (2FA) Code", description="Your account has 2FA enabled.\nCheck your emails for the code and use the command again: </store:1045171702612639836> <multifactor_code>.\n\nNote that you will need enter a new multifactor code every time you check your store.", color=discord.Color.red()).set_image(url="https://cdn.discordapp.com/attachments/871737314831908974/1045223829452095558/image.png")


def multifactor_error():
    return discord.Embed(title="Multifactor Failed", description="The 2FA code you entered was incorrect.\nPlease confirm your code or request a new code with the command: </store:1045171702612639836> <multifactor_code>.\n\nNote that you will need enter a new multifactor code every time you check your store.", color=discord.Color.red())

def skin_not_found(skin_name):
    return discord.Embed(title="Skin Not Found", description=f"I could not find a skin with the name {skin_name}.", color=discord.Color.red())
def not_ready():
    return discord.Embed(title="Not Ready", description="Cypher's Laptop is still booting up. Try again in a few seconds!", color=discord.Color.red())

def skin_embed(skin: GunSkin):

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
    print(skin)
    cost = f"<:vp:1045605973005434940> {comma_number(skin.cost)}" if skin.cost is not None else "<:DVB_False:887589731515392000> Not on sale"
    embed = discord.Embed(title=skin.displayName, description=f" {cost}")
    if tier is not None:
        embed.color = tier["color"]
        embed.description += f"\n{tier['emoji']} **{tier['name']}** tier"
    embed.set_image(url=skin.displayIcon)
    return embed


# ------- Discord Bot Setup Error Responses -------

def permission_error():
    return discord.Embed(title="Permission Error (403 Forbidden)", description="Permissions in this server channel do not allow messages to be sent.\nA server admin will need to allow message sending for Valemporium in channel permission settings.", color=discord.Color.dark_red())


# ------- Unknown Error (Unhandled exception) -------

def unknown_error():
    return discord.Embed(title="An Error Occurred", description="An unknown error occurred. This issue has been raised and will be fixed as soon as possible.\nIf this issue persists, please submit a request in the [Valemporium support server](https://discord.gg/ejvddZr4Dw)", color=discord.Color.dark_red())


# ------- Informational Responses -------

def help_command(is_dev):
    embed = discord.Embed(title="Valemporium - Help", description="All available commands and important command arguments", color=discord.Color.blue())
    embed.add_field(name="</store:1045171702612639836>", value="Retrieves your VALORANT store.", inline=True)
    embed.add_field(name="</skin:1045732151506767973>", value="Search for a VALORANT gun skin.", inline=True)
    embed.add_field(name="</invite:1045732151506767974>", value="Invite Cypher's Laptop to your server!", inline=True)
    embed.add_field(name="</balance:1045213188209258517>", value="View your <:vp:1045605973005434940> Balance.", inline=True)
    embed.add_field(name="</update-password:1045212370944929802>", value="Update your Riot account password in Cypher's Laptop if you have changed it.", inline=True)
    embed.add_field(name="</login:1045213188209258518>", value="Log in to Cypher's Laptop with your Riot account. \nYour password is encrypted and stored securely when you log in.", inline=False)
    embed.add_field(name="</logout:1045213188209258519>", value="Log out of Cypher's Laptop.\nYour credentials are immediately deleted from the database once you log out.", inline=True)
    if is_dev:
        embed.add_field(name="DEVELOPER", value="\u200b", inline=False)
        embed.add_field(name="</update-skins-database:1045634432268255303>", value="Manually update the internal VALORANT gun skins database.", inline=True)
        embed.add_field(name="</get-raw-credentials:1045622620500000821>", value="Get raw credentials of your Riot account to communicate with the VALORANT API for testing.", inline=True)
    embed.set_thumbnail(url="https://cdn.discordapp.com/avatars/844489130822074390/bfe9b52d135dce826739ba0adbe31cfd.png?size=1024")
    return embed


