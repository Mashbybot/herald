"""
Character Inventory Cog for Herald Bot
Handles equipment and notes management for characters
"""

import discord
from discord import app_commands
from discord.ext import commands
from typing import List
import logging

from core.db import get_db_connection
from core.character_utils import find_character, character_autocomplete
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
            conn = get_db_connection()
            cur = conn.cursor()
            
            cur.execute("DELETE FROM equipment WHERE user_id = ? AND character_name = ?", 
                       (self.user_id, self.character_name))
            
            deleted_count = cur.rowcount
            conn.commit()
            conn.close()
            
            embed = discord.Embed(
                title="✅ Equipment Cleared",
                description=f"Removed all {deleted_count} equipment items from **{self.character_name}**",
                color=0x228B22
            )
            
            # Disable all buttons
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
        
        # Disable all buttons
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
            conn = get_db_connection()
            cur = conn.cursor()
            
            cur.execute("DELETE FROM notes WHERE user_id = ? AND character_name = ?", 
                       (self.user_id, self.character_name))
            
            deleted_count = cur.rowcount
            conn.commit()
            conn.close()
            
            embed = discord.Embed(
                title="✅ Notes Cleared",
                description=f"Removed all {deleted_count} notes from **{self.character_name}**'s journal",
                color=0x228B22
            )
            
            # Disable all buttons
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
        
        # Disable all buttons
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
        character="Character name",
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
        character: str,
        action: str,
        item: str = None,
        description: str = None
    ):
        """Manage character equipment"""
        user_id = str(interaction.user.id)
        
        try:
            # Use fuzzy character matching
            char = await find_character(user_id, character)
            
            if not char:
                await interaction.response.send_message(f"⚠️ No character named **{character}** found", ephemeral=True)
                return
            
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Create equipment table if it doesn't exist
            cur.execute("""
                CREATE TABLE IF NOT EXISTS equipment (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    character_name TEXT NOT NULL,
                    item_name TEXT NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id, character_name) REFERENCES characters(user_id, name) ON DELETE CASCADE
                )
            """)
            
            if action == "view":
                # Show all equipment
                cur.execute("""
                    SELECT item_name, description 
                    FROM equipment 
                    WHERE user_id = ? AND character_name = ? 
                    ORDER BY item_name
                """, (user_id, char['name']))
                
                equipment_list = cur.fetchall()
                
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
                    
                    # Split into chunks if too long
                    full_text = "\n".join(equipment_text)
                    if len(full_text) <= 1024:
                        embed.add_field(name="📦 Items", value=full_text, inline=False)
                    else:
                        # Split into multiple fields
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
                
                # Check if item already exists
                cur.execute("SELECT id FROM equipment WHERE user_id = ? AND character_name = ? AND item_name = ?",
                           (user_id, char['name'], item))
                if cur.fetchone():
                    await interaction.response.send_message(f"⚠️ **{item}** already in equipment list", ephemeral=True)
                    return
                
                # Add equipment
                cur.execute("""
                    INSERT INTO equipment (user_id, character_name, item_name, description)
                    VALUES (?, ?, ?, ?)
                """, (user_id, char['name'], item, description))
                
                conn.commit()
                
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
                
                # Remove equipment (fuzzy matching)
                cur.execute("SELECT item_name FROM equipment WHERE user_id = ? AND character_name = ?", 
                           (user_id, char['name']))
                all_items = cur.fetchall()
                
                # Find best match
                target_item = None
                for eq_item in all_items:
                    if eq_item['item_name'].lower() == item.lower():
                        target_item = eq_item['item_name']
                        break
                
                if not target_item:
                    await interaction.response.send_message(f"⚠️ Equipment item **{item}** not found", ephemeral=True)
                    return
                
                cur.execute("DELETE FROM equipment WHERE user_id = ? AND character_name = ? AND item_name = ?",
                           (user_id, char['name'], target_item))
                
                conn.commit()
                
                embed = discord.Embed(
                    title="✅ Equipment Removed",
                    description=f"Removed **{target_item}** from {char['name']}'s equipment",
                    color=0xFF4500
                )
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                logger.info(f"Removed equipment '{target_item}' from {char['name']} for user {user_id}")
                
            elif action == "clear":
                # Clear all equipment with confirmation
                cur.execute("SELECT COUNT(*) as count FROM equipment WHERE user_id = ? AND character_name = ?",
                           (user_id, char['name']))
                count = cur.fetchone()['count']
                
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
        finally:
            conn.close()

    # ===== NOTES COMMANDS =====

    @app_commands.command(name="notes", description="Manage character notes and journal entries")
    @app_commands.describe(
        character="Character name",
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
        character: str,
        action: str,
        title: str = None,
        content: str = None
    ):
        """Manage character notes and journal entries"""
        user_id = str(interaction.user.id)
        
        try:
            # Use fuzzy character matching
            char = await find_character(user_id, character)
            
            if not char:
                await interaction.response.send_message(f"⚠️ No character named **{character}** found", ephemeral=True)
                return
            
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Create notes table if it doesn't exist
            cur.execute("""
                CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    character_name TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id, character_name) REFERENCES characters(user_id, name) ON DELETE CASCADE
                )
            """)
            
            if action == "view":
                # Show all notes
                cur.execute("""
                    SELECT title, content, created_at 
                    FROM notes 
                    WHERE user_id = ? AND character_name = ? 
                    ORDER BY created_at DESC
                """, (user_id, char['name']))
                
                notes_list = cur.fetchall()
                
                embed = discord.Embed(
                    title=f"📓 {char['name']}'s Notes",
                    color=0x4169E1
                )
                
                if not notes_list:
                    embed.description = "*No notes recorded*"
                    embed.add_field(
                        name="💡 Add Notes",
                        value="Use `/notes character:Name action:add title:\"Note Title\" content:\"Note content\"`",
                        inline=False
                    )
                else:
                    for i, note in enumerate(notes_list[:5]):  # Show last 5 notes
                        date_str = note['created_at'][:10]  # Just the date
                        note_preview = note['content'][:100] + "..." if len(note['content']) > 100 else note['content']
                        
                        embed.add_field(
                            name=f"📝 {note['title']} ({date_str})",
                            value=note_preview,
                            inline=False
                        )
                    
                    if len(notes_list) > 5:
                        embed.set_footer(text=f"Showing 5 of {len(notes_list)} notes")
                    else:
                        embed.set_footer(text=f"Total notes: {len(notes_list)}")
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
            elif action == "add":
                if not title or not content:
                    await interaction.response.send_message("❌ Both title and content required for adding notes", ephemeral=True)
                    return
                
                if len(title) > 100:
                    await interaction.response.send_message("❌ Note title too long (max 100 characters)", ephemeral=True)
                    return
                
                if len(content) > 2000:
                    await interaction.response.send_message("❌ Note content too long (max 2000 characters)", ephemeral=True)
                    return
                
                # Add note
                cur.execute("""
                    INSERT INTO notes (user_id, character_name, title, content)
                    VALUES (?, ?, ?, ?)
                """, (user_id, char['name'], title, content))
                
                conn.commit()
                
                embed = discord.Embed(
                    title="✅ Note Added",
                    description=f"Added note **{title}** to {char['name']}'s journal",
                    color=0x228B22
                )
                
                # Show preview of content
                preview = content[:200] + "..." if len(content) > 200 else content
                embed.add_field(name="📝 Content Preview", value=preview, inline=False)
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                logger.info(f"Added note '{title}' to {char['name']} for user {user_id}")
                
            elif action == "remove":
                if not title:
                    await interaction.response.send_message("❌ Note title required for removal", ephemeral=True)
                    return
                
                # Find and remove note (fuzzy matching)
                cur.execute("SELECT title FROM notes WHERE user_id = ? AND character_name = ?", 
                           (user_id, char['name']))
                all_notes = cur.fetchall()
                
                # Find best match
                target_title = None
                for note in all_notes:
                    if note['title'].lower() == title.lower():
                        target_title = note['title']
                        break
                
                if not target_title:
                    await interaction.response.send_message(f"⚠️ Note **{title}** not found", ephemeral=True)
                    return
                
                cur.execute("DELETE FROM notes WHERE user_id = ? AND character_name = ? AND title = ?",
                           (user_id, char['name'], target_title))
                
                conn.commit()
                
                embed = discord.Embed(
                    title="✅ Note Removed",
                    description=f"Removed note **{target_title}** from {char['name']}'s journal",
                    color=0xFF4500
                )
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                logger.info(f"Removed note '{target_title}' from {char['name']} for user {user_id}")
                
            elif action == "clear":
                # Clear all notes with confirmation
                cur.execute("SELECT COUNT(*) as count FROM notes WHERE user_id = ? AND character_name = ?",
                           (user_id, char['name']))
                count = cur.fetchone()['count']
                
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
        finally:
            conn.close()

    # ===== AUTOCOMPLETE FUNCTIONS =====

    @equipment.autocomplete('character')
    @notes.autocomplete('character')
    async def inventory_character_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> List[app_commands.Choice[str]]:
        """Autocomplete character names for inventory commands"""
        return await character_autocomplete(interaction, current)

    @equipment.autocomplete('item')
    async def equipment_item_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> List[app_commands.Choice[str]]:
        """Autocomplete equipment item names for removal"""
        # Only provide autocomplete for remove action
        if not hasattr(interaction, 'namespace') or interaction.namespace.action != "remove":
            return []
        
        try:
            user_id = str(interaction.user.id)
            character = getattr(interaction.namespace, 'character', None)
            
            if not character:
                return []
            
            # Find character using fuzzy matching
            char = await find_character(user_id, character)
            if not char:
                return []
            
            conn = get_db_connection()
            cur = conn.cursor()
            
            cur.execute("SELECT item_name FROM equipment WHERE user_id = ? AND character_name = ? ORDER BY item_name", 
                       (user_id, char['name']))
            items = cur.fetchall()
            conn.close()
            
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
        # Only provide autocomplete for remove action
        if not hasattr(interaction, 'namespace') or interaction.namespace.action != "remove":
            return []
        
        try:
            user_id = str(interaction.user.id)
            character = getattr(interaction.namespace, 'character', None)
            
            if not character:
                return []
            
            # Find character using fuzzy matching
            char = await find_character(user_id, character)
            if not char:
                return []
            
            conn = get_db_connection()
            cur = conn.cursor()
            
            cur.execute("SELECT title FROM notes WHERE user_id = ? AND character_name = ? ORDER BY created_at DESC", 
                       (user_id, char['name']))
            notes_list = cur.fetchall()
            conn.close()
            
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
    
    # Only register guild commands if GUILD_ID is set (development mode)
    if GUILD_ID:
        for command in cog.get_app_commands():
            bot.tree.add_command(command, guild=discord.Object(id=GUILD_ID))
        logger.info(f"Character Inventory cog loaded with {len(cog.get_app_commands())} guild commands")
    else:
        logger.info(f"Character Inventory cog loaded with {len(cog.get_app_commands())} global commands")
