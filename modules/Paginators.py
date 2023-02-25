import discord
from discord import Interaction, ButtonStyle
from io import BytesIO

class BaseView(discord.ui.View):
    def __init__(self, timeout):
        super().__init__(timeout = timeout)
        self.response: discord.InteractionMessage | None = None

    async def on_timeout(self) -> None:
        if not self.response:
            raise AttributeError("A response must be provided for the view to timeout")
        await self.response.edit(view = None)

    async def interaction_check(self, interaction: Interaction, /) -> bool:
        if self.response.interaction.user != interaction.user:
            await interaction.response.send_message(f"This is not your view, please launch your own", ephemeral = True)
            return False
        return True

class ButtonPaginatedEmbeds(BaseView):
    def __init__(self, embed_list, timeout = 30):
        super().__init__(timeout = timeout)
        self.embedlist = embed_list or [discord.Embed()]
        self.pages = [discord.SelectOption(label = f"Page {i+1}", value = str(i)) for i in range(0, len(embed_list))]
        self.page_select.options = self.pages[:25]
        self.page = 0

    @discord.ui.button(label = 'First page', style = ButtonStyle.red)
    async def first(self, interaction: Interaction, button: discord.ui.Button):
        self.page = 0
        self.page_select.options = self.pages[max(self.page - 12, 0): min(self.page + 12, len(self.pages))]
        await interaction.response.edit_message(embed = self.embedlist[0], view = self)

    @discord.ui.button(label = 'Previous page', style = ButtonStyle.red)
    async def previous(self, interaction: Interaction, button: discord.ui.Button):
        if self.page >= 1:
            self.page -= 1
        else:
            self.page = len(self.embedlist) - 1
        self.page_select.options = self.pages[max(self.page - 12, 0): min(self.page + 12, len(self.pages))]
        await interaction.response.edit_message(embed = self.embedlist[self.page], view = self)

    @discord.ui.button(label = 'Stop', style = ButtonStyle.grey)
    async def exit(self, interaction: Interaction, button: discord.ui.Button):
        await self.on_timeout()

    @discord.ui.button(label = 'Next Page', style = ButtonStyle.green)
    async def next(self, interaction: Interaction, button: discord.ui.Button):
        self.page += 1
        if self.page > len(self.embedlist) - 1:
            self.page = 0
        self.page_select.options = self.pages[max(self.page - 12, 0): min(self.page + 12, len(self.pages))]
        await interaction.response.edit_message(embed = self.embedlist[self.page], view = self)

    @discord.ui.button(label = 'Last Page', style = ButtonStyle.green)
    async def last(self, interaction: Interaction, button: discord.ui.Button):
        self.page = len(self.embedlist) - 1
        self.page_select.options = self.pages[max(self.page - 12, 0): min(self.page + 12, len(self.pages))]
        await interaction.response.edit_message(embed = self.embedlist[self.page], view = self)

    @discord.ui.select(placeholder = "Page Select")
    async def page_select(self, interaction: Interaction, select: discord.ui.Select):
        self.page = int(select.values[0])
        self.page_select.options = self.pages[max(self.page - 12, 0): min(self.page + 12, len(self.pages))]
        await interaction.response.edit_message(embed = self.embedlist[self.page], view = self)

class ThemedGraphView(BaseView):
    """
    Handles Light and dark theme text for graphs, provide "Light" and "Dark" keys with plots
    """
    def __init__(self, graphs: dict[str, BytesIO], timeout: int = 30):
        super().__init__(timeout = timeout)
        self.graphs = graphs

    @discord.ui.select(placeholder = "Theme select", options = [discord.SelectOption(label = "Light"), discord.SelectOption(label = "Dark")])
    async def Select(self, interaction: Interaction, select: discord.ui.Select):
        await interaction.response.edit_message(attachments = [discord.File(fp = self.graphs[select.values[0]], filename = "image.png")])
        self.graphs[select.values[0]].seek(0)
