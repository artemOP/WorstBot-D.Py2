import discord
from discord.utils import MISSING
from discord.ext import commands
from typing import Optional
from datetime import datetime as dt

class CodeBlock:
    """
        Returns codeblock in the format of:
        ```{language}
        code
        ```
    """
    def __init__(self, language: str = "py", code: str = MISSING):
        self._codeblock = f"```{language}\n{code}```"

    def __str__(self) -> str:
        return self._codeblock

def to_int(x: str | float | bytes, base: Optional[int] = 10) -> int:
    """
    Attempts to convert to int, returns 0 on error

    :param x: string, float or bytes input
    :param base: default base10
    :return: integer | 0
    """
    try:
        return int(x, base)
    except ValueError:
        return 0


def to_percent(number: int | float, total: int | float, precision: Optional[int] = 0) -> int | float:
    """
    converts fraction to percent (number only)

    :param number: numerator
    :param total: denominator
    :param precision: Optional decimal places
    :return: percent (number only)
    """
    try:
        return round((number / total) * 100, precision)
    except TypeError:
        return 0


def to_datetime(date_str: str, date_format: str) -> dt | None:
    """
    converts date string to datetime object

    :param date_str: raw date
    :param date_format: format of date_str
    :return: datetime object (None on error)
    """
    try:
        return dt.strptime(date_str, date_format)
    except (ValueError, TypeError):
        return None

def to_command_mention(command: commands.Command, guild: discord.Guild) -> str:
    mention_str = command.extras.get(f"mention for {guild.id}")
    if not mention_str:
        mention_str = command.extras.get("mention", "None")
    return mention_str or "None"

# todo: integrate ErrorHandler.py
