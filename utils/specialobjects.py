from typing import Any, Union

import asyncpg


class _MissingSentinel:
    def __eq__(self, other):
        return False

    def __bool__(self):
        return False

    def __repr__(self):
        return "..."


class UserInfo:
    __slots__ = ('user_id', 'notify_about_logging', 'bypass_ban', 'heists', 'heistamt')
    def __init__(self, record):
        self.user_id: int = record.get('user_id')
        self.notify_about_logging: bool = record.get('notify_about_logging')
        self.bypass_ban: bool = record.get('bypass_ban')
        self.heists: int = record.get('heists')
        self.heistamt: int = record.get('heistamt')

    def __repr__(self) -> str:
        return f"<UserInfo user_id={self.user_id} notify_about_logging={self.notify_about_logging} bypass_ban={self.bypass_ban} heists={self.heists} heistamt={self.heistamt}>"

    async def update(self, client):
        a = await client.db.execute("UPDATE userinfo SET notify_about_logging=$1, bypass_ban=$2, heists=$3, heistamt=$4 WHERE user_id = $5", self.notify_about_logging, self.bypass_ban, self.heists, self.heistamt, self.user_id)


MISSING: Any = _MissingSentinel()


class RiotUser:

    __slots__ = ('user_id', 'username', 'password', 'region')

    def __init__(self, record: asyncpg.Record):
        self.user_id: int = record.get('user_id')
        self.username: str = record.get('username')
        self.password: bytes = record.get('password')
        self.region: str = record.get('region')