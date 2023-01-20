import asyncpg
from cryptography.fernet import Fernet
from dotenv import load_dotenv
from utils.specialobjects import RiotUser, GunSkin, ReminderConfig, UserSetting
import os

load_dotenv()
FERNET_KEY = os.getenv("FERNET_KEY")


class DBManager:
    def __init__(self, pool_pg):
        self.pool_pg: asyncpg.Pool = pool_pg

    async def check_user_existence(self, username):
        return bool(await self.get_user_by_username(username))

    async def add_user(self, user_id, username, password, region):
        if not await self.check_user_existence(username):
            password = self.encrypt_password(password)
            await self.pool_pg.execute("INSERT INTO valorant_login (user_id, username, password, region) VALUES ($1, $2, $3, $4)", user_id, username, password, region)
            return True
        return False

    def encrypt_password(self, password):
        password = Fernet(FERNET_KEY).encrypt(password.encode("utf-8"))
        return password

    def decrypt_password(self, password):
        password = (Fernet(FERNET_KEY).decrypt(password)).decode("utf-8")
        return password

    async def update_password(self, username, password):
        if await self.check_user_existence(username):
            password = self.encrypt_password(password)
            await self.pool_pg.execute("UPDATE valorant_login SET password = $1 WHERE username = $2", password, username)
            return True
        return False

    async def get_user_by_username(self, username):
        user = await self.pool_pg.fetchrow("SELECT * FROM valorant_login WHERE username = $1", username)
        if user is None:
            return False
        user_obj = RiotUser(user)
        user_obj.password = self.decrypt_password(user_obj.password)
        return user_obj

    async def get_user_by_user_id(self, user_id):
        user = await self.pool_pg.fetchrow("SELECT * FROM valorant_login WHERE user_id = $1", user_id)
        if user is None:
            return False
        user_obj = RiotUser(user)
        user_obj.password = self.decrypt_password(user_obj.password)
        return user_obj

    async def get_all_users(self):
        users = await self.pool_pg.fetch("SELECT * FROM valorant_login")
        return [RiotUser(user) for user in users]

    async def get_all_skins(self) -> list[GunSkin]:
        all_skins_raw = await self.pool_pg.fetch("SELECT * FROM skins")
        skins = []
        for skin in all_skins_raw:
            sk = GunSkin().from_record(skin)
            skins.append(sk)
        return skins

    async def get_skin_by_name_or_uuid(self, skin_name) -> GunSkin:
        skin = await self.pool_pg.fetchrow("SELECT * FROM skins WHERE LOWER(displayname) = $1 OR LOWER(uuid) = $1", skin_name.lower())
        if skin is None:
            return False
        return GunSkin().from_record(skin)
    
    async def get_skin_by_uuid(self, skin_uuid) -> GunSkin:
        skin = await self.pool_pg.fetchrow("SELECT * FROM skins WHERE uuid = $1", skin_uuid)
        if skin is None:
            return False
        return GunSkin().from_record(skin)
    
    async def get_user_wishlist(self, user_id):
        wishlist = await self.pool_pg.fetch("SELECT * FROM wishlist WHERE user_id = $1", user_id)
        return [wish.get("skin_uuid") for wish in wishlist]
    
    async def add_skin_to_wishlist(self, user_id, skin_uuid):
        if not await self.get_skin_by_uuid(skin_uuid):
            return False
        if skin_uuid in await self.get_user_wishlist(user_id):
            return False
        await self.pool_pg.fetchval("INSERT INTO wishlist (user_id, skin_uuid) VALUES ($1, $2)", user_id, skin_uuid)
        return True

    async def remove_skin_from_wishlist(self, user_id, skin_uuid):
        if not await self.get_skin_by_uuid(skin_uuid):
            return False
        if skin_uuid not in await self.get_user_wishlist(user_id):
            return False
        await self.pool_pg.fetchval("DELETE FROM wishlist WHERE user_id = $1 AND skin_uuid = $2", user_id, skin_uuid)
        return True

    async def fetch_user_reminder_settings(self, user_id) -> ReminderConfig:
        rem_db = await self.pool_pg.fetchrow("SELECT * FROM store_reminder WHERE user_id = $1", user_id)
        if rem_db is None:
            await self.pool_pg.execute("INSERT INTO store_reminder(user_id) VALUES ($1)", user_id)
            rem_db = await self.pool_pg.fetchrow("SELECT * FROM store_reminder WHERE user_id = $1", user_id)
        return ReminderConfig(rem_db)
    
    async def fetch_user_settings(self, user_id) -> UserSetting:
        usr_se_db = await self.pool_pg.fetchrow("SELECT * FROM user_settings WHERE user_id = $1", user_id)
        if usr_se_db is None:
            await self.pool_pg.execute("INSERT INTO user_settings(user_id) VALUES ($1)", user_id)
            usr_se_db = await self.pool_pg.fetchrow("SELECT * FROM user_settings WHERE user_id = $1", user_id)
        return UserSetting(usr_se_db)
    
    async def fetch_reminders(self) -> list[ReminderConfig]:
        reminders = await self.pool_pg.fetch("SELECT * FROM store_reminder")
        return [ReminderConfig(rem) for rem in reminders]

    async def insert_onetimestore(self, user_id, skin1, skin2, skin3, skin4):
        return await self.pool_pg.execute("INSERT INTO onetimestores (user_id, skin1_uuid, skin2_uuid, skin3_uuid, skin4_uuid) VALUES ($1, $2, $3, $4, $5)", user_id, skin1, skin2, skin3, skin4)


