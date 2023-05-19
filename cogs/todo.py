from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from enum import StrEnum, auto
from typing import Optional, Any
from collections.abc import Mapping

import discord
from discord import Interaction, app_commands, ui, ButtonStyle
from discord.ext import commands, tasks
from discord.utils import MISSING, format_dt, utcnow
from rapidfuzz import process

from WorstBot import WorstBot
from modules import EmbedGen, Paginators, Constants

BooleanColours = {True: discord.ButtonStyle.green, False: discord.ButtonStyle.red}


class TodoStatus(StrEnum):
    on_going = auto()
    completed = auto()
    overdue = auto()
    expired = auto()
    cancelled = auto()


@dataclass(slots = True)
class TodoFlags:
    locked: bool = False
    urgent: bool = False
    silent: bool = False


@dataclass(slots = True)
class Todo(Mapping):
    owner: discord.User = MISSING
    guild: Optional[discord.Guild] = None
    message: Optional[discord.PartialMessage] = None
    id_: int = MISSING
    name: str = MISSING
    content: str = MISSING
    deadline: Optional[datetime] = None
    status: TodoStatus = TodoStatus.on_going
    flags: TodoFlags = MISSING
    view_message_id: int = None

    def __post_init__(self):
        for key in self.__slots__:
            if getattr(self, key) is MISSING:
                raise NotImplementedError(f"{key} should not be MISSING")

    def __getitem__(self, item) -> Optional[Any]:
        return getattr(self, item, None)

    def __len__(self) -> int:
        return len(self.__slots__)

    def __iter__(self) -> Any:
        for attr in self.__slots__:
            yield attr


def create_embed(todo: Todo) -> discord.Embed:
    return EmbedGen.SimpleEmbed(
        author = {"name": todo.owner.display_name, "icon_url": todo.owner.display_avatar},
        title = f"{todo.name}: {'' if not todo.deadline else format_dt(todo.deadline, 'R')}",
        text = todo.content
    )


class CreateTodo(ui.Modal):
    def __init__(self, title, todo_id: Optional[int] = None, message: Optional[discord.PartialMessage] = None, todo_name: Optional[str] = None, todo_content: Optional[str] = None, deadline: Optional[datetime] = None, flags: Optional[TodoFlags] = None):
        super().__init__(title = title)
        self.todo_id = todo_id
        self.message = message
        self.deadline = deadline
        self.flags = flags or TodoFlags()
        self.todo_name = ui.TextInput(
            label = "TODO Name",
            placeholder = "Enter your TODO title here:",
            default = todo_name,
            required = True,
            max_length = 100
        )
        self.todo_content = ui.TextInput(
            label = "TODO Content",
            placeholder = "Enter your TODO content here:",
            default = todo_content,
            required = True,
            max_length = 1000,
            style = discord.TextStyle.long
        )

        self.add_item(self.todo_name)
        self.add_item(self.todo_content)

    async def on_submit(self, interaction: Interaction, /) -> None:
        if self.todo_id:
            await interaction.client.execute("UPDATE todo SET name=$1, content=$2 WHERE todo_id = $3", self.todo_name.value, self.todo_content.value, self.todo_id)
        else:
            self.todo_id = await interaction.client.execute("INSERT INTO todo(guild, channel, owner, message, name, content, status) VALUES($1, $2, $3, $4, $5, $6, 'on_going') RETURNING todo_id", interaction.guild_id, interaction.channel_id, interaction.user.id, getattr(self.message, "id", None), self.todo_name.value, self.todo_content.value)
        todo = Todo(interaction.user, interaction.guild, self.message, self.todo_id, self.todo_name.value, self.todo_content.value, self.deadline, TodoStatus.on_going, self.flags)
        view = TodoMenu(todo)
        await interaction.response.send_message(view = view, embed = create_embed(todo), ephemeral = True)
        view.response = await interaction.original_response()


