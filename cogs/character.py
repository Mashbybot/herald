import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional, List, Tuple
import logging

from core.db import get_db_connection
from config.settings import GUILD_ID

logger = logging.getLogger('Herald.Character')

# H5E Skills organized by category
H5E_SKILLS = {
    "Physical": [
        "Athletics", "Brawl", "Craft", "Driving", "Firearms",
        "Larceny", "Melee", "Stealth", "Survival"
    ],
    "Social": [
        "Animal Ken", "Etiquette", "Insight", "Intimidation", "Leadership",
        "Performance", "Persuasion", "Streetwise", "Subterfuge"
    ],
    "Mental": [
        "Academics", "Awareness", "Finance", "Investigation", "Medicine",
        "Occult", "Politics", "Science", "Technology"
    ]
}

# Flatten for backward compatibility
ALL_SKILLS = [skill for category in H5E_SKILLS.values() for skill in category]

def damage_bar(current_max: int, superficial: int, aggravated: int, absolute_max: int = 8) -> str:
    """Create visual damage bar showing current capacity + potential capacity"""
    undamaged = max(0, current_max - superficial - aggravated)
    potential_slots = max(0, absolute_max - current_max)
    return (
        "💚" * undamaged +
        "🧡" * superficial +
        "💔" * aggravated +
        "▪️" * potential_slots
    )

def willpower_bar(current_max: int, superficial: int, aggravated: int, absolute_max: int = 10) -> str:
    """Create visual willpower bar showing current capacity + potential capacity"""
    undamaged = max(0, current_max - superficial - aggravated)
    potential_slots = max(0, absolute_max - current_max)
    return (
        "🟢" * undamaged +
        "🟠" * superficial +
        "⭕" * aggravated +
        "▪️" * potential_slots
    )

