import json
from typing import Any, Union
from enum import Enum, auto

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

    __slots__ = ('uuid', 'displayName', 'cost', 'displayIcon', 'contentTierUUID', 'chromas', 'levels')

    def __init__(self):
        self.uuid: str = None
        self.displayName: str = None
        self.cost: int = None
        self.displayIcon: str = None
        self.contentTierUUID: str = None
        self.chromas: dict = None
        self.levels: dict = None

    def from_record(self, record: asyncpg.Record):
        self.uuid = record.get('uuid')
        self.displayName = record.get('displayname')
        self.cost = record.get('cost')
        self.displayIcon = record.get('displayicon')
        self.contentTierUUID = record.get('contenttieruuid')
        self.chromas = json.loads(record.get('chromas'))
        self.levels = json.loads(record.get('levels'))
        return self

    def __repr__(self):
        return f"<GunSkin uuid={self.uuid} displayName={self.displayName} cost={self.cost} displayIcon={self.displayIcon} contentTierUUID={self.contentTierUUID}> chromas={self.chromas} levels={self.levels}"


class NightMarketGunSkin(GunSkin):
    __slots__ = ('seen', 'discounted_p', 'discounted_cost')

    def __init__(self):
        super().__init__()
        self.seen: bool = False
        self.discounted_p: float = 0
        self.discounted_cost: int = 0

    def __repr__(self):
        return f"<NightMarketGunSkin uuid={self.uuid} displayName={self.displayName} cost={self.cost} displayIcon={self.displayIcon} contentTierUUID={self.contentTierUUID} seen={self.seen} discounted_p={self.discounted_p} discounted_cost={self.discounted_cost}> chromas={self.chromas} levels={self.levels}"

class UserSetting:
    __slots__ = ('user_id', 'currency', 'show_username', 'nm_reminder')

    def __init__(self, record):
        self.user_id: int = record.get('user_id')
        self.currency: Union[str, None] = record.get('currency')
        self.show_username: bool = record.get('show_username')
        self.nm_reminder: bool = record.get('nm_reminder')

    def __repr__(self) -> str:
        return f"<UserSetting user_id={self.user_id} currency={self.currency}> show_username={self.show_username} nm_reminder={self.nm_reminder}>"

    async def update(self, client):
        await client.db.execute("UPDATE user_settings SET currency=$1, show_username=$2, nm_reminder=$3 WHERE user_id=$4", self.currency, self.show_username, self.nm_reminder, self.user_id)


class AccessoryType(Enum):
    PLAYER_CARD = "playercard"
    BUDDY = "buddy"
    SPRAY = "spray"
    PLAYER_TITLE = "playertitle"

class Accessory:
    def __init__(self, uuid, name, theme_uuid, display_title, display_img, wide_img, long_img, type_):
        self.uuid = uuid
        self.name = name
        self.theme_uuid = theme_uuid
        self.display_title = display_title
        self.display_img = display_img
        self.wide_img = wide_img
        self.long_img = long_img
        self.type_ = type_

    # This can be a method or a property
    def to_tuple(self):
        return (self.uuid, self.name, self.theme_uuid, self.display_title, self.display_img, self.wide_img, self.long_img, self.type_.name)

    @staticmethod
    def from_record(record: asyncpg.Record):
        uuid, name, theme_uuid, display_title, display_img, wide_img, long_img, type_ = record.get("uuid"), record.get("name"), record.get("theme_uuid"), record.get("display_title"), record.get("display_img"), record.get("wide_img"), record.get("long_img"), record.get("type")
        if type_ == AccessoryType.PLAYER_CARD.value:
            return PlayerCard(uuid, name, theme_uuid, display_img, wide_img, long_img)
        elif type_ == AccessoryType.BUDDY.value:
            return Buddy(uuid, name, display_img)
        elif type_ == AccessoryType.SPRAY.value:
            return Spray(uuid, name, display_img)
        elif type_ == AccessoryType.PLAYER_TITLE.value:
            return PlayerTitle(uuid, name, display_title)



class PlayerCard(Accessory):
    def __init__(self, uuid, name, theme_uuid, display_img, wide_img, long_img):
        super().__init__(uuid, name, theme_uuid, None, display_img, wide_img, long_img, AccessoryType.PLAYER_CARD)

class Buddy(Accessory):
    def __init__(self, uuid, name, display_img):
        super().__init__(uuid, name, None, None, display_img, None, None, AccessoryType.BUDDY)

class Spray(Accessory):
    def __init__(self, uuid, name, display_img):
        super().__init__(uuid, name, None, None, display_img, None, None, AccessoryType.SPRAY)

class PlayerTitle(Accessory):
    def __init__(self, uuid, name, display_name):
        super().__init__(uuid, name, None, display_name, None, None, None, AccessoryType.PLAYER_TITLE)