class SetDeadline(ui.Modal):
    def __init__(self, todo: Todo):
        super().__init__(title = "Set Deadline")
        self.todo = todo
        deadline = todo.deadline or utcnow()
        self.year = ui.TextInput(
            label = "Deadline Year",
            placeholder = "Enter the deadline year",
            default = str(deadline.year),
            required = False,
            max_length = 4
        )
        self.month = ui.TextInput(
            label = "Deadline Month",
            placeholder = "Enter the deadline month",
            default = str(deadline.month),
            required = False,
            max_length = 2
        )
        self.day = ui.TextInput(
            label = "Deadline Day",
            placeholder = "Enter the deadline day",
            default = str(deadline.day),
            required = False,
            max_length = 2
        )
        self.hour = ui.TextInput(
            label = "Deadline Hour",
            placeholder = "Enter the deadline hour",
            default = str(deadline.hour),
            required = False,
            max_length = 2
        )
        self.minute = ui.TextInput(
            label = "Deadline Minute",
            placeholder = "Enter the deadline minute",
            default = str(deadline.minute),
            required = False,
            max_length = 2
        )
        for item in [self.year, self.month, self.day, self.hour, self.minute]:
            self.add_item(item)

    async def on_submit(self, interaction: Interaction, /) -> None:
        if all((self.year.value, self.month.value, self.day.value, self.hour.value, self.minute.value)):
            try:
                self.todo.deadline = datetime(int(self.year.value), int(self.month.value), int(self.day.value), int(self.hour.value), int(self.minute.value), tzinfo = timezone.utc)
            except ValueError:
                return await interaction.response.send_message("Invalid deadline set, please try again", ephemeral = True)
        else:
            self.todo.deadline = None
        await interaction.client.execute("UPDATE todo SET deadline=$1 WHERE todo_id=$2", self.todo.deadline, self.todo.id_)
        view = TodoMenu(self.todo)
        await interaction.response.send_message(view = view, embed = create_embed(self.todo), ephemeral = True)
        view.response = await interaction.original_response()


