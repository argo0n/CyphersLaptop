import sys
import discord
import traceback
from io import BytesIO
from typing import Sequence, Iterator, Literal
from discord.ext import commands
import inflect
import math
from expr import evaluate
import aiohttp
from utils.errors import ArgumentBaseError
from typing import Optional, Union

from utils.responses import ErrorEmbed

p = inflect.engine()

def durationdisplay(seconds):
    seconds = round(seconds)
    time = []
    if seconds < 60:
        time.append("0")
        time.append(str(seconds))
        return ":".join(time)
    minutes = math.trunc(seconds / 60)
    if minutes < 60:
        seconds = seconds - minutes * 60
        time.append(str(minutes))
        time.append("0" + str(seconds) if seconds < 10 else str(seconds))
    return ":".join(time)

class plural:
    """
    Auto corrects text to show plural or singular depending on the size number.
    """
    def __init__(self, value):
        self.value = value
    def __format__(self, format_spec):
        v = self.value
        singular, sep, plural = format_spec.partition('|')
        plural = plural or f'{singular}s'
        if abs(v) != 1:
            return f'{v} {plural}'
        return f'{v} {singular}'

def comma_number(number:int):
    return "{:,}".format(number)

def short_time(duration:int):
    if duration is None or duration < 1:
        return ''
    duration_in_mins = duration/60
    if duration_in_mins < 1:
        return '< 1m'
    if duration_in_mins < 60:
        return f'{math.ceil(duration_in_mins)}m'
    duration_in_hours = duration_in_mins/60
    if duration_in_hours < 1.017:
        return '1h'
    if duration_in_hours < 24:
        return f'{math.ceil(duration_in_hours)}h'
    duration_in_days = duration_in_hours/24
    if duration_in_days < 1.05:
        return '1d'
    else:
        return f'{math.ceil(duration_in_days)}d'



def human_join(seq, delim=', ', final='or'):
    """
    Returns a str with <final> before the last word.
    """
    size = len(seq)
    if size == 0:
        return ''
    if size == 1:
        return seq[0]
    if size == 2:
        return f'{seq[0]} {final} {seq[1]}'
    return delim.join(seq[:-1]) + f' {final} {seq[-1]}'

def escape(text: str, *, mass_mentions: bool = False, formatting: bool = False) -> str:
    """
    Get text with all mass mentions or markdown escaped.
    """
    if mass_mentions:
        text = text.replace("@everyone", "@\u200beveryone")
        text = text.replace("@here", "@\u200bhere")
    if formatting:
        text = discord.utils.escape_markdown(text)
    return text

def text_to_file(text: str, filename: str = "file.txt", encoding: str = "utf-8"):
    """
    Prepares text to be sent as a file on Discord, without character limit.
    """

    file = BytesIO(text.encode(encoding))
    return discord.File(file, filename)

def box(text: str, lang: str = "") -> str:
    """
    Returns the given text inside a codeblock.
    """
    ret = "```{}\n{}\n```".format(lang, text)
    return ret

def inline(text: str) -> str:
    """
    Returns the given text as inline code.
    """
    if "`" in text:
        return "``{}``".format(text)
    else:
        return "`{}`".format(text)

def pagify(text: str, delims: Sequence[str] = ["\n"], *, priority: bool = False, escape_mass_mentions: bool = True, shorten_by: int = 8, page_length: int = 2000, box_lang: str = None) -> Iterator[str]:
    """
    Generate multiple pages from the given text.
    """
    in_text = text
    page_length -= shorten_by
    while len(in_text) > page_length:
        this_page_len = page_length
        if escape_mass_mentions:
            this_page_len -= in_text.count("@here", 0, page_length) + in_text.count(
                "@everyone", 0, page_length
            )
        closest_delim = (in_text.rfind(d, 1, this_page_len) for d in delims)
        if priority:
            closest_delim = next((x for x in closest_delim if x > 0), -1)
        else:
            closest_delim = max(closest_delim)
        closest_delim = closest_delim if closest_delim != -1 else this_page_len
        if escape_mass_mentions:
            to_send = escape(in_text[:closest_delim], mass_mentions=True)
        else:
            to_send = in_text[:closest_delim]
        if len(to_send.strip()) > 0:
            to_send = box(to_send, lang=box_lang) if box_lang is not None else to_send
            yield to_send
        in_text = in_text[closest_delim:]

    if len(in_text.strip()) > 0:
        in_text = box(in_text, lang=box_lang) if box_lang is not None else in_text
        if escape_mass_mentions:
            yield escape(in_text, mass_mentions=True)
        else:
            yield in_text

