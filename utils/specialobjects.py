from typing import Any, Union

import asyncpg


class _MissingSentinel:
    def __eq__(self, other):
        return False

    def __bool__(self):
        return False

    def __repr__(self):
        return "..."


class ReminderConfig:
    __slots__ = ('user_id', 'enabled', 'show_immediately', 'picture_mode')
    def __init__(self, record):
        self.user_id: int = record.get('user_id')
        self.enabled: bool = record.get('enabled')
        self.show_immediately: bool = record.get('show_immediately')
        self.picture_mode: bool = record.get('picture_mode')

    def __repr__(self) -> str:
        return f"<ReminderConfig user_id={self.user_id} enabled={self.enabled} show_immediately={self.show_immediately} picture_mode={self.picture_mode}>"

    async def update(self, client):
        await client.db.execute("UPDATE store_reminder SET enabled=$1, show_immediately=$2, picture_mode=$3 WHERE user_id=$4", self.enabled, self.show_immediately, self.picture_mode, self.user_id)


MISSING: Any = _MissingSentinel()


class RiotUser:

    __slots__ = ('user_id', 'username', 'password', 'region')

    def __init__(self, record: asyncpg.Record):
        self.user_id: int = record.get('user_id')
        self.username: str = record.get('username')
        self.password: bytes = record.get('password')
        self.region: str = record.get('region')

    def from_method(self, user_id: int, username: str, password: bytes, region: str):
        self.user_id = user_id
        self.username = username
        self.password = password
        self.region = region
        return self


class GunSkin:

    __slots__ = ('uuid', 'displayName', 'cost', 'displayIcon', 'contentTierUUID')

    def __init__(self):
        self.uuid: str = None
        self.displayName: str = None
        self.cost: int = None
        self.displayIcon: str = None
        self.contentTierUUID: str = None

    def from_record(self, record: asyncpg.Record):
        self.uuid = record.get('uuid')
        self.displayName = record.get('displayname')
        self.cost = record.get('cost')
        self.displayIcon = record.get('displayicon')
        self.contentTierUUID = record.get('contenttieruuid')
        return self

    def __repr__(self):
        return f"<GunSkin uuid={self.uuid} displayName={self.displayName} cost={self.cost} displayIcon={self.displayIcon} contentTierUUID={self.contentTierUUID}>"

