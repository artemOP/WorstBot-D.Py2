import discord
from typing import Optional
from . import Errors

async def role_create(guild: discord.Guild, **kwargs) -> discord.Role:
    """Create a role in the provided guild with builtin eh
    :param guild:
    :param kwargs:
        name: str = MISSING,
        permissions: Permissions = MISSING,
        colour: Colour | int = MISSING,
        color: Colour | int = MISSING,
        hoist: bool = MISSING,
        display_icon: bytes | str | None = MISSING,
        mentionable: bool = MISSING,
        reason: str | None = MISSING
    """
    try:
        return await guild.create_role(**kwargs)
    except discord.Forbidden as e:
        raise Errors.ManageRoles(original_error = e, guild = guild, text = 'WorstBot failed to create a role due to missing the "manage roles" permission')

async def role_add(member: discord.Member, role: discord.Role, reason: Optional[str] = None) -> None:
    """Add role to given member with builtin eh

    :param member: Member to apply to
    :param role: Role to apply
    :param reason: Audit log reason
    """
    try:
        await member.add_roles(role, reason = reason or "WorstBot Added A Role")
    except discord.Forbidden as e:
        raise Errors.ManageRoles(original_error = e, guild = member.guild, text = 'WorstBot failed to add a role due to missing the "manage roles" permission')

async def role_remove(member: discord.Member, role: discord.Role, reason: Optional[str] = None) -> None:
    """Remove role from given member with builtin eh

        :param member: Member to remove from
        :param role: Role to remove
        :param reason: Audit log reason
        """
    try:
        await member.remove_roles(role, reason = reason or "WorstBot Removed A Role")
    except discord.Forbidden as e:
        raise Errors.ManageRoles(original_error = e, guild = member.guild, text = 'WorstBot failed to remove a role due to missing the "manage roles" permission')

async def role_edit(role: discord.Role, **kwargs) -> discord.Role:
    """Edit a role with builtin eh

    :param role: R
    :param kwargs:
        name: str = MISSING,
        permissions: Permissions = MISSING,
        colour: Colour | int = MISSING,
        color: Colour | int = MISSING,
        hoist: bool = MISSING,
        display_icon: bytes | str | None = MISSING,
        mentionable: bool = MISSING,
        position: int = MISSING,
        reason: str | None = MISSING
    """
    try:
        return await role.edit(**kwargs)
    except discord.Forbidden as e:
        raise Errors.ManageRoles(original_error = e, guild = role.guild, text = 'WorstBot failed to edit a role due to missing the "manage roles" permission')

async def role_delete(role: discord.Role, reason: str = None) -> None:
    """Delete a role with builtin eh

    :param role:
    :param reason:
    """
    try:
        await role.delete(reason = reason)
    except discord.Forbidden as e:
        raise Errors.ManageRoles(original_error = e, guild = role.guild, text = 'WorstBot failed to delete a role due to missing the "manage roles" permission')
