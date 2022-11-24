from typing import Literal

import discord


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
        description = f"**{username}** is already logged into via another Discord account.\nIf you want to use your Riot account (**{username}**) on this account, log out of **{username}** on your other Discord account."
    return discord.Embed(title="User Already Exists", description=description, color=discord.Color.red())


def already_logged_in(username):
    return discord.Embed(title="Already Logged In", description=f"You are already logged in with the Riot Games account **{username}**.\nYou can only add one account at a time.", color=discord.Color.red())


def user_logged_in(username):
    return discord.Embed(title="Successfully logged in", description=f"**{username}** has been successfully verified and logged in.", color=discord.Color.green()).set_footer(text="Your password is encrypted when stored. Not even the developer can see your password.")


def user_logged_out(username):
    return discord.Embed(title="Successfully logged out", description=f"**{username}** has been successfully logged out.", color=discord.Color.green())


def user_updated(username):
    return discord.Embed(title="User Credentials Updated", description=f"Your Riot Games account, **{username}**'s password has been successfully verified and updated.", color=discord.Color.green())


def no_logged_in_account():
    return discord.Embed(title="No Logged In Account", description="You do not have a Riot account logged in with us.\nUse /adduser <username> <password> <region> to log in.", color=discord.Color.red())

def updated_password(username):
    return discord.Embed(title="Password Updated", description=f"The password for your Riot Games account **{username}** has been successfully updated.", color=discord.Color.green())


# ------- Riot Authentication Errors/Responses -------

def authentication_error(is_update_or_login_command: bool = False):
    if is_update_or_login_command:
        remark = ""
    else:
        remark = "\n\nIf you have updated your password, please use /setpassword <username> <password> <region> in DMs."
    return discord.Embed(title="Authentication Error", description=f"Make sure your **username** and **password** are correct and try again.\n\nEnsure you are using the username and password for signing in to your **Riot Account**, not your Valorant display name or Riot ID.{remark}", color=discord.Color.red()).set_image(url="https://cdn.discordapp.com/attachments/871737314831908974/1045221258670903348/brave_YlSOdWyDbs.png")


def rate_limit_error():
    return discord.Embed(title="Rate Limited", description="Your request has been rate limited by Riot.\nYou might have tried to log in too many times, please try again in a few minutes.", color=discord.Color.red())


def multifactor_detected():
    return discord.Embed(title="Enter 2 Factor Authentication (2FA) Code", description="Your account has 2FA enabled.\nCheck your emails for the code and use the command again: /store <username> <multifactor_code>.\n\nNote that you will need enter a new multifactor code every time you check your store.", color=discord.Color.red()).set_image(url="https://cdn.discordapp.com/attachments/871737314831908974/1045223829452095558/image.png")


def multifactor_error():
    return discord.Embed(title="Multifactor Failed", description="The 2FA code you entered was incorrect.\nPlease confirm your code or request a new code with the command: /store <username> <region>.\n\nNote that you will need enter a new multifactor code every time you check your store.", color=discord.Color.red())


# ------- Discord Bot Setup Error Responses -------

def permission_error():
    return discord.Embed(title="Permission Error (403 Forbidden)", description="Permissions in this server channel do not allow messages to be sent.\nA server admin will need to allow message sending for Valemporium in channel permission settings.", color=discord.Color.dark_red())


# ------- Unknown Error (Unhandled exception) -------

def unknown_error():
    return discord.Embed(title="An Error Occurred", description="An unknown error occurred. This issue has been raised and will be fixed as soon as possible.\nIf this issue persists, please submit a request in the [Valemporium support server](https://discord.gg/ejvddZr4Dw)", color=discord.Color.dark_red())


# ------- Informational Responses -------

def help_command():
    embed = discord.Embed(title="Valemporium - Help", description="All available commands and important command arguments", color=discord.Color.blue())
    embed.add_field(name="/store", value="Retrieves the store of a player", inline=False)
    embed.add_field(name="/balance", value="Retrieves the balance of your Valorant account", inline=False)
    embed.add_field(name="/adduser", value="Saves login credentials to the database (ONLY use this command in DMs)", inline=False)
    embed.add_field(name="/deluser", value="Deletes login credentials from the database (ONLY use this command in DMs)", inline=False)
    embed.add_field(name="/setpassword", value="Edits the password of the user in the database (ONLY use this command in DMs)", inline=False)
    embed.add_field(name="/about", value="About Valemporium", inline=False)
    embed.add_field(name="Region Selection", value="ap - Asia/Pacific\neu - Europe\nkr - Korea\nna - North America, Brazil, and PBE", inline=False)
    embed.add_field(name="Support Server", value="For Discord support, join the [Valemporium support server](https://discord.gg/ejvddZr4Dw)", inline=False)
    embed.add_field(name="⠀", value="Enter your riot username, not your Valorant display name\nOnly enter passwords in direct messages with the bot", inline=False)
    return embed


def about_command():
    embed = discord.Embed(title="Valemporium - About", description="About Valemporium", color=discord.Color.blue())
    embed.add_field(name="Developer", value="Bot created and coded by Pure#2254", inline=False)
    embed.add_field(name="Privacy and Security", value="All passwords and credentials are encrypted with Fernet and stored in a secure database.", inline=False)
    embed.add_field(name="Source", value="This project is open source and can be viewed on [Github](https://github.com/PureAspiration/Valemporium).", inline=False)
    embed.add_field(name="Built with", value="This project is heavy based on [Valorina](https://github.com/sanjaybaskaran01/Valorina), [python-riot-auth](https://github.com/floxay/python-riot-auth), PyMongo.", inline=False)
    embed.add_field(name="License", value="Distributed under the MIT License. Copyright (c) 2022 PureAspiration", inline=False)
    embed.add_field(name="Legal", value="For any riot employees, please contact Pure#2254 regarding this bot before taking any actions on our players and users.\n\nValemporium is not endorsed by Riot Games and the developer is not liable for any damage, bans, or loss of account caused by this bot.\nRiot Games, and all associated properties are trademarks or registered trademarks of Riot Games, Inc.", inline=False)
    return embed

