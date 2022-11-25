import itertools
import json
import aiohttp
from .time import humanize_timedelta


async def getStore(headers, user_id, region):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://pd.{region}.a.pvp.net/store/v2/storefront/{user_id}/", headers=headers) as r:  # gets user's store, returns a json['SingleItemOffers'] that has a list of VALORANT skins the user has in the shop in the form of UUIDs
            data = await r.json()
    skin_panel = data['SkinsPanelLayout']
    return await getSkinDetails(headers, skin_panel, region)


async def getSkinDetails(headers, skin_panel, region):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://pd.{region}.a.pvp.net/store/v1/offers/", headers=headers) as r:  # gets all sellable skins from the official VALORANT API, along with their costs ?
            offers = await r.json()
            skin_names = []
            for item in skin_panel['SingleItemOffers']:
                async with session.get(f"https://valorant-api.com/v1/weapons/skinlevels/{item}/", headers=headers) as r:  # gets the details of a single skin returned from VALORANT API's v2 storefront through the unofficial VALORANT API.
                    content = await r.json()
                    skin_names.append({"id": content['data']['uuid'].lower(), "name": content['data']['displayName']})
            skin_id_cost = []
            for item in offers['Offers']:
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
    return data['Balances']['85ad13f7-3d1b-5128-9eb2-7cd8ee0b5741'], data['Balances']['e59aa87c-4cbf-517a-5983-6e81511be9b7']