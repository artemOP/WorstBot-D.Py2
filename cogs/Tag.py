import discord
from discord import Interaction, app_commands, ui, SelectOption
from discord.ext import commands
from modules.EmbedGen import SimpleEmbed, SimpleEmbedList


class TagModal(ui.Modal, title = "tag"):
    def __init__(self, tagid = None, TagName: str = None, TagValue: str = None, nsfw: bool = False, private: bool = False, public: bool = False, invisible: bool = False):
        super().__init__()
        self.tagid = tagid
        self.TagName = ui.TextInput(
            label = "TagName",
            placeholder = "Enter your Tag Name here.",
            required = True,
            min_length = 1,
            max_length = 256,
            default = TagName,
        )
        self.TagValue = ui.TextInput(
            label = "TagValue",
            placeholder = "Enter your Tag Content here",
            required = True,
            min_length = 1,
            max_length = 1024,
            style = discord.TextStyle.long,
            default = TagValue
        )
        self.MetaData = ui.Select(
            placeholder = "Select additional tag data",
            min_values = 0,
            max_values = 4,
            options = [
                SelectOption(label = "NSFW", description = "Marks tag as NSFW", default = nsfw),
                SelectOption(label = "Private", description = "Only allows tag to be used by owner", default = private),
                SelectOption(label = "Invisible", description = "Hides tag user", default = invisible),
                SelectOption(label = "Public", description = "Allows anyone to edit tag", default = public),
            ]
        )
        self.add_item(self.TagName)
        self.add_item(self.TagValue)
        self.add_item(self.MetaData)

    async def on_submit(self, interaction: Interaction) -> None:
        await interaction.response.defer(ephemeral = True)
        Metadata = {}
        for item in self.MetaData.options:
            if item.label in self.MetaData.values:
                Metadata[item.label] = True
            else:
                Metadata[item.label] = False
        if self.tagid:
            await interaction.client.execute(
                "UPDATE tags SET name = $1, value = $2, nsfw = $3, private = $4, invisible = $5, public = $6 WHERE tagid = $7",
                self.TagName.value, self.TagValue.value, *Metadata.values(), self.tagid
            )
        else:
            self.tagid = await interaction.client.execute(
                "INSERT INTO tags(guild, owner, name, value, nsfw, private, invisible, public) VALUES($1, $2, $3, $4, $5, $6, $7, $8) RETURNING tagid",
                interaction.guild_id, interaction.user.id, self.TagName.value, self.TagValue.value, *Metadata.values()
            )
        await interaction.followup.send(f"{self.TagName.value} has been created", ephemeral = True)


