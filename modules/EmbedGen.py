import discord
from discord import Embed, Colour
from discord.utils import MISSING, utcnow
from itertools import islice
from typing import Optional
from math import ceil
from pydantic import BaseModel, conint, constr, Field

class EmbedField(BaseModel):
    index: conint(ge = 1, le = 25) = Field(default = None)
    name: constr(min_length = 1, curtail_length = 256)
    value: constr(min_length = 1, curtail_length = 1024)
    inline: bool = Field(default = True)

def SimpleEmbed(title: Optional[str] = None, text: str = None, colour: Colour = Colour.random()) -> Embed:
    """
    Generates a simple embed with only the description field

    :param title: Embed Title
    :param text: Embed Description
    :param colour: Embed Colour
    :return: Discord Embed
    """
    return Embed(title = title, description = text[:4000], colour = colour, timestamp = utcnow())


def FullEmbed(
        author: Optional[dict[str, str]] = None,
        title: Optional[str] = None,
        fields: list[EmbedField] = MISSING,
        description: Optional[str] = None,
        colour: Optional[Colour] = Colour.random(),
        footer: Optional[dict[str, str]] = None) -> Embed:
    """
    Generates an embed with up to 25 title: value fields plus description field.

    :param author: Embed Author
    :param title: Embed Title
    :param fields: list of embed fields
    :keyword field: Object containing mandatory name, value. Optional inline, index
    :param description: Embed description
    :param colour: Embed colour
    :param footer: Embed Footer
    :return: Discord Embed
    """
    embed = Embed(title = title, colour = colour, description = description, timestamp = utcnow())
    for field in islice(fields, 25):
        if field.index:
            embed.insert_field_at(index = field.index, name = field.name, value = field.value, inline = field.inline)
        else:
            embed.add_field(name = field.name, value = field.value, inline = field.inline)
    if isinstance(author, dict):
        embed.set_author(name = author.get("name"), url = author.get("url"), icon_url = author.get("icon_url"))
    if isinstance(footer, dict):
        embed.set_footer(text = footer.get("text"), icon_url = footer.get("icon_url"))

    return embed


def EmbedFieldList(
        author: Optional[dict[str, str]] = None,
        title: Optional[list[str] | str] = None,
        fields: list[EmbedField] = MISSING,
        max_fields: Optional[int] = 25,
        description: Optional[list[str]] = None,
        colour: Optional[Colour] = Colour.random(),
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
              colour = colour,
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
                    colour: Optional[Colour] = Colour.random(), ) -> list[Embed]:
    """
    Generates a list of embeds with only the description field filled

    :param author: Embed Author
    :param title: Embed title/titles
    :param descriptions: List of descriptions, up to 4k characters each or string that will be split automatically
    :param colour: Colour of embed
    :return: List of embeds
    """
    if isinstance(descriptions, str):
        descriptions = [descriptions[i: i + 4000] for i in range(0, len(descriptions), 4000)]
    embed_list: list[Embed] = [
        Embed(
            title = title if isinstance(title, str | None) else title[index],
            description = description[:4000],
            colour = colour
        ) for index, description in enumerate(descriptions)
    ]
    if author:
        for embed in embed_list:
            embed.set_author(name = author.get("name"), url = author.get("url"), icon_url = author.get("icon_url"))
    return embed_list
# todo: migrate on to these functions
