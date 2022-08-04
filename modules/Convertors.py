import discord
from typing import Optional
from datetime import datetime as dt


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

# todo: integrate ErrorHandler.py
