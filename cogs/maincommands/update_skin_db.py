import json
import re
import time

import aiohttp
import discord
from discord.ext import commands, tasks

from cogs.maincommands.database import DBManager
from main import clvt
from utils import riot_authorization, get_store
from utils.format import print_exception
from utils.specialobjects import GunSkin



class UpdateSkinDB(commands.Cog):
    def __init__(self, client):
        self.client: clvt = client
        self.dbManager: DBManager = DBManager(self.client.db)


    @tasks.loop(hours=1)
    async def update_skin_db(self):
        upd_time = int(time.time())
        error = None
        try:
            riot_account = await self.dbManager.get_user_by_user_id(0)
            if riot_account:
                pass
            else:
                error = "No Riot Account with user ID 0"
            try:
                auth = riot_authorization.RiotAuth()
                await auth.authorize(riot_account.username, riot_account.password)
            except riot_authorization.Exceptions.RiotAuthenticationError:
                error = "Riot Authentication Error"
            except riot_authorization.Exceptions.RiotRatelimitError:
                error = "Riot Ratelimit Error"
            except riot_authorization.Exceptions.RiotMultifactorError:
                error = "Riot Multifactor Error"
            else:
                headers = {
                    "Authorization": f"Bearer {auth.access_token}",
                    "User-Agent": riot_account.username,
                    "X-Riot-Entitlements-JWT": auth.entitlements_token,
                    "X-Riot-ClientPlatform": "ew0KCSJwbGF0Zm9ybVR5cGUiOiAiUEMiLA0KCSJwbGF0Zm9ybU9TIjogIldpbmRvd3MiLA0KCSJwbGF0Zm9ybU9TVmVyc2lvbiI6ICIxMC4wLjE5MDQyLjEuMjU2LjY0Yml0IiwNCgkicGxhdGZvcm1DaGlwc2V0IjogIlVua25vd24iDQp9",
                    "X-Riot-ClientVersion": "pbe-shipping-55-604424"
                }
                raw_offers = await get_store.getRawOffers(headers, riot_account.region)
                all_skins = await get_store.getAllSkins()
                skins = []
                for s in all_skins:
                    i = GunSkin()
                    i.contentTierUUID = s["contentTierUuid"]
                    if i.contentTierUUID is None:
                        continue
                    skin = s["levels"]
                    for b in skin:
                        i.displayName = b["displayName"]
                        i.uuid = b["uuid"].lower()
                        i.displayIcon = b["displayIcon"]
                        for offer in raw_offers:
                            if offer["OfferID"].lower() == b["uuid"].lower():
                                i.cost = offer["Cost"]["85ad13f7-3d1b-5128-9eb2-7cd8ee0b5741"]
                                break
                        break
                    raw_levels = s["levels"]
                    raw_chromas = s["chromas"]
                    chromas = []
                    levels = []

                    def get_level(s):
                        # Find the substring "Level" and the number following it
                        match = re.search(r'Level (\d+)', s)
                        if match:
                            # Return the number as an integer
                            return int(match.group(1))
                        else:
                            # Return None if no match was found
                            return None

                    for c in raw_chromas:
                        chroma_uuid = c['uuid']
                        name = c['displayName']
                        level = get_level(name)
                        chroma_name = name.split('\n')[-1].replace('(', '').replace(')', '')
                        name_filter = name.split('\n')[0]
                        displayIcon = c['displayIcon']
                        videoURL = c['streamedVideo']
                        chromas.append({
                                "uuid": chroma_uuid,
                                "name": name_filter,
                                "level": level,
                                "chroma_name": chroma_name,
                                "displayIcon": displayIcon,
                                "video": videoURL
                            })
                    i.chromas = chromas
                    if len(raw_levels) < 2:
                        i.levels = []
                    else:
                        for l in raw_levels:
                            display_name = l["displayName"]
                            level_item = l["levelItem"]
                            if level_item:
                                upg = " - " + level_item.split("::")[-1]
                            else:
                                upg = ""
                            level = get_level(display_name)
                            if level is None:
                                if upg is None:
                                    lvl = "Unknown"
                                else:
                                    lvl = upg
                            else:
                                lvl = f"Level {level}" + upg
                            levels.append({
                                    "uuid": l['uuid'],
                                    "displayName": l['displayName'],
                                    "levelName": lvl,
                                    "video": l['streamedVideo'],
                                    "displayIcon": l['displayIcon']
                                })
                        i.levels = levels
                    skins.append(i)




                for i in skins:
                    await self.client.db.execute("INSERT INTO skins(uuid, displayname, cost, displayicon, contenttieruuid, levels, chromas) "
                                                 "VALUES ($1, $2, $3, $4, $5, $6, $7) ON CONFLICT(uuid) DO UPDATE SET displayName = "
                                                 "$2, cost = $3, displayIcon = $4, contenttieruuid = $5, levels = $6, chromas = $7", i.uuid,
                                                 i.displayName, i.cost, i.displayIcon, i.contentTierUUID, json.dumps(i.levels, indent=2), json.dumps(i.chromas, indent=2))
        except Exception as e:
            error = str(e)
            print_exception("Ignoring exception while updating skin database, ", error)
        await self.client.update_service_status("Skin Database Update", upd_time, error)