class Tag(commands.GroupCog, name = "tag"):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.execute(
            """
            CREATE TABLE IF NOT EXISTS tags(
            tagid SERIAL PRIMARY KEY, 
            guild BIGINT NOT NULL, 
            owner BIGINT NOT NULL, 
            name VARCHAR(256) NOT NULL, 
            value VARCHAR(1024) NOT NULL,
            nsfw BOOLEAN DEFAULT FALSE, 
            private BOOLEAN DEFAULT FALSE, 
            public BOOLEAN DEFAULT FALSE,
            invisible BOOLEAN DEFAULT FALSE 
            )
            """
        )
        print("Tag cog online")

    async def OwnerCheck(self, tagid: int, user: int) -> bool:
        select = await self.bot.fetchrow("SELECT owner, public  FROM tags WHERE tagid = $1", tagid)
        owner, public = select.values()
        return True if owner == user or public else False

    @app_commands.command(name = "create", description = "create a tag to recall later by name")
    async def Create(self, interaction: Interaction):
        await interaction.response.send_modal(TagModal())

    @app_commands.command(name = "edit", description = "edit a pre-exifg by name")
    async def Edit(self, interaction: Interaction, tag: str):
        tag = await self.bot.to_int(tag)
        select = await self.bot.fetchrow("SELECT name, value, nsfw, private, public, invisible FROM tags WHERE tagid = $1", tag)
        if not select:
            return
        name, value, nsfw, private, public, invisible = select.values()
        if not await self.OwnerCheck(tag, interaction.user.id):
            return
        await interaction.response.send_modal(TagModal(tag, name, value, nsfw, private, public, invisible))

    @app_commands.command(name = "rename", description = "Rename a tag")
    async def Rename(self, interaction: Interaction, tag: str, new_name: str):
        tag = await self.bot.to_int(tag)
        if not (tag or await self.OwnerCheck(tag, interaction.user.id)):
            return
        name = await self.bot.fetchval("SELECT name FROM tags WHERE tagid = $1", tag)
        await self.bot.execute("UPDATE tags SET name = $2 WHERE tagid = $1", tag, new_name)
        await interaction.response.send_message(f"{name} has been renamed to {new_name}", ephemeral = True)

    @app_commands.command(name = "delete", description = "Delete a tag by name")
    async def Delete(self, interaction: Interaction, tag: str):
        tag = await self.bot.to_int(tag)
        if not (tag or await self.OwnerCheck(tag, interaction.user.id)):
            return
        name = await self.bot.execute("DELETE FROM tags WHERE tagid = $1 RETURNING name", tag)
        await interaction.response.send_message(f"{name} has been Deleted", ephemeral = True)

    async def ViewHelper(self, tag: str, interaction: Interaction, raw: bool):
        if not (tag := await self.bot.to_int(tag)):
            return
        tag = await self.bot.fetchrow("SELECT owner, name, value, nsfw, private, invisible FROM tags WHERE tagid = $1", tag)
        if tag["private"] and tag["owner"] != interaction.user.id:
            return await interaction.followup.send("Tag is private", ephemeral = True)
        if tag["nsfw"] and not interaction.channel.nsfw:
            return await interaction.followup.send("Tag is NSFW", ephemeral = True)
        owner = self.bot.get_user(tag["owner"])
        embed = SimpleEmbed(author = {"name": str(owner), "icon_url": owner.display_avatar},
                            title = tag["name"],
                            text = tag["value"] if not raw else f"```txt\n{tag['value']}\n```")
        if tag["invisible"]:
            await interaction.followup.send("message sent", ephemeral = True)
            await interaction.channel.send(embed = embed)
        else:
            await interaction.followup.send(embed = embed)

    @app_commands.command(name = "view", description = "View a tag by name")
    async def View(self, interaction: Interaction, tag: str):
        await interaction.response.defer(ephemeral = True)
        await self.ViewHelper(tag, interaction, raw = False)

    @app_commands.command(name = "view-raw", description = "View the raw tag text by name")
    async def ViewRaw(self, interaction: Interaction, tag: str):
        await interaction.response.defer(ephemeral = True)
        await self.ViewHelper(tag, interaction, raw = True)

    @app_commands.command(name = "random", description = "View a tag random tag")
    @app_commands.describe(tag = "randomly select from tags containing name")
    async def Random(self, interaction: Interaction, tag: str = None):
        tag = self.bot.current(tag)
        tag = await self.bot.fetchrow("SELECT owner, name, value FROM tags WHERE guild = $1 AND nsfw = FALSE AND private = FALSE AND name LIKE $2 ORDER BY RANDOM() LIMIT 1", interaction.guild_id, f"%{tag}%")
        if not tag:
            return
        owner = self.bot.get_user(tag["owner"])
        await interaction.response.send_message(
            embed = SimpleEmbed(
                author = {"name": str(owner), "icon_url": owner.display_avatar},
                title = tag["name"],
                text = tag["value"]))

    @app_commands.command(name = "list", description = "View all tags by a set user")
    @app_commands.describe(user = "leave Blank to search your own tags")
    async def List(self, interaction: Interaction, user: discord.Member = None):
        user = user or interaction.user
        tags = await self.bot.fetch("SELECT name FROM tags WHERE guild = $1 AND owner = $2 AND private = FALSE", interaction.guild_id, user.id)
        embeds = SimpleEmbedList(title = f"{user.name}'s tags", descriptions = "\n".join(tag["name"] for tag in tags))
        await interaction.response.send_message(embeds = embeds, ephemeral = True)

    @app_commands.command(name = "list-all", description = "View all tags on the server")
    async def ListAll(self, interaction: Interaction):
        tags = await self.bot.fetch("SELECT name FROM tags WHERE guild = $1 AND private = FALSE", interaction.guild_id)
        embeds = SimpleEmbedList(title = "Server tags", descriptions = "\n".join(tag["name"] for tag in tags))
        await interaction.response.send_message(embeds = embeds, ephemeral = True)

    @app_commands.command(name = "transfer", description = "Transfer ownership of tag to someone else")
    async def Transfer(self, interaction: Interaction, tag: str, user: discord.Member):
        if not ((tag := await self.bot.to_int(tag)) or await self.OwnerCheck(tag, interaction.user.id)):
            return
        name = await self.bot.fetchval("UPDATE tags SET owner = $1 WHERE tagid = $2 RETURNING name", user.id, tag)
        await interaction.response.send_message(f"{user.mention} has become the owner of tag {name}")

    @app_commands.command(name = "claim", description = "Claim ownership of orphaned tags")
    async def Claim(self, interaction: Interaction, tag: str):
        if not (tag := await self.bot.to_int(tag)):
            return
        owner = self.bot.get_user(await self.bot.fetchval("SELECT owner FROM tags WHERE tagid = $1", tag))
        if owner not in interaction.guild.members:
            await self.bot.execute("UPDATE tags SET owner = $1 WHERE tagid = $2", interaction.user.id, tag)
            return await interaction.response.send_message("You have successfully claimed the tag", ephemeral = True)
        await interaction.response.send_message("cannot claim tag from a user still in the server", ephemeral = True)

    @Edit.autocomplete("tag")
    @Rename.autocomplete("tag")
    @Delete.autocomplete("tag")
    @Transfer.autocomplete("tag")
    async def PrivilegedTagAutocomplete(self, interaction: Interaction, current: None | int | str = "%") -> list[
        app_commands.Choice]:
        current = self.bot.current(current)
        tags = await self.bot.fetch("SELECT tagid, name FROM tags WHERE guild = $1 AND (owner = $2 OR public = TRUE) AND name LIKE $3", interaction.guild_id, interaction.user.id, current)
        return [app_commands.Choice(name = name, value = str(tagid)) for tagid, name in tags]

    @View.autocomplete("tag")
    @ViewRaw.autocomplete("tag")
    @Claim.autocomplete("tag")
    async def TagViewAutocomplete(self, interaction: Interaction, current: None | str) -> list[app_commands.Choice]:
        current = self.bot.current(current)
        tags = await self.bot.fetch("SELECT tagid, name FROM tags WHERE guild = $1 AND name LIKE $2", interaction.guild_id, current)
        return [app_commands.Choice(name = name, value = str(tagid)) for tagid, name in tags]


async def setup(bot):
    await bot.add_cog(Tag(bot))
