"""
Character Inventory Cog for Herald Bot
Handles equipment and notes management for characters
CONVERTED TO ASYNC POSTGRESQL
"""

import discord
from discord import app_commands
from discord.ext import commands
from typing import List
import logging

from core.db import get_async_db
from core.character_utils import find_character, character_autocomplete, resolve_character, get_active_character
from config.settings import GUILD_ID

logger = logging.getLogger('Herald.Character.Inventory')


# ===== VIEW CLASSES =====

class ClearEquipmentView(discord.ui.View):
    """Confirmation view for clearing all equipment"""
    
    def __init__(self, user_id: str, character_name: str, count: int, timeout: float = 30):
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.character_name = character_name
        self.count = count
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Ensure only the original user can interact"""
        return str(interaction.user.id) == self.user_id
    
    @discord.ui.button(label="Clear All Equipment", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def confirm_clear(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Confirm and execute equipment clearing"""
        try:
            async with get_async_db() as conn:
                result = await conn.execute(
                    "DELETE FROM equipment WHERE user_id = $1 AND character_name = $2",
                    self.user_id, self.character_name
                )
                deleted_count = int(result.split()[-1]) if result else 0
            
            embed = discord.Embed(
                title="✅ Equipment Cleared",
                description=f"Removed all {deleted_count} equipment items from **{self.character_name}**",
                color=0x228B22
            )
            
            for item in self.children:
                item.disabled = True
            
            await interaction.response.edit_message(embed=embed, view=self)
            logger.info(f"Cleared all equipment from '{self.character_name}' for user {self.user_id}")
            
        except Exception as e:
            logger.error(f"Error clearing equipment: {e}")
            await interaction.response.send_message(
                f"❌ Error clearing equipment: {str(e)}", ephemeral=True
            )
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel_clear(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel equipment clearing"""
        embed = discord.Embed(
            title="❌ Clear Cancelled",
            description=f"**{self.character_name}**'s equipment was not cleared",
            color=0x4169E1
        )
        
        for item in self.children:
            item.disabled = True
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def on_timeout(self):
        """Handle timeout"""
        for item in self.children:
            item.disabled = True


class ClearNotesView(discord.ui.View):
    """Confirmation view for clearing all notes"""
    
    def __init__(self, user_id: str, character_name: str, count: int, timeout: float = 30):
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.character_name = character_name
        self.count = count
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Ensure only the original user can interact"""
        return str(interaction.user.id) == self.user_id
    
    @discord.ui.button(label="Clear All Notes", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def confirm_clear(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Confirm and execute notes clearing"""
        try:
            async with get_async_db() as conn:
                result = await conn.execute(
                    "DELETE FROM notes WHERE user_id = $1 AND character_name = $2",
                    self.user_id, self.character_name
                )
                deleted_count = int(result.split()[-1]) if result else 0
            
            embed = discord.Embed(
                title="✅ Notes Cleared",
                description=f"Removed all {deleted_count} notes from **{self.character_name}**'s journal",
                color=0x228B22
            )
            
            for item in self.children:
                item.disabled = True
            
            await interaction.response.edit_message(embed=embed, view=self)
            logger.info(f"Cleared all notes from '{self.character_name}' for user {self.user_id}")
            
        except Exception as e:
            logger.error(f"Error clearing notes: {e}")
            await interaction.response.send_message(
                f"❌ Error clearing notes: {str(e)}", ephemeral=True
            )
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel_clear(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel notes clearing"""
        embed = discord.Embed(
            title="❌ Clear Cancelled",
            description=f"**{self.character_name}**'s notes were not cleared",
            color=0x4169E1
        )
        
        for item in self.children:
            item.disabled = True
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def on_timeout(self):
        """Handle timeout"""
        for item in self.children:
            item.disabled = True


# ===== MAIN COG CLASS =====

class CharacterInventory(commands.Cog):
    """Character Inventory - Equipment and notes management"""
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger('Herald.Character.Inventory')

    # ===== EQUIPMENT COMMANDS =====

    @app_commands.command(name="equipment", description="Manage your character's equipment")
    @app_commands.describe(
        action="What to do with equipment",
        item="Item name (required for add/remove)",
        description="Item description (optional for add)"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="View", value="view"),
        app_commands.Choice(name="Add", value="add"),
        app_commands.Choice(name="Remove", value="remove"),
        app_commands.Choice(name="Clear All", value="clear")
    ])
    async def equipment(
        self,
        interaction: discord.Interaction,
        action: str,
        item: str = None,
        description: str = None
    ):
        """Manage character equipment"""
        user_id = str(interaction.user.id)

        try:
            # Get active character
            active_char_name = await get_active_character(user_id)
            if not active_char_name:
                await interaction.response.send_message(
                    f"❌ No active character set. Use `/character` to set your active character.",
                    ephemeral=True
                )
                return

            char = await find_character(user_id, active_char_name)
            if not char:
                await interaction.response.send_message(
                    f"❌ Could not find your active character.",
                    ephemeral=True
                )
                return
            
            if action == "view":
                async with get_async_db() as conn:
                    equipment_list = await conn.fetch(
                        "SELECT item_name, description FROM equipment WHERE user_id = $1 AND character_name = $2 ORDER BY item_name",
                        user_id, char['name']
                    )
                
                embed = discord.Embed(
                    title=f"🎒 {char['name']}'s Equipment",
                    color=0x8B4513
                )
                
                if not equipment_list:
                    embed.description = "*No equipment recorded*"
                    embed.add_field(
                        name="💡 Add Equipment",
                        value="Use `/equipment character:Name action:add item:\"Item Name\" description:\"Details\"`",
                        inline=False
                    )
                else:
                    equipment_text = []
                    for eq in equipment_list:
                        if eq['description']:
                            equipment_text.append(f"**{eq['item_name']}** - {eq['description']}")
                        else:
                            equipment_text.append(f"**{eq['item_name']}**")
                    
                    full_text = "\n".join(equipment_text)
                    if len(full_text) <= 1024:
                        embed.add_field(name="📦 Items", value=full_text, inline=False)
                    else:
                        chunks = []
                        current_chunk = []
                        current_length = 0
                        
                        for line in equipment_text:
                            if current_length + len(line) + 1 > 1024:
                                chunks.append("\n".join(current_chunk))
                                current_chunk = [line]
                                current_length = len(line)
                            else:
                                current_chunk.append(line)
                                current_length += len(line) + 1
                        
                        if current_chunk:
                            chunks.append("\n".join(current_chunk))
                        
                        for i, chunk in enumerate(chunks):
                            field_name = "📦 Items" if i == 0 else f"📦 Items (cont. {i+1})"
                            embed.add_field(name=field_name, value=chunk, inline=False)
                    
                    embed.set_footer(text=f"Total items: {len(equipment_list)}")
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
            elif action == "add":
                if not item:
                    await interaction.response.send_message("❌ Item name required for adding equipment", ephemeral=True)
                    return
                
                if len(item) > 100:
                    await interaction.response.send_message("❌ Item name too long (max 100 characters)", ephemeral=True)
                    return
                
                async with get_async_db() as conn:
                    existing = await conn.fetchrow(
                        "SELECT id FROM equipment WHERE user_id = $1 AND character_name = $2 AND item_name = $3",
                        user_id, char['name'], item
                    )
                    
                    if existing:
                        await interaction.response.send_message(f"⚠️ **{item}** already in equipment list", ephemeral=True)
                        return
                    
                    await conn.execute(
                        "INSERT INTO equipment (user_id, character_name, item_name, description) VALUES ($1, $2, $3, $4)",
                        user_id, char['name'], item, description
                    )
                
                embed = discord.Embed(
                    title="✅ Equipment Added",
                    description=f"Added **{item}** to {char['name']}'s equipment",
                    color=0x228B22
                )
                
                if description:
                    embed.add_field(name="📝 Description", value=description, inline=False)
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                logger.info(f"Added equipment '{item}' to {char['name']} for user {user_id}")
                
            elif action == "remove":
                if not item:
                    await interaction.response.send_message("❌ Item name required for removing equipment", ephemeral=True)
                    return
                
                async with get_async_db() as conn:
                    all_items = await conn.fetch(
                        "SELECT item_name FROM equipment WHERE user_id = $1 AND character_name = $2",
                        user_id, char['name']
                    )
                    
                    target_item = None
                    for eq_item in all_items:
                        if eq_item['item_name'].lower() == item.lower():
                            target_item = eq_item['item_name']
                            break
                    
                    if not target_item:
                        await interaction.response.send_message(f"⚠️ Equipment item **{item}** not found", ephemeral=True)
                        return
                    
                    await conn.execute(
                        "DELETE FROM equipment WHERE user_id = $1 AND character_name = $2 AND item_name = $3",
                        user_id, char['name'], target_item
                    )
                
                embed = discord.Embed(
                    title="✅ Equipment Removed",
                    description=f"Removed **{target_item}** from {char['name']}'s equipment",
                    color=0xFF4500
                )
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                logger.info(f"Removed equipment '{target_item}' from {char['name']} for user {user_id}")
                
            elif action == "clear":
                async with get_async_db() as conn:
                    count = await conn.fetchval(
                        "SELECT COUNT(*) FROM equipment WHERE user_id = $1 AND character_name = $2",
                        user_id, char['name']
                    )
                
                if count == 0:
                    await interaction.response.send_message(f"⚠️ {char['name']} has no equipment to clear", ephemeral=True)
                    return
                
                view = ClearEquipmentView(user_id, char['name'], count, timeout=30)
                
                embed = discord.Embed(
                    title="⚠️ Clear All Equipment",
                    description=f"Remove all {count} equipment items from **{char['name']}**?",
                    color=0xFF4500
                )
                embed.add_field(name="⚠️ Warning", value="This action cannot be undone.", inline=False)
                embed.set_footer(text="You have 30 seconds to confirm or cancel")
                
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in equipment command: {e}")
            await interaction.response.send_message("❌ An error occurred while managing equipment", ephemeral=True)

    # ===== NOTES COMMANDS =====

    @app_commands.command(name="notes", description="Manage character notes and journal entries")
    @app_commands.describe(
        action="What to do with notes",
        title="Note title (required for add)",
        content="Note content (required for add)"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="View All", value="view"),
        app_commands.Choice(name="Add", value="add"),
        app_commands.Choice(name="Remove", value="remove"),
        app_commands.Choice(name="Clear All", value="clear")
    ])
    async def notes(
        self,
        interaction: discord.Interaction,
        action: str,
        title: str = None,
        content: str = None
    ):
        """Manage character notes and journal entries"""
        user_id = str(interaction.user.id)

        try:
            # Get active character
            active_char_name = await get_active_character(user_id)
            if not active_char_name:
                await interaction.response.send_message(
                    f"❌ No active character set. Use `/character` to set your active character.",
                    ephemeral=True
                )
                return

            char = await find_character(user_id, active_char_name)
            if not char:
                await interaction.response.send_message(
                    f"❌ Could not find your active character.",
                    ephemeral=True
                )
                return
            
            if action == "view":
                async with get_async_db() as conn:
                    notes_list = await conn.fetch(
                        "SELECT title, content, created_at FROM notes WHERE user_id = $1 AND character_name = $2 ORDER BY created_at DESC",
                        user_id, char['name']
                    )
                
                embed = discord.Embed(
                    title=f"📓 {char['name']}'s Notes",
                    color=0x8B4513
                )
                
                if not notes_list:
                    embed.description = "*No notes recorded*"
                    embed.add_field(
                        name="💡 Add Note",
                        value="Use `/notes character:Name action:add title:\"Title\" content:\"Content\"`",
                        inline=False
                    )
                else:
                    for note in notes_list[:10]:
                        note_preview = note['content'][:100] + "..." if len(note['content']) > 100 else note['content']
                        embed.add_field(
                            name=f"📝 {note['title']}",
                            value=note_preview,
                            inline=False
                        )
                    
                    if len(notes_list) > 10:
                        embed.set_footer(text=f"Showing 10 of {len(notes_list)} notes")
                    else:
                        embed.set_footer(text=f"Total notes: {len(notes_list)}")
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
            elif action == "add":
                if not title or not content:
                    await interaction.response.send_message("❌ Title and content required for adding notes", ephemeral=True)
                    return
                
                if len(title) > 100:
                    await interaction.response.send_message("❌ Title too long (max 100 characters)", ephemeral=True)
                    return
                
                if len(content) > 2000:
                    await interaction.response.send_message("❌ Content too long (max 2000 characters)", ephemeral=True)
                    return
                
                async with get_async_db() as conn:
                    await conn.execute(
                        "INSERT INTO notes (user_id, character_name, title, content) VALUES ($1, $2, $3, $4)",
                        user_id, char['name'], title, content
                    )
                
                embed = discord.Embed(
                    title="✅ Note Added",
                    description=f"Added note **{title}** to {char['name']}'s journal",
                    color=0x228B22
                )
                
                content_preview = content[:200] + "..." if len(content) > 200 else content
                embed.add_field(name="📝 Content Preview", value=content_preview, inline=False)
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                logger.info(f"Added note '{title}' to {char['name']} for user {user_id}")
                
            elif action == "remove":
                if not title:
                    await interaction.response.send_message("❌ Title required for removing notes", ephemeral=True)
                    return
                
                async with get_async_db() as conn:
                    all_notes = await conn.fetch(
                        "SELECT title FROM notes WHERE user_id = $1 AND character_name = $2",
                        user_id, char['name']
                    )
                    
                    target_title = None
                    for note in all_notes:
                        if note['title'].lower() == title.lower():
                            target_title = note['title']
                            break
                    
                    if not target_title:
                        await interaction.response.send_message(f"⚠️ Note **{title}** not found", ephemeral=True)
                        return
                    
                    await conn.execute(
                        "DELETE FROM notes WHERE user_id = $1 AND character_name = $2 AND title = $3",
                        user_id, char['name'], target_title
                    )
                
                embed = discord.Embed(
                    title="✅ Note Removed",
                    description=f"Removed note **{target_title}** from {char['name']}'s journal",
                    color=0xFF4500
                )
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                logger.info(f"Removed note '{target_title}' from {char['name']} for user {user_id}")
                
            elif action == "clear":
                async with get_async_db() as conn:
                    count = await conn.fetchval(
                        "SELECT COUNT(*) FROM notes WHERE user_id = $1 AND character_name = $2",
                        user_id, char['name']
                    )
                
                if count == 0:
                    await interaction.response.send_message(f"⚠️ {char['name']} has no notes to clear", ephemeral=True)
                    return
                
                view = ClearNotesView(user_id, char['name'], count, timeout=30)
                
                embed = discord.Embed(
                    title="⚠️ Clear All Notes",
                    description=f"Remove all {count} notes from **{char['name']}**?",
                    color=0xFF4500
                )
                embed.add_field(name="⚠️ Warning", value="This action cannot be undone.", inline=False)
                embed.set_footer(text="You have 30 seconds to confirm or cancel")
                
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in notes command: {e}")
            await interaction.response.send_message("❌ An error occurred while managing notes", ephemeral=True)

    # ===== AUTOCOMPLETE FUNCTIONS =====

    @equipment.autocomplete('item')
    async def equipment_item_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> List[app_commands.Choice[str]]:
        """Autocomplete equipment item names for removal"""
        if not hasattr(interaction, 'namespace') or interaction.namespace.action != "remove":
            return []
        
        try:
            user_id = str(interaction.user.id)
            character = getattr(interaction.namespace, 'character', None)
            
            if not character:
                return []
            
            char = await find_character(user_id, character)
            if not char:
                return []
            
            async with get_async_db() as conn:
                items = await conn.fetch(
                    "SELECT item_name FROM equipment WHERE user_id = $1 AND character_name = $2 ORDER BY item_name",
                    user_id, char['name']
                )
            
            filtered = [
                item['item_name'] for item in items 
                if current.lower() in item['item_name'].lower()
            ]
            
            return [
                app_commands.Choice(name=item_name, value=item_name)
                for item_name in filtered[:25]
            ]
        except Exception as e:
            logger.error(f"Error in equipment item autocomplete: {e}")
            return []

    @notes.autocomplete('title')
    async def notes_title_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> List[app_commands.Choice[str]]:
        """Autocomplete note titles for removal"""
        if not hasattr(interaction, 'namespace') or interaction.namespace.action != "remove":
            return []
        
        try:
            user_id = str(interaction.user.id)
            character = getattr(interaction.namespace, 'character', None)
            
            if not character:
                return []
            
            char = await find_character(user_id, character)
            if not char:
                return []
            
            async with get_async_db() as conn:
                notes_list = await conn.fetch(
                    "SELECT title FROM notes WHERE user_id = $1 AND character_name = $2 ORDER BY created_at DESC",
                    user_id, char['name']
                )
            
            filtered = [
                note['title'] for note in notes_list 
                if current.lower() in note['title'].lower()
            ]
            
            return [
                app_commands.Choice(name=title, value=title)
                for title in filtered[:25]
            ]
        except Exception as e:
            logger.error(f"Error in notes title autocomplete: {e}")
            return []


async def setup(bot: commands.Bot):
    """Setup function for the Character Inventory cog"""
    cog = CharacterInventory(bot)
    await bot.add_cog(cog)
    logger.info(f"Character Inventory cog loaded with {len(cog.get_app_commands())} commands")
