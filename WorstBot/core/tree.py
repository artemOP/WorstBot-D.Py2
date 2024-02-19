from __future__ import annotations

from typing import TYPE_CHECKING, overload

from discord import app_commands, AppCommandType

if TYPE_CHECKING:
    from discord import Interaction
    from discord.ext import commands
    from discord.abc import Snowflake

    from .bot import Bot


class CommandTree(app_commands.CommandTree):
    def __init__(self, bot: Bot):
        super().__init__(bot)

    async def interaction_check(self, interaction: Interaction[Bot], /) -> bool:
        assert interaction.client.owner_ids
        if interaction.user.id in interaction.client.owner_ids:
            return True
        if not interaction.guild:
            await interaction.response.send_message("This bot cannot be used in dm's, sorry", ephemeral=True)
            return False
        return True

    def get_command(
        self,
        command_name: str,
        /,
        *,
        guild: Snowflake | None = None,
        type: AppCommandType = AppCommandType.chat_input,
    ) -> app_commands.Command | app_commands.ContextMenu | app_commands.Group | None:
        command = super().get_command(command_name, guild=guild, type=type)
        if not command:
            command = super().get_command(command_name, guild=None, type=type)
        return command

    def get_commands(
        self,
        *,
        guild: Snowflake | None = None,
        type: AppCommandType | None = None,
    ) -> list[app_commands.Command | app_commands.ContextMenu | app_commands.Group]:
        guild_commands = super().get_commands(guild=guild, type=type)
        global_commands = super().get_commands(guild=None, type=type)
        for global_command in global_commands:
            if global_command.name not in [guild_command.name for guild_command in guild_commands]:
                guild_commands.append(global_command)
        return guild_commands

    @overload
    @staticmethod
    def flatten_commands(
        command_list: list[app_commands.Command | app_commands.Group],
    ) -> list[app_commands.Command]: ...

    @overload
    @staticmethod
    def flatten_commands(
        command_list: list[commands.Command | commands.Group],
    ) -> list[commands.Command]: ...

    @staticmethod
    def flatten_commands(
        command_list: list[app_commands.Command | app_commands.Group] | list[commands.Command | commands.Group],
    ) -> list[app_commands.Command] | list[commands.Command]:
        flat_commands = []
        for command in command_list:
            if isinstance(command, app_commands.Command | commands.Command):
                flat_commands.append(command)
                continue

            for child in command.walk_commands():
                flat_commands.append(child)

        return flat_commands