class Character(commands.Cog):
    """Hunter: The Reckoning 5th Edition character management"""
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger('Herald.Character')

    async def _find_character(self, user_id: str, character_name: str) -> Optional[dict]:
        """Helper function to find character with fuzzy name matching"""
        conn = get_db_connection()
        cur = conn.cursor()
        
        # First try exact match
        cur.execute("SELECT * FROM characters WHERE user_id = ? AND name = ?", (user_id, character_name))
        character = cur.fetchone()
        
        # If no exact match, try case-insensitive fuzzy matching
        if not character:
            cur.execute("SELECT * FROM characters WHERE user_id = ?", (user_id,))
            all_chars = cur.fetchall()
            
            # Find best match (case-insensitive)
            for char in all_chars:
                if char['name'].lower() == character_name.lower():
                    character = char
                    break
        
        conn.close()
        return character

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
        
        try:
            conn = get_db_connection()
            cur = conn.cursor()

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

            # Create character
            cur.execute("""
                INSERT INTO characters (
                    user_id, name,
                    strength, dexterity, stamina,
                    charisma, manipulation, composure,
                    intelligence, wits, resolve,
                    health, willpower,
                    health_sup, health_agg,
                    willpower_sup, willpower_agg
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0, 0)
            """, (
                user_id, name,
                strength, dexterity, stamina,
                charisma, manipulation, composure,
                intelligence, wits, resolve,
                health, willpower
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
            
            embed.set_footer(text="Use /skill_set to assign skill dots • Use /sheet to view full character")

            await interaction.response.send_message(embed=embed)
            logger.info(f"Created character '{name}' for user {user_id}")

        except Exception as e:
            logger.error(f"Error creating character: {e}")
            await interaction.response.send_message(
                f"❌ Error creating character: {str(e)}", ephemeral=True
            )

    @app_commands.command(name="sheet", description="View your Hunter character sheet")
    @app_commands.describe(name="Character name (autocompletes to your characters)")
    async def character_sheet(self, interaction: discord.Interaction, name: str):
        """Display a character sheet with full details"""
        user_id = str(interaction.user.id)
        
        try:
            character, skills = await self._get_character_and_skills(user_id, name)
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
            health_bar = damage_bar(character['health'], character['health_sup'], character['health_agg'], 8)
            # Willpower: max possible is 10 (5 resolve + 5 composure)  
            willpower_display = willpower_bar(character['willpower'], character['willpower_sup'], character['willpower_agg'], 10)
            
            # Edge formatting with black squares for empty
            edge = character['edge'] if character['edge'] is not None else 0
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

            # Skills (all categories combined, smart display logic)
            all_skills = []
            for category in H5E_SKILLS.values():
                all_skills.extend(category)
            
            # Key skills to show as reference when character has few trained skills
            key_skills = ["Athletics", "Brawl", "Firearms", "Stealth", "Intimidation", "Persuasion", "Subterfuge", "Insight", "Investigation", "Occult", "Awareness", "Medicine"]
            
            # Get all trained skills (> 0 dots)
            trained_skills = []
            skill_text = []
            
            for skill_name in all_skills:
                skill_dots = next((s['dots'] for s in skills if s['skill_name'] == skill_name), 0)
                if skill_dots > 0:
                    trained_skills.append(skill_name)
                    dots = "●" * skill_dots + "○" * (5 - skill_dots)
                    skill_text.append(f"**{skill_name}:** {dots} ({skill_dots})")
            
            # If less than 5 trained skills, add key reference skills at 0
            if len(trained_skills) < 5:
                for skill_name in key_skills:
                    if skill_name not in trained_skills:
                        dots = "○" * 5  # All empty circles
                        skill_text.append(f"**{skill_name}:** {dots} (0)")
            
            if skill_text:
                embed.add_field(
                    name="🔧 __Skills__",
                    value="\n".join(skill_text),
                    inline=False
                )

            # Page break before Hunter Mechanics
            embed.add_field(name="\u200b", value="═══════════════════════", inline=False)

            # H5E Mechanics (Creed first, then Desperation)
            h5e_mechanics = []
            
            # Creed
            creed = character['creed']
            creed_display = creed if creed else "*No Creed Set*"
            h5e_mechanics.append(f"**Creed:** {creed_display}")
            
            # Desperation (with anger symbols and white squares)
            desperation = character['desperation'] if character['desperation'] is not None else 0
            desperation_meters = "💢" * desperation + "▫️" * (10 - desperation)
            h5e_mechanics.append(f"**Desperation:** {desperation}/10\n{desperation_meters}")
            
            embed.add_field(
                name="__Hunter Mechanics__",
                value="\n".join(h5e_mechanics),
                inline=False
            )

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            logger.error(f"Error displaying character sheet: {e}")
            await interaction.response.send_message(
                f"❌ Error loading character sheet: {str(e)}", ephemeral=True
            )

    @app_commands.command(name="skill_set", description="Set dots for a skill on your character")
    @app_commands.describe(
        character_name="Character name",
        skill="Skill to update",
        dots="Skill rating (0-5)"
    )
    @app_commands.choices(skill=[
        app_commands.Choice(name=skill, value=skill)
        for skill in ALL_SKILLS[:25]  # Discord limit
    ])
    async def skill_set(
        self,
        interaction: discord.Interaction,
        character_name: str,
        skill: str,
        dots: int,
    ):
        """Set skill dots for a character"""
        user_id = str(interaction.user.id)
        dots = max(0, min(dots, 5))  # Clamp to valid range

        try:
            conn = get_db_connection()
            cur = conn.cursor()

            # Verify character exists
            cur.execute("SELECT name FROM characters WHERE user_id = ? AND name = ?", (user_id, character_name))
            if not cur.fetchone():
                await interaction.response.send_message(
                    f"⚠️ Character **{character_name}** not found", ephemeral=True
                )
                conn.close()
                return

            # Update skill
            cur.execute(
                "UPDATE skills SET dots = ? WHERE user_id = ? AND character_name = ? AND skill_name = ?",
                (dots, user_id, character_name, skill)
            )
            
            if cur.rowcount == 0:
                await interaction.response.send_message(
                    f"⚠️ Skill **{skill}** not found on **{character_name}**", ephemeral=True
                )
                conn.close()
                return

            conn.commit()
            conn.close()

            # Success response
            dots_display = "●" * dots + "○" * (5 - dots)
            await interaction.response.send_message(
                f"✅ **{character_name}**'s **{skill}** set to {dots_display} ({dots} dots)",
                ephemeral=True
            )
            logger.info(f"Updated {character_name}'s {skill} to {dots} dots for user {user_id}")

        except Exception as e:
            logger.error(f"Error setting skill: {e}")
            await interaction.response.send_message(
                f"❌ Error updating skill: {str(e)}", ephemeral=True
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

    @app_commands.command(name="edge", description="View or modify your character's Edge rating")
    @app_commands.describe(
        character="Character name",
        action="What to do with Edge",
        amount="Amount to add/subtract/set (optional for 'view')"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="View", value="view"),
        app_commands.Choice(name="Set", value="set"),
        app_commands.Choice(name="Add", value="add"),
        app_commands.Choice(name="Subtract", value="subtract")
    ])
    async def edge(self, interaction: discord.Interaction, character: str, action: str, amount: int = None):
        """Manage character Edge ratings (0-5)"""
        
        user_id = str(interaction.user.id)
        
        try:
            conn = get_db_connection()
            
            # Get character
            char = conn.execute("""
                SELECT name, edge 
                FROM characters 
                WHERE user_id = ? AND name = ?
            """, (user_id, character)).fetchone()
            
            if not char:
                await interaction.response.send_message(f"⚠️ No character named **{character}** found", ephemeral=True)
                return
            
            current_edge = char['edge'] or 0
            
            # Handle different actions
            if action == "view":
                # Create edge display
                edge_dots = "⚡" * current_edge + "○" * (5 - current_edge)
                
                embed = discord.Embed(
                    title=f"⚡ {char['name']}'s Edge",
                    description=f"**Current Rating:** {current_edge}/5\n{edge_dots}",
                    color=0xFFD700 if current_edge >= 3 else 0x4169E1
                )
                
                # Add Edge benefits info
                if current_edge > 0:
                    embed.add_field(
                        name="💡 Edge Benefits", 
                        value=f"• Add {current_edge} dice to Danger rolls\n• Enhanced supernatural resistance\n• Improved Hunter abilities", 
                        inline=False
                    )
                
                await interaction.response.send_message(embed=embed)
                
            else:
                # Actions that modify edge require amount
                if amount is None:
                    await interaction.response.send_message(f"⚠️ Amount required for **{action}** action", ephemeral=True)
                    return
                
                # Calculate new edge
                if action == "set":
                    new_edge = amount
                elif action == "add":
                    new_edge = current_edge + amount
                elif action == "subtract":
                    new_edge = current_edge - amount
                
                # Validate range (0-5)
                new_edge = max(0, min(5, new_edge))
                
                # Update database
                conn.execute("""
                    UPDATE characters 
                    SET edge = ? 
                    WHERE user_id = ? AND name = ?
                """, (new_edge, user_id, character))
                conn.commit()
                
                # Create response
                change = new_edge - current_edge
                change_text = f"+{change}" if change > 0 else str(change) if change < 0 else "±0"
                
                edge_dots = "⚡" * new_edge + "○" * (5 - new_edge)
                
                embed = discord.Embed(
                    title=f"⚡ {char['name']}'s Edge Updated",
                    description=f"**{current_edge} → {new_edge}** ({change_text})\n{edge_dots}",
                    color=0xFFD700 if new_edge >= 3 else 0x4169E1
                )
                
                # Add note for significant changes
                if new_edge > current_edge:
                    embed.add_field(
                        name="📈 Edge Increased!", 
                        value=f"Your character now adds {new_edge} dice to Danger rolls!", 
                        inline=False
                    )
                
                await interaction.response.send_message(embed=embed)
                
        except Exception as e:
            self.logger.error(f"Error in edge command: {e}")
            await interaction.response.send_message("❌ An error occurred while managing Edge", ephemeral=True)
        finally:
            conn.close()

    @app_commands.command(name="creed", description="View or set your character's Creed")
    @app_commands.describe(
        character="Character name",
        creed="Creed name (leave empty to view current creed)"
    )
    async def creed(self, interaction: discord.Interaction, character: str, creed: str = None):
        """Manage character Creed"""
        
        user_id = str(interaction.user.id)
        
        try:
            # Use fuzzy character matching
            char = await self._find_character(user_id, character)
            
            if not char:
                await interaction.response.send_message(f"⚠️ No character named **{character}** found", ephemeral=True)
                return
            
            current_creed = char['creed']
            
            # If no creed provided, show current creed
            if creed is None:
                embed = discord.Embed(
                    title=f"🗡️ {char['name']}'s Creed",
                    color=0x8B4513
                )
                
                if current_creed:
                    embed.description = f"**Current Creed:** {current_creed}"
                    embed.add_field(
                        name="📜 About Creeds", 
                        value="Creeds define your Hunter's philosophy and approach to the supernatural. They provide moral guidance and special abilities.", 
                        inline=False
                    )
                else:
                    embed.description = "**No Creed set**"
                    embed.add_field(
                        name="💡 Set a Creed", 
                        value="Use `/creed <character> <creed_name>` to set your character's Creed.\n\nCommon Creeds: Innocent, Martyr, Redeemer, Visionary, Wayward", 
                        inline=False
                    )
                
                await interaction.response.send_message(embed=embed)
                
            else:
                # Set new creed
                # Clean up creed name (capitalize properly)
                creed = creed.strip().title()
                
                # Update database using actual character name
                conn = get_db_connection()
                conn.execute("""
                    UPDATE characters 
                    SET creed = ? 
                    WHERE user_id = ? AND name = ?
                """, (creed, user_id, char['name']))
                conn.commit()
                conn.close()
                
                # Create response
                embed = discord.Embed(
                    title=f"🗡️ {char['name']}'s Creed Updated",
                    color=0x8B4513
                )
                
                if current_creed:
                    embed.description = f"**{current_creed}** → **{creed}**"
                    embed.add_field(
                        name="🔄 Creed Changed", 
                        value=f"Your character has embraced the **{creed}** Creed!", 
                        inline=False
                    )
                else:
                    embed.description = f"**Creed Set:** {creed}"
                    embed.add_field(
                        name="✨ New Hunter", 
                        value=f"Your character has joined the **{creed}** Creed and begins their hunt!", 
                        inline=False
                    )
                
                await interaction.response.send_message(embed=embed)
                
        except Exception as e:
            self.logger.error(f"Error in creed command: {e}")
            await interaction.response.send_message("❌ An error occurred while managing Creed", ephemeral=True)

    @app_commands.command(name="desperation", description="View or modify your character's Desperation level")
    @app_commands.describe(
        character="Character name",
        action="What to do with Desperation",
        amount="Amount to add/subtract/set (optional for 'view')"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="View", value="view"),
        app_commands.Choice(name="Set", value="set"),
        app_commands.Choice(name="Add", value="add"),
        app_commands.Choice(name="Subtract", value="subtract")
    ])
    async def desperation(self, interaction: discord.Interaction, character: str, action: str, amount: int = None):
        """Manage character Desperation levels (0-10)"""
        
        user_id = str(interaction.user.id)
        
        try:
            # Use fuzzy character matching
            char = await self._find_character(user_id, character)
            
            if not char:
                await interaction.response.send_message(f"⚠️ No character named **{character}** found", ephemeral=True)
                return
            
            current_desperation = char['desperation']
            
            # Handle different actions
            if action == "view":
                # Create desperation bar
                desperation_bar = self._create_desperation_bar(current_desperation)
                
                embed = discord.Embed(
                    title=f"🌑 {char['name']}'s Desperation",
                    description=f"**Current Level:** {current_desperation}/10\n{desperation_bar}",
                    color=0x8B0000 if current_desperation >= 7 else 0xFF4500 if current_desperation >= 4 else 0x4169E1
                )
                
                # Add Desperation effects info
                if current_desperation >= 7:
                    embed.add_field(
                        name="⚠️ High Desperation Effects", 
                        value="• Rolling Desperation dice on failed rolls\n• Increased supernatural vulnerability", 
                        inline=False
                    )
                
                await interaction.response.send_message(embed=embed)
                
            else:
                # Actions that modify desperation require amount
                if amount is None:
                    await interaction.response.send_message(f"⚠️ Amount required for **{action}** action", ephemeral=True)
                    return
                
                # Calculate new desperation
                if action == "set":
                    new_desperation = amount
                elif action == "add":
                    new_desperation = current_desperation + amount
                elif action == "subtract":
                    new_desperation = current_desperation - amount
                
                # Validate range (0-10)
                new_desperation = max(0, min(10, new_desperation))
                
                # Update database using actual character name
                conn = get_db_connection()
                conn.execute("""
                    UPDATE characters 
                    SET desperation = ? 
                    WHERE user_id = ? AND name = ?
                """, (new_desperation, user_id, char['name']))
                conn.commit()
                conn.close()
                
                # Create response
                change = new_desperation - current_desperation
                change_text = f"+{change}" if change > 0 else str(change) if change < 0 else "±0"
                
                desperation_bar = self._create_desperation_bar(new_desperation)
                
                embed = discord.Embed(
                    title=f"🌑 {char['name']}'s Desperation Updated",
                    description=f"**{current_desperation} → {new_desperation}** ({change_text})\n{desperation_bar}",
                    color=0x8B0000 if new_desperation >= 7 else 0xFF4500 if new_desperation >= 4 else 0x4169E1
                )
                
                # Add warning for high desperation
                if new_desperation >= 7 and current_desperation < 7:
                    embed.add_field(
                        name="⚠️ High Desperation!", 
                        value="Your character is now rolling Desperation dice on failed rolls!", 
                        inline=False
                    )
                
                await interaction.response.send_message(embed=embed)
                
        except Exception as e:
            self.logger.error(f"Error in desperation command: {e}")
            await interaction.response.send_message("❌ An error occurred while managing Desperation", ephemeral=True)

    def _create_desperation_bar(self, desperation: int) -> str:
        """Create a visual desperation bar (0-10)"""
        filled = "🔴" * desperation
        empty = "⚫" * (10 - desperation)
        return f"`[{filled}{empty}]` {desperation}/10"

    @app_commands.command(name="damage", description="Apply health or willpower damage to your character")
    @app_commands.describe(
        character="Character name",
        track="Damage track (health or willpower)",
        amount="Amount of damage to apply",
        damage_type="Type of damage (superficial or aggravated)"
    )
    @app_commands.choices(
        track=[
            app_commands.Choice(name="Health", value="health"),
            app_commands.Choice(name="Willpower", value="willpower")
        ],
        damage_type=[
            app_commands.Choice(name="Superficial", value="superficial"),
            app_commands.Choice(name="Aggravated", value="aggravated")
        ]
    )
    async def apply_damage(
        self,
        interaction: discord.Interaction,
        character: str,
        track: str,
        amount: int,
        damage_type: str = "superficial"
    ):
        """Apply damage to a character's health or willpower"""
        user_id = str(interaction.user.id)
        
        if amount < 1:
            await interaction.response.send_message("❌ Damage amount must be positive", ephemeral=True)
            return

        try:
            # Use fuzzy character matching
            char = await self._find_character(user_id, character)
            
            if not char:
                await interaction.response.send_message(f"⚠️ Character **{character}** not found", ephemeral=True)
                return

            # Determine fields to update
            if track == "health":
                max_track = char['health']
                sup_field = 'health_sup'
                agg_field = 'health_agg'
                current_sup = char['health_sup']
                current_agg = char['health_agg']
                track_emoji = "💚"
            else:  # willpower
                max_track = char['willpower']
                sup_field = 'willpower_sup'
                agg_field = 'willpower_agg'
                current_sup = char['willpower_sup']
                current_agg = char['willpower_agg']
                track_emoji = "🧠"

            # Calculate new damage totals
            if damage_type == "superficial":
                new_sup = min(current_sup + amount, max_track - current_agg)
                new_agg = current_agg
            else:  # aggravated
                # Aggravated damage converts superficial to aggravated
                new_agg = min(current_agg + amount, max_track)
                new_sup = max(0, current_sup - amount)  # Reduced by converted damage

            # Update database using actual character name
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(f"UPDATE characters SET {sup_field} = ?, {agg_field} = ? WHERE user_id = ? AND name = ?",
                       (new_sup, new_agg, user_id, char['name']))
            conn.commit()
            conn.close()

            # Create response
            remaining = max_track - new_sup - new_agg
            damage_bar_display = damage_bar(max_track, new_sup, new_agg, 8 if track == "health" else 10)
            
            embed = discord.Embed(
                title=f"💥 Damage Applied",
                description=f"**{char['name']}** takes {amount} {damage_type} {track} damage",
                color=0x8B0000
            )
            
            embed.add_field(
                name=f"{track_emoji} {track.title()}",
                value=f"{damage_bar_display}\n{remaining}/{max_track} remaining",
                inline=False
            )

            if remaining == 0:
                if track == "health":
                    embed.add_field(name="💀 Incapacitated!", value="Character is unconscious and dying", inline=False)
                else:
                    embed.add_field(name="😵 Willpower Broken!", value="Character cannot spend willpower", inline=False)

            await interaction.response.send_message(embed=embed)
            logger.info(f"Applied {amount} {damage_type} {track} damage to {char['name']} for user {user_id}")

        except Exception as e:
            logger.error(f"Error applying damage: {e}")
            await interaction.response.send_message(f"❌ Error applying damage: {str(e)}", ephemeral=True)

    @app_commands.command(name="heal", description="Heal health or willpower damage from your character")
    @app_commands.describe(
        character="Character name",
        track="Track to heal (health or willpower)",
        amount="Amount to heal",
        heal_type="Type of healing (superficial or aggravated)"
    )
    @app_commands.choices(
        track=[
            app_commands.Choice(name="Health", value="health"),
            app_commands.Choice(name="Willpower", value="willpower")
        ],
        heal_type=[
            app_commands.Choice(name="Superficial", value="superficial"),
            app_commands.Choice(name="Aggravated", value="aggravated"),
            app_commands.Choice(name="All", value="all")
        ]
    )
    async def heal_damage(
        self,
        interaction: discord.Interaction,
        character: str,
        track: str,
        amount: int,
        heal_type: str = "superficial"
    ):
        """Heal damage from a character"""
        user_id = str(interaction.user.id)
        
        if amount < 1:
            await interaction.response.send_message("❌ Heal amount must be positive", ephemeral=True)
            return

        try:
            # Use fuzzy character matching
            char = await self._find_character(user_id, character)
            
            if not char:
                await interaction.response.send_message(f"⚠️ Character **{character}** not found", ephemeral=True)
                return

            # Determine fields to update
            if track == "health":
                max_track = char['health']
                sup_field = 'health_sup'
                agg_field = 'health_agg'
                current_sup = char['health_sup']
                current_agg = char['health_agg']
                track_emoji = "💚"
            else:  # willpower
                max_track = char['willpower']
                sup_field = 'willpower_sup'
                agg_field = 'willpower_agg'  
                current_sup = char['willpower_sup']
                current_agg = char['willpower_agg']
                track_emoji = "🧠"

            # Calculate healing
            if heal_type == "all":
                new_sup = 0
                new_agg = 0
                healed_amount = current_sup + current_agg
            elif heal_type == "superficial":
                new_sup = max(0, current_sup - amount)
                new_agg = current_agg
                healed_amount = current_sup - new_sup
            else:  # aggravated
                new_agg = max(0, current_agg - amount)
                new_sup = current_sup
                healed_amount = current_agg - new_agg

            # Update database using actual character name
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(f"UPDATE characters SET {sup_field} = ?, {agg_field} = ? WHERE user_id = ? AND name = ?",
                       (new_sup, new_agg, user_id, char['name']))
            conn.commit()
            conn.close()

            # Create response
            remaining = max_track - new_sup - new_agg
            damage_bar_display = damage_bar(max_track, new_sup, new_agg, 8 if track == "health" else 10)
            
            heal_text = f"all damage" if heal_type == "all" else f"{healed_amount} {heal_type} damage"
            
            embed = discord.Embed(
                title=f"✨ Healing Applied",
                description=f"**{char['name']}** heals {heal_text}",
                color=0x228B22
            )
            
            embed.add_field(
                name=f"{track_emoji} {track.title()}",
                value=f"{damage_bar_display}\n{remaining}/{max_track} remaining",
                inline=False
            )

            await interaction.response.send_message(embed=embed)
            logger.info(f"Healed {heal_text} from {char['name']}'s {track} for user {user_id}")

        except Exception as e:
            logger.error(f"Error healing damage: {e}")
            await interaction.response.send_message(f"❌ Error healing damage: {str(e)}", ephemeral=True)

    async def _get_character_and_skills(self, user_id: str, character_name: str) -> Tuple[Optional[dict], List[dict]]:
        """Helper function to get character and skills data with fuzzy name matching"""
        conn = get_db_connection()
        cur = conn.cursor()
        
        # First try exact match
        cur.execute("SELECT * FROM characters WHERE user_id = ? AND name = ?", (user_id, character_name))
        character = cur.fetchone()
        
        # If no exact match, try case-insensitive fuzzy matching
        if not character:
            cur.execute("SELECT * FROM characters WHERE user_id = ?", (user_id,))
            all_chars = cur.fetchall()
            
            # Find best match (case-insensitive)
            best_match = None
            for char in all_chars:
                if char['name'].lower() == character_name.lower():
                    best_match = char
                    break
            
            character = best_match
        
        skills = []
        if character:
            # Get skills using the actual character name from database
            cur.execute(
                "SELECT skill_name, dots FROM skills WHERE user_id = ? AND character_name = ? ORDER BY skill_name",
                (user_id, character['name'])
            )
            skills = cur.fetchall()
        
        conn.close()
        return character, skills

    async def get_character_attribute(self, user_id: str, character_name: str, attribute: str) -> Optional[int]:
        """Get a specific attribute value for a character (for roll integration)"""
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            cur.execute(f"SELECT {attribute.lower()} FROM characters WHERE user_id = ? AND name = ?", (user_id, character_name))
            result = cur.fetchone()
            conn.close()
            
            return result[attribute.lower()] if result else None
        except Exception as e:
            logger.error(f"Error getting attribute {attribute}: {e}")
            return None

    async def get_character_skill(self, user_id: str, character_name: str, skill_name: str) -> Optional[int]:
        """Get a specific skill value for a character (for roll integration)"""
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            cur.execute("SELECT dots FROM skills WHERE user_id = ? AND character_name = ? AND skill_name = ?", 
                       (user_id, character_name, skill_name))
            result = cur.fetchone()
            conn.close()
            
            return result['dots'] if result else None
        except Exception as e:
            logger.error(f"Error getting skill {skill_name}: {e}")
            return None

async def setup(bot: commands.Bot):
    """Setup function for the Character cog"""
    cog = Character(bot)
    await bot.add_cog(cog)
    
    # Only register guild commands if GUILD_ID is set (development mode)
    if GUILD_ID:
        for command in cog.get_app_commands():
            bot.tree.add_command(command, guild=discord.Object(id=GUILD_ID))
        logger.info(f"Character cog loaded with {len(cog.get_app_commands())} guild commands")
    else:
        logger.info(f"Character cog loaded with {len(cog.get_app_commands())} global commands")