def print_exception(text, error):
    """
    Prints the exception with proper traceback.
    """
    traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)
    etype = type(error)
    trace = error.__traceback__
    lines = traceback.format_exception(etype, error, trace)
    return ''.join(lines)

def ordinal(number:int):
    return p.ordinal(number)

def plural_noun(noun: str):
    return p.plural_noun(noun)


def get_command_name(command: Union[commands.Command, discord.ApplicationCommand]):
    """
    Returns commands name.
    """
    if isinstance(command, commands.Command):
        if command.parent:
            return f"{get_command_name(command.parent)} {command.name}"
        else:
            return command.name
    elif isinstance(command, discord.ApplicationCommand):
        return command.qualified_name


class TabularData:
    def __init__(self):
        self._widths = []
        self._columns = []
        self._rows = []

    def set_columns(self, columns):
        self._columns = columns
        self._widths = [len(c) + 2 for c in columns]

    def add_row(self, row):
        rows = [str(r) for r in row]
        self._rows.append(rows)
        for index, element in enumerate(rows):
            width = len(element) + 2
            if width > self._widths[index]:
                self._widths[index] = width

    def add_rows(self, rows):
        for row in rows:
            self.add_row(row)

    def render(self):
        """
        Renders a table in rST format.
        """

        sep = '+'.join('-' * w for w in self._widths)
        sep = f'+{sep}+'

        to_draw = [sep]

        def get_entry(d):
            elem = '|'.join(f'{e:^{self._widths[i]}}' for i, e in enumerate(d))
            return f'|{elem}|'

        to_draw.append(get_entry(self._columns))
        to_draw.append(sep)

        for row in self._rows:
            to_draw.append(get_entry(row))

        to_draw.append(sep)
        return '\n'.join(to_draw)


def split_string_into_list(string, return_type: Literal[str, int], delimiter=',', include_empty_elements: Optional[bool] = False) -> list:
    """
    Splits a string into a list. It will always return a list.
    """
    if include_empty_elements is True and return_type == int:
        raise ValueError("include_empty_elements cannot be True if return_type is int")
    if string is None:
        return []
    if len(string) == 0:
        return []
    split = string.split(delimiter)
    split = [s.strip() for s in split]
    new_split = []
    for s in split:
        if len(s) > 0:
            if return_type == str:
                new_split.append(s)
            elif return_type == int:
                new_split.append(int(s))
        else:
            if include_empty_elements is True:
                if return_type == str:
                    new_split.append(s)
    return new_split


def stringnum_toint(string:str):
    allowedsymbols = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "m", "k", 'e', '.', '-', ',']
    string = string.lower()
    for character in list(string):
        if character not in allowedsymbols:
            return None
    if string.isnumeric():
        return int(string)
    if "," in string:
        string = string.replace(", ", "").replace(",", "")
    if "m" in string:
        string = string.replace("m", "*1000000+")
    if "k" in string:
        string = string.replace("k", "*1000+")
    if 'e' in string:
        string = string.replace("e", "*10^")
    if string.endswith('+') or string.endswith('-'):
        string += "0"
    if string.endswith('/') or string.endswith('*') or string.endswith('^'):
        string += "1"
    try:
        intstring = evaluate(string)
    except:
        raise ArgumentBaseError(message=f"Something went wrong while I was trying to calculate how much you meant from `{string}`. Please contact the developer about this!")
    intstring = int(intstring) if intstring is not None else intstring
    return intstring


