import asyncio
from typing import Optional

import discord
from discord.ext import commands

from cogs.maincommands.database import DBManager
from utils.responses import *
from utils.helper import *


class WishListManager(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.dbManager: DBManager = DBManager(self.client.db)

    wishlist_grp = discord.SlashCommandGroup(name="wishlist", description="Manage your VALORANT skin wishlist.")

    async def valorant_skin_autocomplete(self, ctx: discord.AutocompleteContext):
        if not self.ready:
            return ["Cypher's Laptop is still booting up. Try again in a few seconds!"]
        sk = await self.dbManager.get_all_skins()

        if len(ctx.value) > 0:
            results = []
            for skin in sk:
                if ctx.value.lower() in skin.displayName.lower():
                    results.append(skin.displayName)
            return results[:25]
        else:
            return [s.displayName for s in sk[:25]]

    async def get_user_wishlisted_skins(self, ctx: discord.AutocompleteContext):
        if not self.ready:
            return ["Cypher's Laptop is still booting up. Try again in a few seconds!"]
        sk = await self.dbManager.get_user_wishlist(ctx.interaction.user.id)
        skin_names = []
        results = []
        if len(ctx.value) > 0:

            for uuid in sk:
                if len(results) <= 25:
                    skin = await self.dbManager.get_skin_by_uuid(uuid)
                    if ctx.value.lower() in skin.displayName.lower():
                        results.append(skin.displayName)
        else:
            for uuid in sk:
                if len(results) <= 25:
                    skin = await self.dbManager.get_skin_by_uuid(uuid)
                    results.append(skin.displayName)
        return results


    @wishlist_grp.command(name="show", description="Check your VALORANT shop wishlist.")
    async def wishlist(self, ctx):
        wishlist = await self.dbManager.get_user_wishlist(ctx.author.id)
        skins = []
        tier_uuids = get_tier_data()
        for wish in wishlist:
            sk = await self.dbManager.get_skin_by_uuid(wish)
            em = ""
            for tier in tier_uuids:
                if tier["uuid"] == sk.contentTierUUID:
                    em = tier["emoji"]
            skins.append(f"{em} {sk.displayName}")
        embed = discord.Embed(title="Wishlist", description="\n".join(skins) if len(skins) > 0 else "You have no skins on your wishlist. Use </wishlist add:1046095784292130946> to add some!", color=self.client.embed_color)
        embed.set_footer(text=f"{len(skins)} skins on your wishlist")
        await ctx.respond(embed=embed)

    @wishlist_grp.command(name="add", description="Add a VALORANT gun skin to your wishlist.")
    async def add(self, ctx, skin: discord.Option(str, "A VALORANT gun skin name", autocomplete=valorant_skin_autocomplete)):
        sk = await self.dbManager.get_skin_by_name_or_uuid(skin)
        if sk is None:
            await ctx.respond(embed=skin_not_found(skin))
        result = await self.dbManager.add_skin_to_wishlist(ctx.author.id, sk.uuid)
        if result is True:
            await ctx.respond(embed=skin_added_to_wishlist(sk.displayName))
        else:
            await ctx.respond(embed=skin_already_on_wishlist(sk.displayName))

    @wishlist_grp.command(name="remove", description="Remove a VALORANT gun skin from your wishlist.")
    async def remove(self, ctx, skin: discord.Option(str, "A VALORANT gun skin name", autocomplete=get_user_wishlisted_skins)):
        sk = await self.dbManager.get_skin_by_name_or_uuid(skin)
        if sk is None:
            await ctx.respond(embed=skin_not_found(skin))
        result = await self.dbManager.remove_skin_from_wishlist(ctx.author.id, sk.uuid)
        if result is True:
            await ctx.respond(embed=skin_removed_from_wishlist(sk.displayName))
        else:
            await ctx.respond(embed=skin_not_on_wishlist(sk.displayName))