class TodoMenu(Paginators.BaseView):
    def __init__(self, todo: Todo):
        super().__init__(timeout = 300)
        self.todo = todo

        self.toggle_deadline.style = BooleanColours[not bool(self.todo.deadline)]
        self.toggle_deadline.label = "Add deadline" if not self.todo.deadline else "Remove deadline"

        self.mark_complete.disabled = True if self.todo.status is TodoStatus.completed else False

        previous = ui.Button(label = "previous TODO", row = 0, style = discord.ButtonStyle.red)
        next_ = ui.Button(label = "next TODO", row = 0, style = discord.ButtonStyle.green)
        previous.callback = self.previous_todo
        next_.callback = self.next_todo
        self.add_item(previous)
        if self.todo.message:
            jump_link = ui.Button(label = "Go To", row = 0, url = self.todo.message.jump_url)
            self.add_item(jump_link)
        self.add_item(next_)

    async def form_todo(self, interaction: Interaction, row):
        if not row:
            return await interaction.response.defer()
        todo = Todo(
            owner = interaction.user,
            message = row.get("message"),
            id_ = row.get("todo_id"),
            name = row.get("name"),
            content = row.get("content"),
            deadline = row.get("deadline"),
            status = TodoStatus[row.get("status")],
            flags = TodoFlags(row.get("locked"), row.get("urgent"), row.get("silent"))
        )
        self.todo = todo
        embed = create_embed(todo)
        self.mark_complete.disabled = True if self.todo.status is TodoStatus.completed else False
        await interaction.response.edit_message(embed = embed, view = self)

    async def previous_todo(self, interaction: Interaction):
        row = await interaction.client.fetchrow("SELECT todo_id, message, name, content, deadline, status, locked, urgent, silent FROM todo WHERE todo_id<$1 AND owner=$2 AND status!='cancelled' ORDER BY todo_id DESC LIMIT 1", self.todo.id_, interaction.user.id)
        await self.form_todo(interaction, row)

    async def next_todo(self, interaction: Interaction):
        row = await interaction.client.fetchrow("SELECT todo_id, message, name, content, deadline, status, locked, urgent, silent FROM todo WHERE todo_id>$1 AND owner=$2 AND status!='cancelled' ORDER BY todo_id LIMIT 1", self.todo.id_, interaction.user.id)
        await self.form_todo(interaction, row)

    @ui.button(label = "Edit", row = 1)
    async def edit_todo(self, interaction: Interaction, button: ui.Button):
        if self.todo.flags.locked is True:
            return await interaction.response.send_message("This TODO is locked, please unlock to edit")
        self.stop()
        await self.response.delete()
        await interaction.response.send_modal(CreateTodo(title = "Edit TODO", todo_id = self.todo.id_, message = self.todo.message, todo_name = self.todo.name, todo_content = self.todo.content))

    @ui.button(row = 1)
    async def toggle_deadline(self, interaction: Interaction, button: ui.Button):
        if self.todo.flags.locked is True:
            return await interaction.response.send_message("This TODO is locked, please unlock to edit")
        await interaction.response.send_modal(SetDeadline(self.todo))
        self.stop()
        await self.response.delete()

    @ui.button(label = "Edit Flags", row = 1)
    async def edit_flags(self, interaction: Interaction, button: ui.Button):
        view = SetFlags(self.todo)
        await interaction.response.send_message(view = view, ephemeral = True)
        view.response = await interaction.original_response()

    @ui.button(label = "Close", row = 2, style = discord.ButtonStyle.red)
    async def close(self, interaction: Interaction, button: ui.Button):
        self.stop()
        await self.response.delete()

    @ui.button(label = "Mark Completed", row = 2, style = discord.ButtonStyle.green)
    async def mark_complete(self, interaction: Interaction, button: ui.Button):
        if self.todo.flags.locked is True:
            return await interaction.response.send_message("This TODO is locked, please unlock to edit", ephemeral = True)
        self.todo.status = TodoStatus.completed
        await interaction.client.execute("UPDATE todo SET status='completed' WHERE todo_id=$1", self.todo.id_)
        button.disabled = True
        await interaction.response.edit_message(view = self)


class SetFlags(Paginators.BaseView):
    def __init__(self, todo: Todo):
        super().__init__(timeout = 60)
        self.todo = todo
        for child in self.children:  # type: ui.Button
            child.style = BooleanColours[getattr(todo.flags, child.label.lower())]

    async def on_timeout(self) -> None:
        await self.response.delete()

    @ui.button(label = "Locked", style = discord.ButtonStyle.red)
    async def set_locked(self, interaction: Interaction, button: ui.Button):
        await self.update_flag(interaction, button)

    @ui.button(label = "Urgent", style = discord.ButtonStyle.red)
    async def set_urgent(self, interaction: Interaction, button: ui.Button):
        await self.update_flag(interaction, button)

    @ui.button(label = "Silent", style = discord.ButtonStyle.red)
    async def set_silent(self, interaction: Interaction, button: ui.Button):
        await self.update_flag(interaction, button)

    async def update_flag(self, interaction: Interaction, button: ui.Button):
        setattr(self.todo.flags, button.label.lower(), not getattr(self.todo.flags, button.label.lower()))
        await interaction.client.execute("UPDATE todo SET locked=$2, urgent=$3, silent=$4 WHERE todo_id=$1", self.todo.id_, *asdict(self.todo.flags).values())
        button.style = BooleanColours[getattr(self.todo.flags, button.label.lower())]
        await interaction.response.edit_message(view = self)


