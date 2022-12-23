import discord
from discord import Embed, Colour
from discord.utils import MISSING, utcnow
from itertools import islice
from typing import Optional
from math import ceil
from pydantic import BaseModel, conint, constr, Field
from inspect import currentframe, getargvalues


class EmbedField(BaseModel):
    index: conint(ge = 1, le = 25) = Field(default = None)
    name: constr(min_length = 1, curtail_length = 256)
    value: constr(min_length = 1, curtail_length = 1024)
    inline: bool = Field(default = True)


def set_colour(colour: Colour | None):
    return Colour.random() if not colour else colour

def set_author(embed: discord.Embed, author: dict[str, str]) -> discord.Embed:
    if isinstance(author, dict):
        embed.set_author(name = author.get("name"), url = author.get("url"), icon_url = author.get("icon_url"))
    else:
        raise NotImplementedError
    return embed


def set_footer(embed: discord.Embed, footer: dict[str, str]) -> discord.Embed:
    if isinstance(footer, dict):
        embed.set_footer(text = footer.get("text"), icon_url = footer.get("icon_url"))
    else:
        raise NotImplementedError
    return embed


def set_image(embed: discord.Embed, image: str) -> discord.Embed:
    if isinstance(image, str):
        embed.set_image(url = image)
    else:
        raise NotImplementedError
    return embed


def set_thumbnail(embed: discord.Embed, image: str) -> discord.Embed:
    if isinstance(image, str):
        embed.set_thumbnail(url = image)
    else:
        raise NotImplementedError
    return embed


def SimpleEmbed(author: Optional[dict[str, str]] = None,
                title: Optional[str] = None,
                text: str = "",
                image: Optional[str] = None,
                thumbnail: Optional[str] = None,
                colour: Optional[Colour] = None,
                footer: Optional[dict[str, str]] = None) -> Embed:
    """
    Generates a simple embed with only the description field

    :param author: Embed Author: Optional dict{name: ..., url: ..., icon_url: ...}
    :param title: Embed Title: Str
    :param text: Embed Description: Str
    :param image: Embed Image: Optional str
    :param thumbnail: Embed Thumbnail: Optional str
    :param colour: Embed Colour: Optional colour
    :param footer: Embed footer: Optional dict{text: ..., icon_url: ...}
    :return: Discord Embed
    """
    embed = Embed(title = title, description = text[:4000], colour = set_colour(colour), timestamp = utcnow())
    _, _, _, values = getargvalues(currentframe())
    for arg, value in values.items():
        if any(arg in field for field in OPTIONAL_FIELDS) and value:
            OPTIONAL_FIELDS[arg](embed, value)
    return embed


def FullEmbed(
        author: Optional[dict[str, str]] = None,
        title: Optional[str] = None,
        fields: list[EmbedField] = MISSING,
        description: Optional[str] = None,
        image: Optional[str] = None,
        thumbnail: Optional[str] = None,
        colour: Optional[Colour] = None,
        footer: Optional[dict[str, str]] = None) -> Embed:
    """
    Generates an embed with up to 25 title: value fields plus description field.

    :param author: Embed Author: Optional dict{name: ..., url: ..., icon_url: ...}
    :param title: Embed Title: Optional str
    :param fields: list of embed fields: list[ EmbedField(Index = Optional[int], Name = str, Value = str, Inline = Optional[Bool]) ]
    :param description: Embed description: Optional str
    :param image: Embed Image: Optional str
    :param thumbnail: Embed Thumbnail: Optional str
    :param colour: Embed Colour: Optional colour
    :param footer: Embed footer: Optional dict{text: ..., icon_url: ...}
    :return: Discord Embed
    """
    embed = Embed(title = title, colour = set_colour(colour), description = description, timestamp = utcnow())
    for field in islice(fields, 25):
        if field.index:
            embed.insert_field_at(index = field.index, name = field.name, value = field.value, inline = field.inline)
        else:
            embed.add_field(name = field.name, value = field.value, inline = field.inline)
    _, _, _, values = getargvalues(currentframe())
    for arg, value in values.items():
        if any(arg in field for field in OPTIONAL_FIELDS) and value:
            OPTIONAL_FIELDS[arg](embed, value)
    return embed