def stringtime_duration(string:str):
    allowedsymbols=["1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "m", "s", 'h', 'y', 'd', 'r', 'e', 'c', 'm', 'i', 'n', 'w', 'k']
    string = string.lower()
    for character in list(string):
        if character not in allowedsymbols:
            return None
    if string.isnumeric():
        return int(string)
    if 'sec' in string:
        string = string.replace('sec', '+')
    if 's' in string:
        string = string.replace('s', '+')
    if 'min' in string:
        string = string.replace('mins', '*60+').replace('min', '*60+')
    if 'm' in string:
        string = string.replace('m', '*60+')
    if 'hour' in string:
        string = string.replace('hours', '*3600+').replace('hour', '*3600+')
    if 'hr' in string:
        string = string.replace('hrs', '*3600+').replace('hr', '*3600+')
    if 'h' in string:
        string = string.replace('h', '*3600+')
    if 'day' in string:
        string = string.replace('days', '*86400+').replace('day', '*86400+')
    if 'd' in string:
        string = string.replace('d', '*86400+')
    if 'week' in string:
        string = string.replace('weeks', '*604800+').replace('week', '*604800+')
    if 'w' in string:
        string = string.replace('w', '*604800+')
    if 'year' in string:
        string = string.replace('years', '*31536000+').replace('year', '*31536000+')
    if 'yr' in string:
        string = string.replace('yrs', '*31536000+').replace('yr', '*31536000+')
    if 'y' in string:
        string = string.replace('y', '*31536000+')
    if string.endswith('+') or string.endswith('-'):
        string += "0"
    if string.endswith('/') or string.endswith('*') or string.endswith('^'):
        string += "1"
    try:
        intstring = evaluate(string)
    except:
        return None
    intstring = int(intstring) if intstring is not None else intstring
    return intstring


def grammarformat(iterable):
    if len(iterable) == 0:
        return ''
    if len(iterable) == 1:
        return iterable[0]
    if len(iterable) == 2:
        return iterable[0] + ' and ' + iterable[1]
    return ', '.join(iterable[:-1]) + ', and ' + iterable[-1]


async def get_image(url:str):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as r:
                data = await r.read()
        except aiohttp.InvalidURL:
            raise ArgumentBaseError(message=f"Invalid URL: {url}")
        except aiohttp.ClientError:
            raise ArgumentBaseError(message="Something went wrong while trying to get the image.")
        else:
            return data


def generate_loadbar(percentage: float, length: Optional[int] = 20):
    aStartLoad = "<a:DVB_aStartLoad:912007459898544198>"
    aMiddleLoad = "<a:DVB_aMiddleLoad:912007457214185565>"
    aEndLoad = "<a:DVB_aEndLoad:912007457591668827>"
    StartLoad = "<:DVB_StartLoad:912007458581516289>"
    MiddleLoad = "<:DVB_MiddleLoad:912007459118411786>"
    EndLoad = "<:DVB_EndLoad:912007458594127923>"
    eStartLoad = "<:DVB_eStartLoad:912007458938044436>"
    eMiddleLoad = "<:DVB_eMiddleLoad:912007458992574534>"
    eEndLoad = "<:DVB_eEndLoad:912007458942230608>"
    if length is None:
        length = 20
    rounded = round(percentage * length)
    if rounded == 0:
        return eStartLoad + eMiddleLoad * (length - 2) + eEndLoad
    else:
        if rounded == length:
            return StartLoad + MiddleLoad * (length - 2) + aEndLoad
        else:
            if rounded > 1:
                return StartLoad + MiddleLoad * (rounded - 1 - 1) + aMiddleLoad  + eMiddleLoad * (length - rounded - 1) + eEndLoad
            else:
                return aStartLoad + eMiddleLoad * (length - 1 - 1) + eEndLoad

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
    await ctx.respond(embed=embed);

