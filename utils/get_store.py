import itertools
import json
import aiohttp
from .time import humanize_timedelta


async def getStore(headers, user_id, region) -> (list[str], int):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://pd.{region}.a.pvp.net/store/v2/storefront/{user_id}/", headers=headers) as r:  # gets user's store, returns a json['SingleItemOffers'] that has a list of VALORANT skins the user has in the shop in the form of UUIDs
            data = await r.json()
    skin_panel = data['SkinsPanelLayout']
    skins = []
    for skin_uuid in skin_panel['SingleItemOffers']:
        skin_uuid = skin_uuid.lower()
        skins.append(skin_uuid)
    return skins, skin_panel['SingleItemOffersRemainingDurationInSeconds']


async def getNightMarket(headers, user_id, region):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://pd.{region}.a.pvp.net/store/v2/storefront/{user_id}/", headers=headers) as r:
            data = await r.json()
    #data = json.loads(open("assets/sample_response_with_night.json", "r").read())
    try:
        night_market = data["BonusStore"]
        night_market_offers = night_market["BonusStoreOffers"]
        skins = []
        for item in night_market_offers:
            uuid: str = item["Offer"]["OfferID"].lower()
            org_cost: int = item["Offer"]["Cost"]["85ad13f7-3d1b-5128-9eb2-7cd8ee0b5741"]
            discounted_p: int = item["DiscountPercent"]
            discounted_cost: int = item["DiscountCosts"]["85ad13f7-3d1b-5128-9eb2-7cd8ee0b5741"]
            is_seen: bool = item["IsSeen"]
            skins.append((uuid, org_cost, discounted_p, discounted_cost, is_seen))
        return skins, night_market["BonusStoreRemainingDurationInSeconds"]
    except KeyError: # no night market
        return None, 0


async def getAllSkins():
    async with aiohttp.ClientSession() as session:
         async with session.get(f"https://valorant-api.com/v1/weapons/skins") as r:
             data = await r.json()
    return data.get('data')



async def getRawOffers(headers, region):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://pd.{region}.a.pvp.net/store/v1/offers/",
                               headers=headers) as r:  # gets all sellable skins from the official VALORANT API, along with their costs ?
            offers = await r.json()
    return offers["Offers"]

async def getSkinDetails(headers, skin_panel, region):
    offers = await getRawOffers(headers, region)
    async with aiohttp.ClientSession() as session:
        skin_names = []
        for item in skin_panel['SingleItemOffers']:
            async with session.get(f"https://valorant-api.com/v1/weapons/skinlevels/{item}/", headers=headers) as r:  # gets the details of a single skin returned from VALORANT API's v2 storefront through the unofficial VALORANT API.
                content = await r.json()
                skin_names.append({"id": content['data']['uuid'].lower(), "name": content['data']['displayName']})
        skin_id_cost = []
        for item in offers:
            if skin_panel['SingleItemOffers'].count(item['OfferID'].lower()) > 0:
                skin_id_cost.append({"id": item['OfferID'].lower(), "cost": list(item['Cost'].values())[0]})

        offer_skins = []
        for item, item2 in itertools.product(skin_names, skin_id_cost):
            if item['id'] in item2['id']:
                offer_skins.append([item['name'], item2['cost'], f"https://media.valorant-api.com/weaponskinlevels/{item['id']}/displayicon.png"])

        return offer_skins, humanize_timedelta(seconds=skin_panel['SingleItemOffersRemainingDurationInSeconds'])


async def getBalance(headers, puuid, region):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://pd.{region}.a.pvp.net/store/v1/wallet/{puuid}", headers=headers, json={}) as r:
            data = await r.json()
    balances = data['Balances']
    return balances['85ad13f7-3d1b-5128-9eb2-7cd8ee0b5741'], balances['e59aa87c-4cbf-517a-5983-6e81511be9b7'], balances['85ca954a-41f2-ce94-9b45-8ca3dd39a00d'], balances['f08d4ae3-939c-4576-ab26-09ce1f23bb37']


async def check_limited_function(client):
    return await client.db.fetchval("SELECT enabled FROM temptable WHERE enabled IS NOT NULL")