def EmbedFieldList(
        author: Optional[dict[str, str]] = None,
        title: Optional[list[str] | str] = None,
        fields: list[EmbedField] = MISSING,
        max_fields: Optional[int] = 25,
        description: Optional[list[str]] = None,
        colour: Optional[Colour] = None,
        footers: Optional[list[dict[str, str]]] | dict[str, str] | None = None) -> list[Embed]:
    """
    Generates list of embed with {max_fields} number of fields per embed.

    :param author: Embed Author
    :param title: Embed Title
    :param fields: Embed fields {name, value, inline}
    :param max_fields: Number of fields per embed (up to 25)
    :param description: Embed descriptions
    :param colour: Colour of embeds
    :param footers: Embed footers, leave blank for page count
    :return: List of embeds
    """
    embed_list: list[Embed] = [
        Embed(title = title if isinstance(title, str | None) else title[i],
              colour = set_colour(colour),
              description = None if not description else description[i],
              timestamp = utcnow())
        for i in range(0, max(ceil(len(fields) / max_fields), 1))
    ]
    field_index = 0
    for index, embed in enumerate(embed_list):
        while len(embed.fields) < min(len(fields), max_fields) and field_index < len(fields):
            field = fields[field_index]
            if field.index:
                embed.insert_field_at(index = field.index, name = field.name, value = field.value, inline = field.inline)
            else:
                embed.add_field(name = field.name, value = field.value, inline = field.inline)
            field_index += 1
        if author:
            embed.set_author(name = author.get("name"), url = author.get("url"), icon_url = author.get("icon_url"))
        if not footers:
            embed.set_footer(text = f"Page {index + 1} of {len(embed_list)}")
        elif isinstance(footers, list):
            embed.set_footer(text = footers[index].get("text"), icon_url = footers[index].get("icon_url"))
        else:
            embed.set_footer(text = footers.get("text"), icon_url = footers.get("icon_url"))
    return embed_list


def SimpleEmbedList(author: Optional[dict[str, str]] = None,
                    title: Optional[list[str] | str] = None,
                    descriptions: list[str] | str = MISSING,
                    image: Optional[list[str] | str] = None,
                    thumbnail: Optional[list[str] | str] = None,
                    colour: Optional[Colour] = None,
                    footer: Optional[list[dict[str, str]] | dict[str, str]] = None) -> list[Embed]:
    """
    Generates a list of embeds with only the description field filled

    :param author: Embed Author: Optional dict{name: ..., url: ..., icon_url: ...}
    :param title: Embed title/titles: list[str] | str
    :param descriptions: List of descriptions, up to 4k characters each or string that will be split automatically
    :param image: image url(s): list[str] | str
    :param thumbnail: image thumbnail(s): list[str] | str
    :param colour: Colour of embed: discord.Colour
    :param footer: Embed footer(s): Optional list[dict] | dict{name: ..., url: ..., icon_url: ...}
    :return: List of embeds
    """
    if isinstance(descriptions, str):
        descriptions = [descriptions[i: i + 4000] for i in range(0, len(descriptions), 4000)]
    embed_list: list[Embed] = [
        Embed(
            title = title if isinstance(title, str | None) else title[index],
            description = description[:4000],
            colour = set_colour(colour)
        ) for index, description in enumerate(descriptions)
    ]
    if author:
        for embed in embed_list:
            set_author(embed, author)
    if image:
        if isinstance(image, list):
            for embed, img in zip(embed_list, image):
                set_image(embed, img)
        else:
            for embed in embed_list:
                set_image(embed, image)
    if thumbnail:
        if isinstance(thumbnail, list):
            for embed, img in zip(embed_list, thumbnail):
                set_thumbnail(embed, img)
        else:
            for embed in embed_list:
                set_thumbnail(embed, thumbnail)
    if footer:
        if isinstance(footer, list):
            for embed, ftr in zip(embed_list, footer):
                set_footer(embed, ftr)
        else:
            for embed in embed_list:
                set_footer(embed, footer)

    return embed_list


OPTIONAL_FIELDS = {"author": set_author,
                   "footer": set_footer,
                   "image": set_image,
                   "thumbnail": set_thumbnail
                   }
