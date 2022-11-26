import asyncpg
from cryptography.fernet import Fernet
from dotenv import load_dotenv
from utils.specialobjects import RiotUser, GunSkin
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

    async def get_skin(self, skin_name) -> GunSkin:
        skin = await self.pool_pg.fetchrow("SELECT * FROM skins WHERE LOWER(displayname) = $1", skin_name.lower())
        if skin is None:
            return False
        return GunSkin().from_record(skin)

