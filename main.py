import asyncio
import os
import time
from typing import Optional, Union, Tuple

import aiohttp
import discord
import asyncpg
import datetime
from dotenv import load_dotenv
from discord import client
from discord.ext import commands, tasks
from utils.context import CLVTcontext
from utils.format import print_exception
from utils.specialobjects import MISSING, UserInfo


strfformat = "%d-%m-%y %H:%M:%S"


AVAILABLE_EXTENSIONS = [
    "cogs.maincommands",
    "cogs.reminders",
    "cogs.errors",
    "cogs.dev"
]

load_dotenv('credentials.env')
token = os.getenv('TOKEN')
host = os.getenv('HOST')
database = os.getenv('DATABASE')
user = os.getenv('dbUSER')
port = int(os.getenv('dbPORT'))
password = os.getenv('dbPASSWORD')


intents = discord.Intents(messages=True, message_content=True)
allowed_mentions = discord.AllowedMentions(everyone=False, roles=False)


class clvt(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix = self.get_prefix, intents=intents, allowed_mentions=allowed_mentions, case_insensitive=True)
        self.custom_status = False
        self.prefixes = {}
        self.uptime = None
        self.embed_color: int = 0x57F0F0
        self.db: asyncpg.pool = None
        self.serverconfig = {}
        self.maintenance = {}
        self.maintenance_message = {}
        self.available_extensions = AVAILABLE_EXTENSIONS
        self.editqueue = []
        self.deleted_edit_messages = []
        for ext in self.available_extensions:
            self.load_extension(ext, store=False)
            print(f"{datetime.datetime.utcnow().strftime(strfformat)} | Loaded {ext}")

    async def get_context(self, message, *, cls=None):
        context = await super().get_context(message, cls=CLVTcontext)
        return context

    async def process_commands(self, message: discord.Message):
        ctx: CLVTcontext = await self.get_context(message)
        await self.invoke(ctx)

    async def on_message(self, message):
        if message.author.bot:
            return
        await self.process_commands(message)

    async def after_ready(self):
        await self.wait_until_ready()

    async def on_ready(self):
        print(f"{datetime.datetime.utcnow().strftime(strfformat)} | Loaded all Server Configurations")
        all_tables = ['prefixes', "valorant_login", "devmode", "skins"]
        print(f"{datetime.datetime.utcnow().strftime(strfformat)} | Checking for missing databases")
        tables = await self.db.fetch("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE';")
        tables = [i.get('table_name') for i in tables]
        if tables is None:
            pass
        else:
            missing_tables = []
            for table in all_tables:
                if table not in tables:
                    missing_tables.append(table)
            if len(missing_tables) == 0:
                pass
            else:
                print(f"Some databases do not exist, creating them now...")
                await self.db.execute("""
                CREATE TABLE IF NOT EXISTS valorant_login(user_id bigint PRIMARY KEY NOT NULL, username text NOT NULL, password bytea NOT NULL, region text NOT NULL);
                CREATE TABLE IF NOT EXISTS devmode(user_id bigint, enabled boolean);
                CREATE TABLE IF NOT EXISTS skins(uuid text PRIMARY KEY NOT NULL, displayName text not null, displayIcon text, cost int, contentTierUUID text);
                CREATE TABLE IF NOT EXISTS prefixes(guild_id bigint PRIMARY KEY NOT NULL, prefix text NOT NULL);
                """)
        print(f"{datetime.datetime.utcnow().strftime(strfformat)} | {self.user} ({self.user.id}) is ready")

    @property
    def error_channel(self):
        return self.get_guild(801457328346890241).get_channel(1045982323599999078)

    async def is_dev(self, user_id):
        return await self.db.fetchval("SELECT enabled FROM devmode WHERE user_id=$1", user_id)

    async def on_guild_join(self, guild):
        await self.db.execute('INSERT INTO prefixes VALUES ($1, $2) ON CONFLICT DO UPDATE SET prefix=$2', guild.id, "cl.")

    async def get_prefix(self, message):
        if message.guild is None:
            return commands.when_mentioned_or('.')(self, message)
        guild_id = message.guild.id
        if not (prefix := self.prefixes.get(guild_id)):
            query = "SELECT prefix FROM prefixes WHERE guild_id=$1"
            data = await self.db.fetchrow(query, guild_id)
            if data is None:
                await self.db.execute("INSERT INTO prefixes VALUES ($1, $2)", guild_id, 'cl.')
                data = {}
            prefix = self.prefixes.setdefault(guild_id, data.get("prefix") or '.')
        if message.content.lower().startswith(prefix):
            prefix = message.content[:len(prefix)]
        return commands.when_mentioned_or(prefix)(self, message)

    async def set_prefix(self, guild, prefix):
        await self.db.execute('UPDATE prefixes SET prefix=$1 WHERE guild_id=$2', prefix, guild.id)
        self.prefixes[guild.id] = prefix

    async def update_service_status(self, service_type, upd_time, error = None):
        types = {
            "Skin Database Update": 1045986497825878047
        }
        async with aiohttp.ClientSession() as session:
            webh = discord.Webhook.from_url(os.getenv('WEBHOOK'), session=session)
            if service_type not in types.keys():
                print(f"Service type should be one of {types.keys()}")
                return
            if error is None:
                embed = discord.Embed(title=service_type, color=discord.Color.green())
                embed.add_field(name="Last Update", value=f"<t:{upd_time}:R>")
            else:
                embed = discord.Embed(title=service_type, color=discord.Color.red())
                embed.add_field(name="Last Update", value=f"<t:{upd_time}:R>")
                embed.add_field(name="Error", value=str(error))
            try:
                await webh.edit_message(message_id=types.get(service_type), embed=embed)
            except Exception as e:
                print(f"Failed to update status for \"{service_type}\": {e}")







    async def fetch_user_info(self, user_id):
        userinfo = await self.db.fetchrow("SELECT * FROM userinfo WHERE user_id=$1", user_id)
        if userinfo is None:
            await self.db.execute("INSERT INTO userinfo(user_id) VALUES ($1)", user_id)
            userinfo = await self.db.fetchrow("SELECT * FROM userinfo WHERE user_id=$1", user_id)
        return UserInfo(userinfo)

    def get_guild_prefix(self, guild):
        if guild is None:
            return 'cl.'
        return self.prefixes.get(guild.id)

    async def shutdown(self):
        """Cancels tasks and shuts down the bot."""
        await self.topgg_webhook.close()
        await self.close()

    def starter(self):
        """starts the bot properly."""
        start = time.time()
        print(f"{datetime.datetime.utcnow().strftime(strfformat)} | Starting Bot")
        try:
            pool_pg = self.loop.run_until_complete(asyncpg.create_pool(
                host=host,
                port=port,
                database=database,
                user=user,
                password=password
            ))
        except Exception as e:
            print_exception(f"{datetime.datetime.utcnow().strftime(strfformat)} | Could not connect to databases:", e)
        else:
            self.uptime = discord.utils.utcnow()
            self.db = pool_pg
            print(f"{datetime.datetime.utcnow().strftime(strfformat)} | Connected to the database")
            self.loop.create_task(self.after_ready())
            self.run(token)

if __name__ == '__main__':
    client = clvt()
    client.starter()