import discord
from typing import Optional
from . import Errors

async def role_add(member: discord.Member, role: discord.Role, reason: Optional[str] = None) -> None:
    """
    Add role to given member

    :param member:
    :param role:
    :param reason:
    :return: success bool
    """
    try:
        await member.add_roles(role, reason = reason or "WorstBot Added A Role")
    except discord.Forbidden as e:
        raise Errors.ManageRoles(original_error = e, message = 'WorstBot failed to add a role due to missing the "manage roles" permission')

async def role_remove(member: discord.Member, role: discord.Role, reason: Optional[str] = None) -> None:
    """
        Remove role from given member

        :param member:
        :param role:
        :param reason:
        :return: success bool
        """
    try:
        await member.remove_roles(role, reason = reason or "WorstBot Removed A Role")
    except discord.Forbidden as e:
        raise Errors.ManageRoles(original_error = e, message = 'WorstBot failed to remove a role due to missing the "manage roles" permission')