class TodoList(Paginators.ButtonPaginatedEmbeds):
    def __init__(self, embed_list: list[EmbedGen.Embed]):
        super().__init__(timeout = 60, embed_list = embed_list)
        self.open_todo.options = [discord.SelectOption(label = todo.name, value = index) for index, todo in self.embedlist[self.page].extras.items()]

    @ui.select(placeholder = "Open Todo")
    async def open_todo(self, interaction: Interaction, select: ui.Select):
        todo = self.embedlist[self.page].extras[int(select.values[0])]
        view = TodoMenu(todo)
        await interaction.response.send_message(view = view, embed = create_embed(todo), ephemeral = True)
        view.response = await interaction.original_response()

    @discord.ui.button(label = 'First page', style = ButtonStyle.red)
    async def first(self, interaction: Interaction, button: discord.ui.Button):
        await super().first(interaction, button)
        self.open_todo.options = [discord.SelectOption(label = todo.name, value = index) for index, todo in self.embedlist[self.page].extras.items()]
        await interaction.edit_original_response(view = self)

    @discord.ui.button(label = 'Previous page', style = ButtonStyle.red)
    async def previous(self, interaction: Interaction, button: discord.ui.Button):
        await super().previous(interaction, button)
        self.open_todo.options = [discord.SelectOption(label = todo.name, value = index) for index, todo in self.embedlist[self.page].extras.items()]
        await interaction.edit_original_response(view = self)

    @discord.ui.button(label = 'Next Page', style = ButtonStyle.green)
    async def next(self, interaction: Interaction, button: discord.ui.Button):
        await super().next(interaction, button)
        self.open_todo.options = [discord.SelectOption(label = todo.name, value = index) for index, todo in self.embedlist[self.page].extras.items()]
        await interaction.edit_original_response(view = self)

    @discord.ui.button(label = 'Last Page', style = ButtonStyle.green)
    async def last(self, interaction: Interaction, button: discord.ui.Button):
        await super().last(interaction, button)
        self.open_todo.options = [discord.SelectOption(label = todo.name, value = index) for index, todo in self.embedlist[self.page].extras.items()]
        await interaction.edit_original_response(view = self)

    @discord.ui.select(placeholder = "Page Select")
    async def page_select(self, interaction: Interaction, select: discord.ui.Select):
        await super().page_select(interaction, select)
        self.open_todo.options = [discord.SelectOption(label = todo.name, value = index) for index, todo in self.embedlist[self.page].extras.items()]
        await interaction.edit_original_response(view = self)

class TodoReminder(Paginators.BaseView):
    def __init__(self, todo: Todo):
        super().__init__(timeout = None)
        self.todo = todo
        self.mark_complete.custom_id = f"reminder:{todo.id_}"

    @ui.button(label = "Mark Complete", style = ButtonStyle.green)
    async def mark_complete(self, interaction: Interaction, button: ui.Button):
        self.todo.status = TodoStatus.completed
        await interaction.client.execute("UPDATE todo SET status='completed' WHERE todo_id=$1", self.todo.id_)
        button.disabled = True
        self.stop()
        await interaction.response.edit_message(view = self, content = f"{self.todo.name} has been marked as completed")

