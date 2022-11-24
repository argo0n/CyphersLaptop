import discord

from discord.ext import pages

custom_buttons = [
    pages.PaginatorButton("first", emoji=discord.PartialEmoji.from_str('<:DVB_first_check:955345524519759903>'), style=discord.ButtonStyle.blurple),
    pages.PaginatorButton("prev", emoji=discord.PartialEmoji.from_str('<:DVB_prev_check:955345544623038484>'), style=discord.ButtonStyle.red),
    pages.PaginatorButton("page_indicator", style=discord.ButtonStyle.gray, disabled=True),
    pages.PaginatorButton("next", emoji=discord.PartialEmoji.from_str('<:DVB_next_check:955345527610945536>'), style=discord.ButtonStyle.green),
    pages.PaginatorButton("last", emoji=discord.PartialEmoji.from_str('<:DVB_last_check:955345526302318622>'), style=discord.ButtonStyle.blurple)
]


class SingleMenuPaginator(pages.Paginator):
    def __init__(self, pages, author_check=True, timeout=30.0):
        super().__init__(
            pages=pages,
            show_disabled=True,
            show_indicator=True,
            show_menu=False,
            author_check=author_check,
            disable_on_timeout=True,
            use_default_buttons=False,
            custom_buttons=custom_buttons,
            loop_pages=False,
            timeout=timeout
        )


class MultiMenuPaginator(pages.Paginator):
    def __init__(self, pages, menu_placeholder="View all options...", author_check=True, timeout=60.0):
        super().__init__(
            pages=pages,
            menu_placeholder=menu_placeholder,
            show_menu=True,
            show_disabled=True,
            show_indicator=True,
            author_check=author_check,
            disable_on_timeout=True,
            use_default_buttons=False,
            custom_buttons=custom_buttons,
            loop_pages=False,
            timeout=timeout
        )