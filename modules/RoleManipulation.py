import discord
from typing import Optional

async def role_add(member: discord.Member, role: discord.Role, reason: Optional[str] = None) -> bool:
    """
    Add role to given member

    :param member:
    :param role:
    :param reason:
    :return: success bool
    """
    try:
        await member.add_roles(role, reason = reason or "WorstBot Added A Role")
        return True
    except discord.Forbidden | discord.HTTPException:
        return False

async def role_remove(member: discord.Member, role: discord.Role, reason: Optional[str] = None) -> bool:
    """
        Remove role from given member

        :param member:
        :param role:
        :param reason:
        :return: success bool
        """
    try:
        await member.remove_roles(role, reason = reason or "WorstBot Removed A Role")
        return True
    except discord.Forbidden | discord.HTTPException:
        return False