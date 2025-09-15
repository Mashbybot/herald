"""
Character Management Cog for Herald Bot
Handles basic character CRUD operations: create, delete, rename, list, sheet display
"""

import discord
from discord import app_commands
from discord.ext import commands
from typing import List
import logging

from core.db import get_db_connection
from core.character_utils import (
    find_character, character_autocomplete, get_character_and_skills, 
    ensure_h5e_columns, ALL_SKILLS, H5E_SKILLS, HeraldMessages
)
from core.ui_utils import create_health_bar, create_willpower_bar
from config.settings import GUILD_ID

logger = logging.getLogger('Herald.Character.Management')


def safe_get_character_field(character, field, default=None):
    """Safely get a field from sqlite3.Row with default value"""
    try:
        value = character[field]
        return value if value is not None else default
    except (KeyError, IndexError):
        return default


class DeleteConfirmationView(discord.ui.View):
    """Confirmation view for character deletion"""
    
    def __init__(self, user_id: str, character_name: str, timeout: float = 30):
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.character_name = character_name
        self.confirmed = False
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Ensure only the original user can interact"""
        return str(interaction.user.id) == self.user_id
    
    @discord.ui.button(label="Delete Character", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def confirm_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Confirm and execute character deletion"""
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Delete character (skills will be deleted by CASCADE)
            cur.execute("DELETE FROM characters WHERE user_id = ? AND name = ?", 
                       (self.user_id, self.character_name))
            
            if cur.rowcount == 0:
                await interaction.response.send_message(
                    "⚠️ Character not found or already deleted", ephemeral=True
                )
                conn.close()
                return
            
            conn.commit()
            conn.close()
            
            embed = discord.Embed(
                title="✅ Character Deleted",
                description=f"**{self.character_name}** has been permanently deleted",
                color=0x228B22
            )
            
            embed.add_field(
                name="Data Removed",
                value="• Character sheet\n• All skill ratings\n• Equipment and notes",
                inline=False
            )
            
            # Disable all buttons
            for item in self.children:
                item.disabled = True
            
            await interaction.response.edit_message(embed=embed, view=self)
            logger.info(f"Deleted character '{self.character_name}' for user {self.user_id}")
            
        except Exception as e:
            logger.error(f"Error deleting character: {e}")
            await interaction.response.send_message(
                f"❌ Error deleting character: {str(e)}", ephemeral=True
            )
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel character deletion"""
        embed = discord.Embed(
            title="❌ Deletion Cancelled",
            description=f"**{self.character_name}** was not deleted",
            color=0x4169E1
        )
        
        # Disable all buttons
        for item in self.children:
            item.disabled = True
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def on_timeout(self):
        """Handle timeout"""
        # Disable all buttons when timeout occurs
        for item in self.children:
            item.disabled = True


class CharacterManagement(commands.Cog):
    """Character Management - Basic CRUD operations for Hunter characters"""
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger('Herald.Character.Management')

    @app_commands.command(name="create", description="Create your Hunter character sheet")
    @app_commands.describe(
        name="Character name",
        strength="Strength (1-5, default: 1)",
        dexterity="Dexterity (1-5, default: 1)",
        stamina="Stamina (1-5, default: 1)",
        charisma="Charisma (1-5, default: 1)",
        manipulation="Manipulation (1-5, default: 1)",
        composure="Composure (1-5, default: 1)",
        intelligence="Intelligence (1-5, default: 1)",
        wits="Wits (1-5, default: 1)",
        resolve="Resolve (1-5, default: 1)",
        ambition="Long-term goal (recovers aggravated willpower damage)",
        desire="Short-term goal (recovers superficial willpower damage)",
        drive="Why you hunt the supernatural"
    )
    async def create_character(
        self,
        interaction: discord.Interaction,
        name: str,
        strength: int = 1,
        dexterity: int = 1,
        stamina: int = 1,
        charisma: int = 1,
        manipulation: int = 1,
        composure: int = 1,
        intelligence: int = 1,
        wits: int = 1,
        resolve: int = 1,
        ambition: str = None,
        desire: str = None,
        drive: str = None,
    ):
        """Create a new Hunter character"""
        user_id = str(interaction.user.id)
        
        # Validate attribute ranges
        attributes = {
            "Strength": strength, "Dexterity": dexterity, "Stamina": stamina,
            "Charisma": charisma, "Manipulation": manipulation, "Composure": composure,
            "Intelligence": intelligence, "Wits": wits, "Resolve": resolve
        }
        
        for attr_name, value in attributes.items():
            if not 1 <= value <= 5:
                await interaction.response.send_message(
                    f"❌ {attr_name} must be between 1 and 5 (got {value})", ephemeral=True
                )
                return
        
        # Validate character name
        if len(name) < 2 or len(name) > 32:
            await interaction.response.send_message(
                "❌ Character name must be between 2 and 32 characters", ephemeral=True
            )
            return

        # Validate optional text fields
        if ambition and len(ambition) > 200:
            await interaction.response.send_message(
                "❌ Ambition must be 200 characters or less", ephemeral=True
            )
            return
        
        if desire and len(desire) > 200:
            await interaction.response.send_message(
                "❌ Desire must be 200 characters or less", ephemeral=True
            )
            return
            
        if drive and len(drive) > 200:
            await interaction.response.send_message(
                "❌ Drive must be 200 characters or less", ephemeral=True
            )
            return
        
        try:
            conn = get_db_connection()
            cur = conn.cursor()

            # Ensure H5E columns exist
            await ensure_h5e_columns()

            # Check for existing character
            cur.execute("SELECT name FROM characters WHERE user_id = ? AND name = ?", (user_id, name))
            if cur.fetchone():
                await interaction.response.send_message(
                    f"⚠️ You already have a character named **{name}**", ephemeral=True
                )
                conn.close()
                return

            # Calculate derived stats (H5E rules)
            health = stamina + 3
            willpower = resolve + composure

            # Create character with H5E mechanics
            cur.execute("""
                INSERT INTO characters (
                    user_id, name,
                    strength, dexterity, stamina,
                    charisma, manipulation, composure,
                    intelligence, wits, resolve,
                    health, willpower,
                    health_sup, health_agg,
                    willpower_sup, willpower_agg,
                    ambition, desire, drive
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0, 0, ?, ?, ?)
            """, (
                user_id, name,
                strength, dexterity, stamina,
                charisma, manipulation, composure,
                intelligence, wits, resolve,
                health, willpower,
                ambition, desire, drive
            ))

            # Initialize all skills at 0
            for skill in ALL_SKILLS:
                cur.execute("""
                    INSERT INTO skills (user_id, character_name, skill_name, dots)
                    VALUES (?, ?, ?, 0)
                """, (user_id, name, skill))

            conn.commit()
            conn.close()

            # Success response with character summary
            embed = discord.Embed(
                title="✅ Character Created",
                description=f"**{name}** is ready for the hunt!",
                color=0x4169E1
            )
            
            # Add attribute summary
            phys = f"Str {strength} • Dex {dexterity} • Sta {stamina}"
            soc = f"Cha {charisma} • Man {manipulation} • Com {composure}"
            ment = f"Int {intelligence} • Wit {wits} • Res {resolve}"
            
            embed.add_field(name="Physical", value=phys, inline=False)
            embed.add_field(name="Social", value=soc, inline=False)
            embed.add_field(name="Mental", value=ment, inline=False)
            embed.add_field(name="Derived Stats", value=f"Health: {health} • Willpower: {willpower}", inline=False)
            
            # Add H5E mechanics if provided
            h5e_info = []
            if ambition:
                h5e_info.append(f"**Ambition:** {ambition}")
            if desire:
                h5e_info.append(f"**Desire:** {desire}")
            if drive:
                h5e_info.append(f"**Drive:** {drive}")
            
            if h5e_info:
                embed.add_field(name="Hunter Mechanics", value="\n".join(h5e_info), inline=False)
            
            embed.set_footer(text="Use /skill_set to assign skill dots • Use /sheet to view full character")

            await interaction.response.send_message(embed=embed)
            logger.info(f"Created character '{name}' for user {user_id}")

        except Exception as e:
            logger.error(f"Error creating character: {e}")
            await interaction.response.send_message(
                f"❌ Error creating character: {str(e)}", ephemeral=True
            )

    @app_commands.command(name="delete", description="Delete one of your characters (with confirmation)")
    @app_commands.describe(name="Character name to delete")
    async def delete_character(self, interaction: discord.Interaction, name: str):
        """Delete a character with confirmation prompt"""
        user_id = str(interaction.user.id)
        
        try:
            # Find character using fuzzy matching
            character = await find_character(user_id, name)
            
            if not character:
                await interaction.response.send_message(
                    f"⚠️ No character named **{name}** found", ephemeral=True
                )
                return
            
            # Create confirmation view
            view = DeleteConfirmationView(user_id, character['name'], timeout=30)
            
            embed = discord.Embed(
                title="⚠️ Confirm Character Deletion",
                description=f"Are you sure you want to delete **{character['name']}**?",
                color=0xFF4500
            )
            
            # Show character summary before deletion
            embed.add_field(
                name="Character Info",
                value=(
                    f"**Attributes:** Str {character['strength']}, Dex {character['dexterity']}, Sta {character['stamina']}\n"
                    f"**Health:** {character['health']} • **Willpower:** {character['willpower']}\n"
                    f"**Creed:** {safe_get_character_field(character, 'creed', 'None set')}"
                ),
                inline=False
            )
            
            embed.add_field(
                name="⚠️ Warning",
                value="This action cannot be undone. All character data and skills will be permanently lost.",
                inline=False
            )
            
            embed.set_footer(text="You have 30 seconds to confirm or cancel")
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in delete character: {e}")
            await interaction.response.send_message(
                f"❌ Error loading character: {str(e)}", ephemeral=True
            )

    @app_commands.command(name="rename", description="Rename one of your characters")
    @app_commands.describe(
        old_name="Current character name", 
        new_name="New character name"
    )
    async def rename_character(self, interaction: discord.Interaction, old_name: str, new_name: str):
        """Rename a character"""
        user_id = str(interaction.user.id)
        
        # Validate new name
        if len(new_name) < 2 or len(new_name) > 32:
            await interaction.response.send_message(
                "❌ Character name must be between 2 and 32 characters", ephemeral=True
            )
            return
        
        try:
            # Find character using fuzzy matching
            character = await find_character(user_id, old_name)
            
            if not character:
                await interaction.response.send_message(
                    f"⚠️ No character named **{old_name}** found", ephemeral=True
                )
                return
            
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Check if new name already exists
            cur.execute("SELECT name FROM characters WHERE user_id = ? AND name = ?", (user_id, new_name))
            if cur.fetchone():
                await interaction.response.send_message(
                    f"⚠️ You already have a character named **{new_name}**", ephemeral=True
                )
                conn.close()
                return
            
            # Update character name (this will cascade to related tables)
            cur.execute(
                "UPDATE characters SET name = ? WHERE user_id = ? AND name = ?",
                (new_name, user_id, character['name'])
            )
            
            # Update skills table (since foreign key uses name, not ID)
            cur.execute(
                "UPDATE skills SET character_name = ? WHERE user_id = ? AND character_name = ?",
                (new_name, user_id, character['name'])
            )
            
            # Update other related tables that might exist
            tables_to_update = ['equipment', 'notes', 'xp_log', 'specialties']
            for table in tables_to_update:
                try:
                    cur.execute(f"""
                        UPDATE {table} SET character_name = ? 
                        WHERE user_id = ? AND character_name = ?
                    """, (new_name, user_id, character['name']))
                except:
                    # Table might not exist yet, ignore
                    pass
            
            conn.commit()
            conn.close()
            
            embed = discord.Embed(
                title="✅ Character Renamed",
                description=f"**{character['name']}** is now **{new_name}**",
                color=0x228B22
            )
            
            embed.set_footer(text="All skills and character data have been preserved")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            logger.info(f"Renamed character '{character['name']}' to '{new_name}' for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error renaming character: {e}")
            await interaction.response.send_message(
                f"❌ Error renaming character: {str(e)}", ephemeral=True
            )

    @app_commands.command(name="characters", description="List your characters")
    async def list_characters(self, interaction: discord.Interaction):
        """List all characters for the user"""
        user_id = str(interaction.user.id)
        
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            cur.execute("SELECT name FROM characters WHERE user_id = ? ORDER BY name", (user_id,))
            characters = cur.fetchall()
            conn.close()
            
            if not characters:
                await interaction.response.send_message(
                    "📝 You don't have any characters yet. Use `/create` to make one!", ephemeral=True
                )
                return
            
            char_list = "\n".join([f"• {char['name']}" for char in characters])
            embed = discord.Embed(
                title="📋 Your Characters",
                description=char_list,
                color=0x4169E1
            )
            embed.set_footer(text="Use /sheet <name> to view a character sheet")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error listing characters: {e}")
            await interaction.response.send_message(
                f"❌ Error loading characters: {str(e)}", ephemeral=True
            )

    @app_commands.command(name="sheet", description="View your Hunter character sheet")
    @app_commands.describe(name="Character name (autocompletes to your characters)")
    async def character_sheet(self, interaction: discord.Interaction, name: str):
        """Display a character sheet with full details"""
        user_id = str(interaction.user.id)
        
        try:
            character, skills = await get_character_and_skills(user_id, name)
            if not character:
                await interaction.response.send_message(
                    f"⚠️ No character named **{name}** found", ephemeral=True
                )
                return

            embed = discord.Embed(
                title=f"📋 {character['name']}'s Character Sheet",
                color=0x4169E1
            )

            # Health, Willpower, and Edge displayed vertically
            # Health: max possible is 8 (5 stamina + 3)
            health_bar = create_health_bar(character['health'], character['health_sup'], character['health_agg'], 8)
            # Willpower: max possible is 10 (5 resolve + 5 composure)  
            willpower_display = create_willpower_bar(character['willpower'], character['willpower_sup'], character['willpower_agg'], 10)
            
            # Edge formatting with black squares for empty
            edge = safe_get_character_field(character, 'edge', 0)
            edge_dots = "⭐" * edge + "▪️" * (5 - edge)
            
            embed.add_field(
                name="__Health__", 
                value=f"\n{health_bar}",
                inline=False
            )
            embed.add_field(
                name="__Willpower__",
                value=f"\n{willpower_display}",
                inline=False
            )
            embed.add_field(
                name="__Edge__",
                value=f"\n{edge_dots}",
                inline=False
            )

            # Page break before attributes
            embed.add_field(name="\u200b", value="═══════════════════════", inline=False)

            # Attributes organized by category
            phys = f"**Strength:** {character['strength']}\n**Dexterity:** {character['dexterity']}\n**Stamina:** {character['stamina']}"
            soc = f"**Charisma:** {character['charisma']}\n**Manipulation:** {character['manipulation']}\n**Composure:** {character['composure']}"
            ment = f"**Intelligence:** {character['intelligence']}\n**Wits:** {character['wits']}\n**Resolve:** {character['resolve']}"
            
            embed.add_field(name="__⚔️ Physical__", value=phys, inline=True)
            embed.add_field(name="__💬 Social__", value=soc, inline=True)
            embed.add_field(name="__🎓 Mental__", value=ment, inline=True)

            # Skills (all categories combined, smart display logic with specialties)
            all_skills = []
            for category in H5E_SKILLS.values():
                all_skills.extend(category)
            
            # Key skills to show as reference when character has few trained skills
            key_skills = ["Athletics", "Brawl", "Firearms", "Stealth", "Intimidation", "Persuasion", "Subterfuge", "Insight", "Investigation", "Occult", "Awareness", "Medicine"]
            
            # Get all trained skills (> 0 dots) and their specialties
            trained_skills = []
            skill_text = []
            
            # Get specialties for this character (with error handling for missing table)
            specialty_data = []
            try:
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("""
                    SELECT skill_name, specialty_name 
                    FROM specialties 
                    WHERE user_id = ? AND character_name = ?
                    ORDER BY skill_name, specialty_name
                """, (user_id, character['name']))
                specialty_data = cur.fetchall()
                conn.close()
            except Exception as e:
                # Table doesn't exist yet, that's fine - no specialties to show
                logger.debug(f"Specialties table not found (this is normal): {e}")
                specialty_data = []
            
            # Group specialties by skill
            specialties_by_skill = {}
            for spec in specialty_data:
                skill_name = spec['skill_name']
                if skill_name not in specialties_by_skill:
                    specialties_by_skill[skill_name] = []
                specialties_by_skill[skill_name].append(spec['specialty_name'])
            
            for skill_name in all_skills:
                skill_dots = next((s['dots'] for s in skills if s['skill_name'] == skill_name), 0)
                if skill_dots > 0:
                    trained_skills.append(skill_name)
                    dots = "●" * skill_dots + "○" * (5 - skill_dots)
                    skill_line = f"**{skill_name}:** {dots} ({skill_dots})"
                    
                    # Add specialties if any
                    if skill_name in specialties_by_skill:
                        specialty_list = ", ".join(specialties_by_skill[skill_name])
                        skill_line += f"\n*Specialties: {specialty_list}*"
                    
                    skill_text.append(skill_line)
            
            # If less than 5 trained skills, add key reference skills at 0
            if len(trained_skills) < 5:
                for skill_name in key_skills:
                    if skill_name not in trained_skills:
                        dots = "○" * 5  # All empty circles
                        skill_text.append(f"**{skill_name}:** {dots} (0)")
            
            if skill_text:
                # Handle long skill lists with specialties
                full_text = "\n".join(skill_text)
                if len(full_text) <= 1024:
                    embed.add_field(
                        name="🔧 __Skills__",
                        value=full_text,
                        inline=False
                    )
                else:
                    # Split into chunks for long lists
                    chunks = []
                    current_chunk = []
                    current_length = 0
                    
                    for line in skill_text:
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
                        field_name = "🔧 __Skills__" if i == 0 else f"🔧 __Skills__ (cont. {i+1})"
                        embed.add_field(name=field_name, value=chunk, inline=False)

            # Page break before Hunter Mechanics
            embed.add_field(name="\u200b", value="═══════════════════════", inline=False)

            # H5E Mechanics (Creed first, then Desperation, then Ambition/Desire/Drive)
            h5e_mechanics = []
            
            # Creed
            creed = character['creed'] if character['creed'] else None
            creed_display = creed if creed else "*No Creed Set*"
            h5e_mechanics.append(f"**Creed:** {creed_display}")
            
            # Desperation (with anger symbols and white squares)
            desperation = safe_get_character_field(character, 'desperation', 0)
            desperation_meters = "💢" * desperation + "▫️" * (10 - desperation)
            h5e_mechanics.append(f"**Desperation:** {desperation}/10\n{desperation_meters}")
            
            # Core H5E character mechanics
            ambition = safe_get_character_field(character, 'ambition', '')
            desire = safe_get_character_field(character, 'desire', '')
            drive = safe_get_character_field(character, 'drive', '')
            redemption = safe_get_character_field(character, 'redemption', '')
            
            if ambition:
                h5e_mechanics.append(f"**Ambition:** {ambition}")
            if desire:
                h5e_mechanics.append(f"**Desire:** {desire}")
            if drive:
                drive_text = f"**Drive:** {drive}"
                if redemption:
                    drive_text += f"\n*Redemption:* {redemption}"
                h5e_mechanics.append(drive_text)
            
            embed.add_field(
                name="__Hunter Mechanics__",
                value="\n\n".join(h5e_mechanics),
                inline=False
            )

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            logger.error(f"Error displaying character sheet: {e}")
            await interaction.response.send_message(
                f"❌ Error loading character sheet: {str(e)}", ephemeral=True
            )

    # Autocomplete functions
    @delete_character.autocomplete('name')
    @rename_character.autocomplete('old_name') 
    @character_sheet.autocomplete('name')
    async def management_character_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> List[app_commands.Choice[str]]:
        """Autocomplete character names for management commands"""
        return await character_autocomplete(interaction, current)


async def setup(bot: commands.Bot):
    """Setup function for the Character Management cog"""
    cog = CharacterManagement(bot)
    await bot.add_cog(cog)
    
    # Only register guild commands if GUILD_ID is set (development mode)
    if GUILD_ID:
        for command in cog.get_app_commands():
            bot.tree.add_command(command, guild=discord.Object(id=GUILD_ID))
        logger.info(f"Character Management cog loaded with {len(cog.get_app_commands())} guild commands")
    else:
        logger.info(f"Character Management cog loaded with {len(cog.get_app_commands())} global commands")
