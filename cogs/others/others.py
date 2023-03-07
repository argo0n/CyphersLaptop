import json

import discord
from discord.ext import commands

from main import clvt
from utils.buttons import SingleURLButton, SuggestionDeveloperView, confirm, SuggestionUserReplyView, FAQMenu, FAQView
from .settings import Settings
from ..maincommands.database import DBManager
from utils.responses import not_me_message, message_delete_success, help_command, dm_only_command


class Others(Settings, commands.Cog):
    def __init__(self, client):
        self.client: clvt = client
        self.dbManager: DBManager = None

    @commands.Cog.listener()
    async def on_ready(self):
        self.client.add_view(FAQView())
        self.client.add_view(SuggestionDeveloperView())
        self.client.add_view(SuggestionUserReplyView())
        await self.client.wait_until_ready()
        self.dbManager = DBManager(self.client.db)


    @commands.slash_command(name="help", description="See all of Cypher's Laptop commands.")
    async def help(self, ctx: discord.ApplicationContext):
        await ctx.respond(embed=help_command(await self.client.is_dev(ctx.author.id)))

    @commands.message_command(name="Delete my message")
    async def delete_own_message(self, ctx: discord.ApplicationContext, message: discord.Message):
        if message.author.id != self.client.user.id:
            return await ctx.respond(embed=not_me_message(), ephemeral=True)
        # check if channel is a DM channel
        if ctx.guild is not None:
            return await ctx.respond(embed=dm_only_command(), ephemeral=True)

        await message.delete()
        await ctx.respond(embed=message_delete_success(), ephemeral=True)

    @commands.slash_command(name="about", description="About Cypher's Laptop.")
    async def about(self, ctx: discord.ApplicationContext):
        embed = discord.Embed(
            title="Nothing stays hidden from Cypher. Nothing. Not even your <:val:1046289333344288808> VALORANT Store.",
            description="Cypher's Laptop helps you track your <:val:1046289333344288808> Store, to make sure you never miss out on your favorite skin.",
            color=discord.Color.blue())
        embed.add_field(name="Features",
                        value="• **Check** and **Track** your VALORANT Store with a wishlist\n• **Search** for VALORANT gun skins\n• View your <:vp:1045605973005434940> <:rp:1045991796838256640> Balance\n• Get daily reminders to check your store\n",
                        inline=False)
        embed.add_field(name="Get started",
                        value="1) Login to your Riot account through the </login:1045213188209258518> command. Your password is encrypted and stored securely.\n2) Run </store:1045171702612639836> to check your VALORANT Store!\n\nA login isn't required for seraching skins. You can log out anytime, and your credentials are deleted immediately from our storage.",
                        inline=False)
        # embed.add_field(name="\u200b", value="\u200b", inline=False)
        embed.add_field(name="Developer", value="Argon#0002", inline=True)
        embed.add_field(name="Privacy",
                        value="Passwords are encrypted with Fernet and stored in a secure database. Not even the developer can view them.",
                        inline=True)
        embed.add_field(name="Source",
                        value="[GitHub](https://github.com/argo0n/CyphersLaptop)",
                        inline=True)
        embed.add_field(name="Thanks",
                        value="[Valorina](https://github.com/sanjaybaskaran01/Valorina), [Valemporium](https://github.com/PureAspiration/Valemporium), [ValorantClientAPI](https://github.com/HeyM1ke/ValorantClientAPI), [python-riot-auth](https://github.com/floxay/python-riot-auth), [Valorant-API](https://valorant-api.com/)",
                        inline=True)
        embed.set_footer(
            text="Cypher's Laptop is not endorsed by Riot Games and does not reflect the views or opinions of Riot Games or anyone officially involved in producing or managing Riot Games properties. Riot Games and all associated properties are trademarks or registered trademarks of Riot Games, Inc.")
        await ctx.respond(embed=embed)

    @commands.slash_command(name="invite", description="Invite Cypher's Laptop to your server!")
    async def invite(self, ctx: discord.ApplicationContext):
        embed = discord.Embed(title="Cypher's Laptop - A VALORANT Store tracking bot on Discord",
                              description="Nothing stays hidden from Cypher. Nothing. Not even your VALORANT Store.\nCypher's Laptop helps you track your VALORANT Store, to make sure you never miss out on your favorite skin.",
                              color=0x2f3136)
        embed.set_image(
            url="https://cdn.discordapp.com/attachments/805604591630286918/1045968296488480818/CyphersLaptopWideEdited.png")

        await ctx.respond(embed=embed, view=SingleURLButton(text="Click here to invite Cypher's Laptop",
                                                            link=f"https://discord.com/api/oauth2/authorize?client_id={self.client.user.id}&permissions=137439266880&scope=bot%20applications.commands"))

    @commands.slash_command(name="suggest", description="Suggestions don't always get approved, but keep the ideas going!")
    async def suggest(self, ctx: discord.ApplicationContext,
                      suggestion: discord.Option(str, description="An idea for a new feature or improvement for Cypher's Laptop", min_length=1, max_length=512)
                      ):
        await ctx.defer()
        channel = await self.client.fetch_channel(1075290139703660594)
        c = confirm(ctx, self.client, 30)
        m = await ctx.respond(embed=discord.Embed(title="Are you sure you want to make this suggestion?", description=suggestion, color=self.client.embed_color), view=c)
        await c.wait()
        if c.returning_value is not True:
            return
        else:
            suggestion_id = await self.client.db.fetchval("INSERT INTO suggestions(user_id, content) VALUES($1, $2) RETURNING suggestion_id", ctx.author.id, suggestion)
            embed = discord.Embed(title=f"Suggestion #{suggestion_id}", description=suggestion, color=discord.Color.blue())
            embed.set_author(name=ctx.author, icon_url=ctx.author.display_avatar.url)
            channel_suggestion_msg = await channel.send(embed=embed, view=SuggestionDeveloperView())
            await self.client.db.execute("UPDATE suggestions SET server_message_id = $1 WHERE suggestion_id = $2", channel_suggestion_msg.id, suggestion_id)
            user_embed = discord.Embed(title="Your suggestion has been submitted.", description=suggestion, color=self.client.embed_color).set_footer(text="If we need more information, you'll be contacted via DMs.").set_thumbnail(url=ctx.me.display_avatar.url)
            if type(m) == discord.Interaction:
                await m.edit_original_response(embed=user_embed)
            else:
                await m.edit(embed=user_embed)
            if ctx.guild is not None:
                await ctx.author.send(embed=user_embed)

    @commands.slash_command(name="faq", description="Check out Cypher's Laptop's frequently asked questions.")
    async def faq(self, ctx: discord.ApplicationContext):
        embed = discord.Embed(description="Select a Frequently Asked Question.", color=self.client.embed_color)
        embed.set_author(name="Cypher's Laptop",
                         icon_url="https://cdn.discordapp.com/avatars/844489130822074390/ab663738f44bf18062f0a5f77cf4ebdd.png?size=32")
        await ctx.respond(embed=embed, view=FAQView())