@app_commands.default_permissions()
class Todos(commands.GroupCog, name = "todo"):

    def __init__(self, bot: WorstBot):
        self.bot = bot
        self.context_menu = None
        self.todos: dict[int: list[Todo]] = {}  # {user_id: {todo_id: Todo_}}
        self.reminders = []
        self.logger = self.bot.logger.getChild(self.qualified_name)

    async def cog_load(self) -> None:
        if not await self.bot.execute("SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'todo_status')"):
            await self.bot.execute(f"""CREATE TYPE todo_status as ENUM ({', '.join(f"'{status}'" for status in TodoStatus.__members__.values())})""")
        await self.bot.execute("CREATE TABLE IF NOT EXISTS todo(todo_id SERIAL PRIMARY KEY, guild BIGINT, channel BIGINT, owner BIGINT, message BIGINT, name TEXT, content TEXT, status todo_status, deadline timestamptz, locked bool DEFAULT FALSE, urgent bool DEFAULT FALSE, silent bool DEFAULT FALSE, view_message BIGINT)")
        self.context_menu = app_commands.ContextMenu(name = "Add to TODO list", callback = self.todo_add_context, type = discord.AppCommandType.message)
        self.bot.tree.add_command(self.context_menu)
        self.todos = {}
        self.ReminderTask.start()
        self.prepare_views.start()
        self.logger.info(f"{self.qualified_name} cog loaded")

    async def cog_unload(self) -> None:
        self.ReminderTask.stop()
        self.bot.tree.remove_command(self.Context_menu)
        del self.todos
        for view in self.todos:  # type: ui.View
            view.stop()
        self.logger.info(f"{self.qualified_name} cog unloaded")

    @tasks.loop(count = 1)
    async def prepare_views(self):
        todo_rows = await self.bot.fetch("SELECT todo_id, owner FROM todo WHERE status='expired' OR (status='overdue' AND view_message IS NOT NULL)")
        for row in todo_rows:
            owner = await self.bot.maybe_fetch_user(row["owner"])
            todo = await self.get_todo(owner, row["todo_id"])
            view = TodoReminder(todo)
            self.reminders.append(view)
            self.bot.add_view(view, message_id = todo.view_message_id)

    @prepare_views.before_loop
    async def prepare_view_before(self):
        await self.bot.wait_until_ready()

    async def get_todo(self, owner: discord.User, todo_id: int) -> Optional[Todo]:
        if not self.todos.get(owner.id):
            self.todos[owner.id] = {}
        if todo := self.todos[owner.id].get(todo_id):
            return todo
        row = await self.bot.fetchrow("SELECT todo_id, guild, channel, owner, message, name, content, status, deadline, locked, urgent, silent, view_message FROM todo WHERE owner=$1 AND todo_id=$2", owner.id, todo_id)
        guild = self.bot.get_guild(row.get("guild"))
        channel = self.bot.get_partial_messageable(row.get("channel"), guild_id = row.get("guild"))
        message = channel.get_partial_message(row["message"])
        flags = TodoFlags(row.get("locked"), row.get("urgent"), row.get("silent"))
        status = TodoStatus[row.get("status")]
        todo = Todo(owner, guild, message, todo_id, row.get("name"), row.get("content"), row.get("deadline"), status, flags, row.get("view_message"))
        self.todos[owner.id][todo_id] = todo
        return todo

    @app_commands.command(name = "add")
    async def todo_add_command(self, interaction: Interaction):
        """Launch a modal to create a TODO"""
        await interaction.response.send_modal(CreateTodo(title = "Create TODO"))

    async def todo_add_context(self, interaction: Interaction, message: discord.Message):
        """Launch a modal to create a TODO based on a message"""
        await interaction.response.send_modal(CreateTodo(title = "Create TODO", message = message, todo_name = str(message.author), todo_content = message.content))

    @app_commands.command(name = "edit")
    async def todo_edit(self, interaction: Interaction, todo: int):
        """Relaunch a modal to edit a TODO

        :param interaction:
        :param todo: The TODO to edit
        """
        todo = await self.get_todo(interaction.user, todo)
        await interaction.response.send_modal(CreateTodo(title = "Edit TODO", todo_id = todo.id_, message = todo.message, todo_name = todo.name, todo_content = todo.content))

    @app_commands.command(name = "remove")
    async def todo_remove(self, interaction: Interaction, todo: int):
        """Cancel a TODO

        :param interaction:
        :param todo: The TODO to cancel
        """
        await self.bot.execute("UPDATE todo SET status = 'cancelled' WHERE todo_id = $1", todo)
        await interaction.response.send_message("TODO marked as 'cancelled'", ephemeral = True)

    @app_commands.command(name = "view")
    async def todo_view(self, interaction: Interaction, todo: int):
        """View a selected TODO

        :param interaction:
        :param todo: The TODO to view
        """
        todo = await self.get_todo(interaction.user, todo)
        view = TodoMenu(todo)
        await interaction.response.send_message(view = view, embed = create_embed(todo), ephemeral = True)
        view.response = await interaction.original_response()

    @app_commands.command(name = "list")
    async def todo_list(self, interaction: Interaction, status: Optional[TodoStatus] = None):
        """List out all of your TODOs

        :param interaction:
        :param status: Optionally select the status of the TODOS to view
        """
        await interaction.response.defer(ephemeral = True)
        if status:
            todos = await self.bot.fetch("SELECT todo_id FROM todo WHERE owner=$1 AND status=$2", interaction.user.id, status.value)
        else:
            todos = await self.bot.fetch("SELECT todo_id FROM todo WHERE owner=$1", interaction.user.id)
        todos = [await self.get_todo(interaction.user, todo["todo_id"]) for todo in todos]
        embed_list = EmbedGen.EmbedFieldList(
            author = {
                "name": interaction.user.display_name,
                "icon_url": interaction.user.display_avatar
            },
            title = "TODOs",
            fields = [
                EmbedGen.EmbedField(
                    name = todo.name,
                    value = f"""
                            status: {todo.status}
                            deadline: {format_dt(todo.deadline, "R") if todo.deadline else "No deadline!"}\n{Constants.BLANK}
                            """,
                    inline = False
                )
                for todo in todos
            ],
            max_fields = 5,
            extras = [todo for todo in todos]
        )
        view = TodoList(embed_list)
        await interaction.followup.send(view = view, embed = embed_list[0], ephemeral = True)
        view.response = await interaction.original_response()

    @todo_edit.autocomplete("todo")
    @todo_remove.autocomplete("todo")
    @todo_view.autocomplete("todo")
    async def todo_autcomplete(self, interaction: Interaction, current: Optional[str]):
        todos = await self.bot.fetch("SELECT todo_id, name FROM todo WHERE owner=$1 AND status='on_going'", interaction.user.id)
        if not current:
            return [app_commands.Choice(name = name, value = todo_id) for todo_id, name in todos][:25]

        fuzzy = process.extract(current, [todo["name"] for todo in todos], limit = 25, score_cutoff = 90)
        fuzzy = [role_name for role_name, _, _ in fuzzy]
        return [app_commands.Choice(name = name, value = todo_id) for todo_id, name in todos if name in fuzzy]

    @tasks.loop(seconds = 5, reconnect = True)
    async def ReminderTask(self):
        row = await self.bot.fetchrow("SELECT todo_id, owner FROM todo WHERE status IN ('on_going', 'overdue') AND deadline IS NOT NULL AND silent is FALSE ORDER BY deadline LIMIT 1")
        if not row:
            return
        owner_id, todo_id = row.get("owner"), row.get("todo_id")

        owner = await self.bot.maybe_fetch_user(owner_id)
        todo = await self.get_todo(owner, todo_id)

        if todo.deadline - utcnow() > timedelta(days = 7):
            return

        todo.status = TodoStatus.overdue
        await self.bot.execute("UPDATE todo SET status=$1 WHERE todo_id=$2", todo.status, todo.id_)
        await discord.utils.sleep_until(todo.deadline)
        embed = create_embed(todo)
        view = TodoReminder(todo)
        message = await owner.send(view = view, embed = embed)
        view.response = message
        if not todo.flags.urgent:
            todo.status = TodoStatus.expired
        else:
            todo.deadline += timedelta(days = 1)
        await self.bot.execute("UPDATE todo SET status=$1, deadline=$2, view_message=$3 WHERE todo_id=$4", todo.status, todo.deadline, message.id, todo.id_)

    @ReminderTask.before_loop
    async def BeforeReminder(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(Todos(bot))
