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


async def cl_unavailable_riot_sucks(ctx: discord.ApplicationContext):
    locales = {
        "id": {
            "title": "Cypher's Laptop sementara tidak tersedia",
            "description": "## Saat ini saya tidak bisa mendapatkan toko Anda, karena Riot Games telah menambal metode yang saya gunakan.\n\nArtinya, metode yang digunakan Cypher's Laptop untuk berkomunikasi dengan Riot Games sengaja diblokir oleh mereka.\n\n**__Semua__** pengecek toko **__tidak bisa__** membiarkan Anda memeriksa toko Anda.",
            "footer": "Tindakan Anda tidak selesai.",
            "field_name": "Apa yang harus saya lakukan sekarang?",
            "field_value": "Cypher's Laptop akan DM Anda jika perbaikan telah diterapkan.\n\nUntuk saat ini, gunakan klien permainan VALORANT untuk memeriksa toko Anda.\n\nSaya tidak memiliki kendali atas masalah ini; terserah Riot Games untuk membuka blokir metode yang digunakan oleh pengecek toko."
        },
        "da": {
            "title": "Cypher's Laptop midlertidigt utilgængelig",
            "description": "## Jeg kan ikke hente din butik lige nu, da Riot Games har patched metoden, som jeg bruger.\n\nDet vil sige, en metode som Cypher's Laptop bruger til at kommunikere med Riot Games, er blevet bevidst blokeret af dem.\n\n**__Alle__** butikskontrollører er **__ude af stand__** til at lade dig kontrollere din butik.",
            "footer": "Din handling blev ikke fuldført.",
            "field_name": "Hvad gør jeg nu?",
            "field_value": "Cypher's Laptop vil sende dig en besked, hvis der er implementeret en løsning.\n\nBrug for nuværende VALORANT-spilklienten til at kontrollere din butik.\n\nJeg har ingen kontrol over dette problem; det er op til Riot Games at ophæve blokeringen af den metode, som butikskontrollører bruger."
        },
        "de": {
            "title": "Cypher's Laptop vorübergehend nicht verfügbar",
            "description": "## Ich kann deinen Store im Moment nicht abrufen, da Riot Games die von mir verwendete Methode gepatcht hat.\n\nDas heißt, eine Methode, die Cypher's Laptop verwendet, um mit Riot Games zu kommunizieren, wurde von ihnen absichtlich blockiert.\n\n**__Alle__** Store-Checker sind **__nicht in der Lage__**, deinen Store anzuzeigen.",
            "footer": "Ihre Aktion wurde nicht abgeschlossen.",
            "field_name": "Was soll ich jetzt tun?",
            "field_value": "Cypher's Laptop wird dir eine Nachricht senden, wenn eine Lösung implementiert wurde.\n\nVerwende derzeit den VALORANT-Spielclient, um deinen Store zu überprüfen.\n\nIch habe keine Kontrolle über dieses Problem; es liegt an Riot Games, die verwendete Methode zur Überprüfung der Stores zu entsperren."
        },
        "en-GB": {
            "title": "Cypher's Laptop unavailable (for now)",
            "description": "## I have no way of getting your store at the moment, as Riot Games has patched the method that I use.\n\nThat is, a method that Cypher's Laptop uses to communicate with Riot Games was intentionally blocked by them.\n\n**__All__** store checkers are **__unable__** to let you check your store.",
            "footer": "Your action was not completed.",
            "field_name": "What do I do now?",
            "field_value": "Cypher's Laptop will DM you if a fix has been implemented.\n\nFor now, rely on the VALORANT Game Client to check your store.\n\nI have no control of this issue; it is up to Riot Games to unblock the method used by store checkers."
        },
        "en-US": {
            "title": "Cypher's Laptop unavailable (for now)",
            "description": "## I have no way of getting your store at the moment, as Riot Games has patched the method that I use.\n\nThat is, a method that Cypher's Laptop uses to communicate with Riot Games was intentionally blocked by them.\n\n**__All__** store checkers are **__unable__** to let you check your store.",
            "footer": "Your action was not completed.",
            "field_name": "What do I do now?",
            "field_value": "Cypher's Laptop will DM you if a fix has been implemented.\n\nFor now, rely on the VALORANT Game Client to check your store.\n\nI have no control of this issue; it is up to Riot Games to unblock the method used by store checkers."
        },
        "es-ES": {
            "title": "Cypher's Laptop no disponible (por ahora)",
            "description": "## No puedo obtener tu tienda en este momento, ya que Riot Games ha parcheado el método que uso.\n\nEs decir, un método que Cypher's Laptop usa para comunicarse con Riot Games fue bloqueado intencionalmente por ellos.\n\n**__Todos__** los verificadores de tiendas son **__incapaces__** de dejarte revisar tu tienda.",
            "footer": "Tu acción no se completó.",
            "field_name": "¿Qué hago ahora?",
            "field_value": "Cypher's Laptop te enviará un mensaje si se ha implementado una solución.\n\nPor ahora, confía en el cliente del juego VALORANT para revisar tu tienda.\n\nNo tengo control sobre este problema; depende de Riot Games desbloquear el método utilizado por los verificadores de tiendas."
        },
        "es-419": {
            "title": "Cypher's Laptop no disponible (por ahora)",
            "description": "## No puedo obtener tu tienda en este momento, ya que Riot Games ha parcheado el método que uso.\n\nEs decir, un método que Cypher's Laptop usa para comunicarse con Riot Games fue bloqueado intencionalmente por ellos.\n\n**__Todos__** los verificadores de tiendas son **__incapaces__** de dejarte revisar tu tienda.",
            "footer": "Tu acción no se completó.",
            "field_name": "¿Qué hago ahora?",
            "field_value": "Cypher's Laptop te enviará un mensaje si se ha implementado una solución.\n\nPor ahora, confía en el cliente del juego VALORANT para revisar tu tienda.\n\nNo tengo control sobre este problema; depende de Riot Games desbloquear el método utilizado por los verificadores de tiendas."
        },
        "fr": {
            "title": "Cypher's Laptop indisponible (pour l'instant)",
            "description": "## Je ne peux pas accéder à votre magasin pour le moment, car Riot Games a patché la méthode que j'utilise.\n\nC'est-à-dire qu'une méthode utilisée par Cypher's Laptop pour communiquer avec Riot Games a été intentionnellement bloquée par eux.\n\n**__Tous__** les vérificateurs de magasins sont **__incapables__** de vous permettre de vérifier votre magasin.",
            "footer": "Votre action n'a pas été complétée.",
            "field_name": "Que dois-je faire maintenant ?",
            "field_value": "Cypher's Laptop vous enverra un message si une solution a été mise en œuvre.\n\nPour l'instant, utilisez le client de jeu VALORANT pour vérifier votre magasin.\n\nJe n'ai aucun contrôle sur ce problème ; c'est à Riot Games de débloquer la méthode utilisée par les vérificateurs de magasins."
        },
        "hr": {
            "title": "Cypher's Laptop trenutno nije dostupan",
            "description": "## Trenutno nemam način da dođem do vaše trgovine jer je Riot Games zakrpio metodu koju koristim.\n\nTo jest, metoda koju Cypher's Laptop koristi za komunikaciju s Riot Gamesom je namjerno blokirana od strane njih.\n\n**__Svi__** provjeritelji trgovina su **__nesposobni__** vam omogućiti provjeru vaše trgovine.",
            "footer": "Vaša akcija nije dovršena.",
            "field_name": "Što sada?",
            "field_value": "Cypher's Laptop će vam poslati poruku ako je popravak implementiran.\n\nZa sada, koristite VALORANT klijent igre za provjeru vaše trgovine.\n\nNemam kontrolu nad ovim problemom; na Riot Gamesu je da deblokira metodu koju koriste provjeritelji trgovina."
        },
        "it": {
            "title": "Cypher's Laptop non disponibile (per ora)",
            "description": "## Al momento non posso ottenere il tuo negozio, poiché Riot Games ha patchato il metodo che utilizzo.\n\nCioè, un metodo che Cypher's Laptop utilizza per comunicare con Riot Games è stato intenzionalmente bloccato da loro.\n\n**__Tutti__** i controllori del negozio sono **__incapaci__** di permetterti di controllare il tuo negozio.",
            "footer": "La tua azione non è stata completata.",
            "field_name": "Cosa devo fare adesso?",
            "field_value": "Cypher's Laptop ti invierà un messaggio se è stata implementata una soluzione.\n\nPer ora, fai affidamento sul client di gioco VALORANT per controllare il tuo negozio.\n\nNon ho il controllo su questo problema; spetta a Riot Games sbloccare il metodo utilizzato dai controllori del negozio."
        },
        "lt": {
            "title": "Cypher's Laptop laikinai nepasiekiamas",
            "description": "## Šiuo metu negaliu gauti jūsų parduotuvės, nes Riot Games pataisė metodą, kurį naudoju.\n\nTai yra, metodą, kurį Cypher's Laptop naudoja bendraujant su Riot Games, jie tyčia užblokavo.\n\n**__Visi__** parduotuvės tikrintojai yra **__negalintys__** leisti jums patikrinti savo parduotuvę.",
            "footer": "Jūsų veiksmas nebuvo baigtas.",
            "field_name": "Ką man dabar daryti?",
            "field_value": "Cypher's Laptop praneš jums, jei bus įgyvendintas pataisymas.\n\nKol kas naudokite VALORANT žaidimo klientą savo parduotuvei patikrinti.\n\nAš neturiu šios problemos kontrolės; tai priklauso nuo Riot Games, ar atblokuoti metodą, kurį naudoja parduotuvės tikrintojai."
        },
        "hu": {
            "title": "Cypher's Laptop nem elérhető (jelenleg)",
            "description": "## Jelenleg nem tudom megszerezni az áruházadat, mivel a Riot Games javította az általam használt módszert.\n\nEz azt jelenti, hogy a Cypher's Laptop által használt módszert a Riot Games szándékosan blokkolta.\n\n**__Minden__** áruházellenőrző **__képtelen__** engedni, hogy ellenőrizd az áruházadat.",
            "footer": "A műveleted nem fejeződött be.",
            "field_name": "Mit tegyek most?",
            "field_value": "Cypher's Laptop értesíteni fog, ha javítást hajtottak végre.\n\nEgyelőre használd a VALORANT játékklienst az áruház ellenőrzésére.\n\nNincs befolyásom erre a problémára; a Riot Games döntése, hogy feloldja az áruházellenőrzők által használt módszert."
        },
        "nl": {
            "title": "Cypher's Laptop tijdelijk niet beschikbaar",
            "description": "## Ik kan je winkel momenteel niet ophalen, omdat Riot Games de methode die ik gebruik heeft gepatcht.\n\nDat wil zeggen, een methode die Cypher's Laptop gebruikt om te communiceren met Riot Games is opzettelijk door hen geblokkeerd.\n\n**__Alle__** winkelcheckers zijn **__niet in staat__** je winkel te laten controleren.",
            "footer": "Je actie is niet voltooid.",
            "field_name": "Wat moet ik nu doen?",
            "field_value": "Cypher's Laptop zal je een bericht sturen als er een oplossing is geïmplementeerd.\n\nGebruik voorlopig de VALORANT-gameclient om je winkel te controleren.\n\nIk heb geen controle over dit probleem; het is aan Riot Games om de methode die door winkelcheckers wordt gebruikt te deblokkeren."
        },
        "no": {
            "title": "Cypher's Laptop midlertidig utilgjengelig",
            "description": "## Jeg har ingen mulighet til å hente butikken din for øyeblikket, da Riot Games har fikset metoden jeg bruker.\n\nDet vil si at en metode som Cypher's Laptop bruker for å kommunisere med Riot Games, har blitt bevisst blokkert av dem.\n\n**__Alle__** butikksjekkere er **__ute av stand__** til å la deg sjekke butikken din.",
            "footer": "Handlingen din ble ikke fullført.",
            "field_name": "Hva gjør jeg nå?",
            "field_value": "Cypher's Laptop vil sende deg en melding hvis en løsning er implementert.\n\nFor nå, bruk VALORANT-spillklienten for å sjekke butikken din.\n\nJeg har ingen kontroll over dette problemet; det er opp til Riot Games å oppheve blokkeringen av metoden som brukes av butikksjekkere."
        },
        "pl": {
            "title": "Cypher's Laptop chwilowo niedostępny",
            "description": "## Obecnie nie mogę uzyskać dostępu do twojego sklepu, ponieważ Riot Games załatało metodę, której używam.\n\nTo znaczy, metoda, której Cypher's Laptop używa do komunikacji z Riot Games, została celowo przez nich zablokowana.\n\n**__Wszyscy__** kontrolerzy sklepu są **__niezdolni__** do pozwalania ci sprawdzać swojego sklepu.",
            "footer": "Twoja akcja nie została zakończona.",
            "field_name": "Co mam teraz zrobić?",
            "field_value": "Cypher's Laptop wyśle ci wiadomość, jeśli zostanie wdrożona poprawka.\n\nNa razie użyj klienta gry VALORANT, aby sprawdzić swój sklep.\n\nNie mam kontroli nad tym problemem; to zależy od Riot Games, aby odblokować metodę używaną przez kontrolerów sklepu."
        },
        "pt-BR": {
            "title": "Cypher's Laptop indisponível (por enquanto)",
            "description": "## Não tenho como obter sua loja no momento, pois a Riot Games corrigiu o método que uso.\n\nOu seja, um método que o Cypher's Laptop usa para se comunicar com a Riot Games foi intencionalmente bloqueado por eles.\n\n**__Todos__** os verificadores de lojas estão **__incapazes__** de permitir que você verifique sua loja.",
            "footer": "Sua ação não foi concluída.",
            "field_name": "O que faço agora?",
            "field_value": "Cypher's Laptop enviará uma mensagem para você se uma correção for implementada.\n\nPor enquanto, confie no cliente de jogo VALORANT para verificar sua loja.\n\nNão tenho controle sobre este problema; cabe à Riot Games desbloquear o método usado pelos verificadores de lojas."
        },
        "ro": {
            "title": "Cypher's Laptop indisponibil (pentru moment)",
            "description": "## Nu am nicio modalitate de a accesa magazinul tău în acest moment, deoarece Riot Games a corectat metoda pe care o folosesc.\n\nAdică, o metodă pe care Cypher's Laptop o folosește pentru a comunica cu Riot Games a fost blocată intenționat de către aceștia.\n\n**__Toți__** verificatorii de magazine sunt **__incapabili__** să îți permită verificarea magazinului tău.",
            "footer": "Acțiunea ta nu a fost finalizată.",
            "field_name": "Ce fac acum?",
            "field_value": "Cypher's Laptop îți va trimite un mesaj dacă a fost implementată o soluție.\n\nPentru moment, folosește clientul de joc VALORANT pentru a verifica magazinul tău.\n\nNu am control asupra acestei probleme; depinde de Riot Games să deblocheze metoda utilizată de verificatorii de magazine."
        },
        "fi": {
            "title": "Cypher's Laptop ei ole käytettävissä (tällä hetkellä)",
            "description": "## En voi tällä hetkellä hakea kauppaasi, koska Riot Games on korjannut käyttämäni menetelmän.\n\nEli menetelmä, jota Cypher's Laptop käyttää kommunikoidakseen Riot Gamesin kanssa, on tarkoituksella estetty heidän toimesta.\n\n**__Kaikki__** kaupan tarkastajat ovat **__kykenemättömiä__** antamaan sinun tarkistaa kauppasi.",
            "footer": "Toimintosi ei onnistunut.",
            "field_name": "Mitä teen nyt?",
            "field_value": "Cypher's Laptop lähettää sinulle viestin, jos korjaus on otettu käyttöön.\n\nTällä hetkellä luota VALORANT-peliasiakasohjelmaan kauppasi tarkistamiseksi.\n\nMinulla ei ole hallintaa tähän ongelmaan; on Riot Gamesin vastuulla poistaa eston, jota kaupan tarkastajat käyttävät."
        },
        "sv-SE": {
            "title": "Cypher's Laptop otillgänglig (för närvarande)",
            "description": "## Jag har ingen möjlighet att få tillgång till din butik för närvarande, eftersom Riot Games har patchat metoden jag använder.\n\nDet vill säga, en metod som Cypher's Laptop använder för att kommunicera med Riot Games har avsiktligt blockerats av dem.\n\n**__Alla__** butiksgranskare är **__oförmögna__** att låta dig kontrollera din butik.",
            "footer": "Din åtgärd slutfördes inte.",
            "field_name": "Vad ska jag göra nu?",
            "field_value": "Cypher's Laptop kommer att skicka ett meddelande till dig om en lösning har implementerats.\n\nFör närvarande, använd VALORANT-spelklienten för att kontrollera din butik.\n\nJag har ingen kontroll över detta problem; det är upp till Riot Games att avblockera metoden som används av butiksgranskare."
        },
        "vi": {
            "title": "Cypher's Laptop hiện không khả dụng",
            "description": "## Hiện tại tôi không thể lấy cửa hàng của bạn, vì Riot Games đã vá phương pháp tôi sử dụng.\n\nTức là, một phương pháp mà Cypher's Laptop sử dụng để giao tiếp với Riot Games đã bị họ cố ý chặn lại.\n\n**__Tất cả__** các công cụ kiểm tra cửa hàng đều **__không thể__** cho phép bạn kiểm tra cửa hàng của mình.",
            "footer": "Hành động của bạn chưa hoàn thành.",
            "field_name": "Bây giờ tôi phải làm gì?",
            "field_value": "Cypher's Laptop sẽ gửi tin nhắn cho bạn nếu một bản sửa lỗi đã được triển khai.\n\nHiện tại, hãy sử dụng khách hàng trò chơi VALORANT để kiểm tra cửa hàng của bạn.\n\nTôi không kiểm soát vấn đề này; việc mở khóa phương pháp sử dụng bởi các công cụ kiểm tra cửa hàng phụ thuộc vào Riot Games."
        },
        "tr": {
            "title": "Cypher's Laptop geçici olarak kullanılamıyor",
            "description": "## Şu anda mağazanı alamıyorum, çünkü Riot Games kullandığım yöntemi yamaladı.\n\nYani, Cypher's Laptop'ın Riot Games ile iletişim kurmak için kullandığı bir yöntem kasıtlı olarak onlar tarafından engellendi.\n\n**__Tüm__** mağaza kontrolörleri mağazanı kontrol etmeni **__sağlayamaz__**.",
            "footer": "Eylemin tamamlanmadı.",
            "field_name": "Şimdi ne yapmalıyım?",
            "field_value": "Cypher's Laptop bir düzeltme uygulanmışsa sana DM gönderecek.\n\nŞu anda mağazanı kontrol etmek için VALORANT oyun istemcisini kullan.\n\nBu sorun üzerinde kontrolüm yok; mağaza kontrolörleri tarafından kullanılan yöntemin engelini kaldırmak Riot Games'in sorumluluğunda."
        },
        "cs": {
            "title": "Cypher's Laptop není momentálně dostupný",
            "description": "## Momentálně nemohu získat váš obchod, protože Riot Games opravili metodu, kterou používám.\n\nTo znamená, že metoda, kterou Cypher's Laptop používá ke komunikaci s Riot Games, byla úmyslně zablokována.\n\n**__Všechny__** kontrolory obchodů jsou **__neschopné__** umožnit vám kontrolovat váš obchod.",
            "footer": "Vaše akce nebyla dokončena.",
            "field_name": "Co mám teď dělat?",
            "field_value": "Cypher's Laptop vám pošle zprávu, pokud byla implementována oprava.\n\nProzatím používejte klienta hry VALORANT ke kontrole vašeho obchodu.\n\nNemám kontrolu nad tímto problémem; záleží na Riot Games, aby odblokovali metodu používanou kontrolory obchodů."
        },
        "el": {
            "title": "Cypher's Laptop δεν είναι διαθέσιμο (προς το παρόν)",
            "description": "## Αυτή τη στιγμή δεν μπορώ να αποκτήσω το κατάστημά σας, καθώς η Riot Games έχει διορθώσει τη μέθοδο που χρησιμοποιώ.\n\nΔηλαδή, μια μέθοδος που χρησιμοποιεί το Cypher's Laptop για να επικοινωνεί με τη Riot Games έχει αποκλειστεί σκόπιμα από αυτούς.\n\n**__Όλοι__** οι ελεγκτές καταστημάτων είναι **__ανίκανοι__** να σας επιτρέψουν να ελέγξετε το κατάστημά σας.",
            "footer": "Η ενέργειά σας δεν ολοκληρώθηκε.",
            "field_name": "Τι να κάνω τώρα;",
            "field_value": "Το Cypher's Laptop θα σας στείλει ένα μήνυμα εάν έχει εφαρμοστεί μια διόρθωση.\n\nΠρος το παρόν, βασιστείτε στον πελάτη του παιχνιδιού VALORANT για να ελέγξετε το κατάστημά σας.\n\nΔεν έχω κανέναν έλεγχο σε αυτό το ζήτημα. Εξαρτάται από τη Riot Games να ξεμπλοκάρει τη μέθοδο που χρησιμοποιούν οι ελεγκτές καταστημάτων."
        },
        "bg": {
            "title": "Cypher's Laptop временно недостъпен",
            "description": "## В момента не мога да взема магазина ви, тъй като Riot Games са запушили метода, който използвам.\n\nТова означава, че метод, който Cypher's Laptop използва за комуникация с Riot Games, е умишлено блокиран от тях.\n\n**__Всички__** проверяващи магазини са **__неспособни__** да ви позволят да проверите вашия магазин.",
            "footer": "Вашето действие не беше завършено.",
            "field_name": "Какво да правя сега?",
            "field_value": "Cypher's Laptop ще ви изпрати съобщение, ако е приложена корекция.\n\nЗасега разчитайте на клиента на играта VALORANT, за да проверите магазина си.\n\nНямам контрол върху този проблем; зависи от Riot Games да деблокират метода, използван от проверяващите магазини."
        },
        "ru": {
            "title": "Cypher's Laptop временно недоступен",
            "description": "## Я не могу получить ваш магазин в данный момент, так как Riot Games исправили метод, который я использую.\n\nТо есть метод, который Cypher's Laptop использует для связи с Riot Games, был намеренно заблокирован ими.\n\n**__Все__** проверяющие магазины **__не могут__** позволить вам проверить ваш магазин.",
            "footer": "Ваше действие не было завершено.",
            "field_name": "Что мне делать теперь?",
            "field_value": "Cypher's Laptop отправит вам сообщение, если будет реализовано исправление.\n\nНа данный момент используйте клиент игры VALORANT для проверки вашего магазина.\n\nЯ не контролирую эту проблему; это зависит от Riot Games разблокировать метод, используемый проверяющими магазины."
        },
        "uk": {
            "title": "Cypher's Laptop тимчасово недоступний",
            "description": "## Я не можу отримати ваш магазин на даний момент, оскільки Riot Games виправили метод, який я використовую.\n\nТобто метод, який Cypher's Laptop використовує для зв'язку з Riot Games, був навмисно заблокований ними.\n\n**__Всі__** перевіряючі магазини **__не здатні__** дозволити вам перевірити ваш магазин.",
            "footer": "Вашу дію не було завершено.",
            "field_name": "Що мені робити зараз?",
            "field_value": "Cypher's Laptop надішле вам повідомлення, якщо буде реалізовано виправлення.\n\nНа даний момент використовуйте клієнт гри VALORANT для перевірки вашого магазину.\n\nЯ не контролюю цю проблему; це залежить від Riot Games розблокувати метод, який використовують перевіряючі магазини."
        },
        "hi": {
            "title": "Cypher's Laptop अस्थायी रूप से अनुपलब्ध है",
            "description": "## मैं इस समय आपके स्टोर को प्राप्त करने में असमर्थ हूँ, क्योंकि Riot Games ने उस विधि को पैच कर दिया है जिसका मैं उपयोग करता हूँ।\n\nयानि, एक विधि जिसे Cypher's Laptop Riot Games से संवाद करने के लिए उपयोग करता है, उन्हें जानबूझकर अवरुद्ध कर दिया गया है।\n\n**__सभी__** स्टोर चेकर **__असमर्थ__** हैं आपको अपना स्टोर जांचने की अनुमति देने के लिए।",
            "footer": "आपकी क्रिया पूरी नहीं हुई।",
            "field_name": "अब मुझे क्या करना चाहिए?",
            "field_value": "Cypher's Laptop आपको डीएम करेगा यदि एक फिक्स को लागू किया गया है।\n\nफिलहाल, अपने स्टोर की जांच के लिए VALORANT गेम क्लाइंट पर निर्भर रहें।\n\nइस समस्या पर मेरा कोई नियंत्रण नहीं है; यह Riot Games पर निर्भर करता है कि वे स्टोर चेकर द्वारा उपयोग की जाने वाली विधि को अनब्लॉक करें।"
        },
        "th": {
            "title": "Cypher's Laptop ไม่พร้อมใช้งาน (ในขณะนี้)",
            "description": "## ฉันไม่มีทางรับร้านค้าของคุณในขณะนี้ เนื่องจาก Riot Games ได้แก้ไขวิธีการที่ฉันใช้\n\nนั่นคือ วิธีการที่ Cypher's Laptop ใช้ในการสื่อสารกับ Riot Games ถูกบล็อกโดยเจตนา\n\n**__ตัวตรวจสอบร้านค้าทั้งหมด__** **__ไม่สามารถ__** ให้คุณตรวจสอบร้านค้าของคุณ",
            "footer": "การดำเนินการของคุณไม่เสร็จสิ้น",
            "field_name": "ฉันควรทำอย่างไรตอนนี้?",
            "field_value": "Cypher's Laptop จะส่งข้อความถึงคุณหากมีการแก้ไข\n\nในขณะนี้ ให้ใช้ VALORANT Game Client เพื่อตรวจสอบร้านค้าของคุณ\n\nฉันไม่มีการควบคุมปัญหานี้ มันขึ้นอยู่กับ Riot Games ที่จะปลดบล็อกวิธีที่ใช้โดยตัวตรวจสอบร้านค้า"
        },
        "zh-CN": {
            "title": "Cypher's Laptop 暂时不可用",
            "description": "## 目前我无法获取你的商店信息，因为 Riot Games 修补了我使用的方法。\n\n也就是说，Cypher's Laptop 用来与 Riot Games 通信的方法被他们故意封锁了。\n\n**__所有__** 商店检查工具都 **__无法__** 让你查看你的商店。",
            "footer": "你的操作未完成。",
            "field_name": "我现在该怎么办？",
            "field_value": "如果实现了修复，Cypher's Laptop 会私信你。\n\n目前，请使用 VALORANT 游戏客户端查看你的商店。\n\n我对此问题没有控制权；是否解除商店检查工具使用的方法取决于 Riot Games。"
        },
        "ja": {
            "title": "Cypher's Laptopは現在利用できません",
            "description": "## 現在、使用している方法がRiot Gamesによって修正されたため、ストアを取得することができません。\n\nつまり、Cypher's LaptopがRiot Gamesと通信するために使用している方法が意図的にブロックされました。\n\n**__すべての__** ストアチェッカーは、ストアを確認することが **__できません__** 。",
            "footer": "アクションが完了しませんでした。",
            "field_name": "今何をすればいいですか？",
            "field_value": "修正が実装された場合、Cypher's LaptopがDMを送信します。\n\n現在のところ、ストアを確認するにはVALORANTゲームクライアントを使用してください。\n\nこの問題を制御することはできません。ストアチェッカーが使用する方法をブロック解除するかどうかはRiot Gamesに依存します。"
        },
        "zh-TW": {
            "title": "Cypher's Laptop 暫時無法使用",
            "description": "## 目前我無法獲取你的商店信息，因為 Riot Games 修補了我使用的方法。\n\n也就是說，Cypher's Laptop 用來與 Riot Games 通信的方法被他們故意封鎖了。\n\n**__所有__** 商店檢查工具都 **__無法__** 讓你查看你的商店。",
            "footer": "你的操作未完成。",
            "field_name": "我現在該怎麼辦？",
            "field_value": "如果實現了修復，Cypher's Laptop 會私信你。\n\n目前，請使用 VALORANT 遊戲客戶端查看你的商店。\n\n我對此問題沒有控制權；是否解除商店檢查工具使用的方法取決於 Riot Games。"
        },
        "ko": {
            "title": "Cypher's Laptop 일시적으로 사용 불가",
            "description": "## Riot Games가 내가 사용하는 방법을 패치했기 때문에 현재 상점을 얻을 수 없습니다.\n\n즉, Cypher's Laptop이 Riot Games와 통신하는 데 사용하는 방법이 의도적으로 차단되었습니다.\n\n**__모든__** 상점 검사기는 상점을 확인할 수 **__없습니다__**.",
            "footer": "작업이 완료되지 않았습니다.",
            "field_name": "이제 무엇을 해야 합니까?",
            "field_value": "수정 사항이 구현되면 Cypher's Laptop이 DM을 보낼 것입니다.\n\n지금은 VALORANT 게임 클라이언트를 사용하여 상점을 확인하십시오.\n\n이 문제를 제어할 수 없습니다. 상점 검사기가 사용하는 방법을 차단 해제하는 것은 Riot Games에 달려 있습니다."
        }
    }

    locale = ctx.locale if ctx.locale in locales else "en-US"
    strings = locales[locale]

    embed = ErrorEmbed(title=strings["title"],
                       description=strings["description"])
    embed.set_footer(text=strings["footer"])
    embed.add_field(name=strings["field_name"], value=strings["field_value"])
    await ctx.respond(embed=embed)
