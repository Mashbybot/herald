"""
Shared utilities for Herald character management system.
Contains common functions used across multiple character cogs.
Enhanced with unified UX/UI system for consistent user experience.
"""

import discord
import logging
from typing import Optional, List, Tuple
from discord import app_commands
from core.db import get_db_connection

logger = logging.getLogger('Herald.Character.Utils')

# ===== UNIFIED EMOJI SYSTEM =====

class HeraldEmojis:
    """Centralized emoji system for consistent Herald bot styling"""
    
    # Status & Results
    SUCCESS = "✅"
    ERROR = "❌"
    WARNING = "⚠️"
    INFO = "ℹ️"
    LOADING = "⏳"
    NEW = "✨"
    
    # Health & Damage (Distinct from Willpower)
    HEALTH_FULL = "💚"
    HEALTH_SUPERFICIAL = "🧡" 
    HEALTH_AGGRAVATED = "💔"
    HEALTH_EMPTY = "🖤"
    
    # Willpower (Different colors for clarity)
    WILLPOWER_FULL = "🟢"
    WILLPOWER_SUPERFICIAL = "🟠"
    WILLPOWER_AGGRAVATED = "⭕"
    WILLPOWER_EMPTY = "⚫"
    
    # H5E Mechanics
    EDGE = "⚡"
    EDGE_EMPTY = "🔹"
    DESPERATION = "😰"
    DESPERATION_EMPTY = "⬜"
    
    # Attributes
    PHYSICAL = "💪"
    SOCIAL = "🗣️" 
    MENTAL = "🧠"
    
    # Character Elements
    CREED = "⚖️"
    AMBITION = "🎯"
    DESIRE = "💫"
    DRIVE = "🔥"
    REDEMPTION = "🕊️"
    
    # Skills & Progression
    SKILL_FILLED = "●"
    SKILL_EMPTY = "○"
    SPECIALTY = "🎯"
    XP = "⭐"
    
    # Equipment & Notes
    EQUIPMENT = "🎒"
    NOTES = "📝"
    
    # Dice Rolling
    DICE = "🎲"
    CRITICAL = "💥"
    SUCCESS_DIE = "🎯"
    
    # Visual Separators
    SEPARATOR = "━━━━━━━━━━━━━━━━━━━━━━"
    DIVIDER = "▫️"


# ===== ENHANCED MESSAGE SYSTEM =====

class HeraldMessages:
    """Centralized user-friendly messages with actionable suggestions"""
    
    @staticmethod
    async def character_not_found(user_id: str, character_name: str) -> str:
        """Enhanced character not found message with suggestions"""
        # Get user's characters for suggestions
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT name FROM characters WHERE user_id = ? ORDER BY name", (user_id,))
            user_characters = [row['name'] for row in cur.fetchall()]
            conn.close()
        except:
            user_characters = []
        
        base_msg = f"{HeraldEmojis.WARNING} Character **{character_name}** not found."
        
        if user_characters:
            if len(user_characters) == 1:
                suggestion = f"\n💡 Did you mean **{user_characters[0]}**?"
            elif len(user_characters) <= 3:
                names = "**, **".join(user_characters)
                suggestion = f"\n💡 Your characters: **{names}**"
            else:
                suggestion = f"\n💡 Use `/characters` to see your {len(user_characters)} characters"
        else:
            suggestion = f"\n💡 Create your first character with `/create name:\"Character Name\"`"
        
        return base_msg + suggestion
    
    @staticmethod
    def xp_insufficient(needed: int, available: int, improvement: str) -> str:
        """Enhanced XP insufficient message"""
        shortfall = needed - available
        return (
            f"{HeraldEmojis.ERROR} Need **{needed} XP** to improve {improvement}.\n"
            f"💰 You have **{available} XP** available.\n"
            f"💡 You need **{shortfall} more XP**. Use `/xp action:add amount:{shortfall}` to add more."
        )
    
    @staticmethod
    def skill_at_maximum(skill_name: str, current_dots: int) -> str:
        """Enhanced skill maximum message"""
        return (
            f"{HeraldEmojis.WARNING} **{skill_name}** is already at maximum ({current_dots} dots).\n"
            f"💡 Consider adding specialties with `/specialty action:add skill:{skill_name} specialty:\"Your Focus\"`"
        )
    
    @staticmethod
    def operation_success(title: str, description: str) -> str:
        """Standardized success message"""
        return f"{HeraldEmojis.SUCCESS} **{title}**\n{description}"
    
    @staticmethod
    def operation_failed(title: str, error: str, suggestion: str = None) -> str:
        """Standardized error message"""
        msg = f"{HeraldEmojis.ERROR} **{title}**\n{error}"
        if suggestion:
            msg += f"\n💡 {suggestion}"
        return msg


# ===== H5E SKILLS SYSTEM =====

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


# ===== ENHANCED VISUAL DISPLAY FUNCTIONS =====

def create_health_bar(current_max: int, superficial: int, aggravated: int, max_possible: int = 8) -> str:
    """Create health bar with consistent emoji system"""
    undamaged = max(0, current_max - superficial - aggravated)
    potential = max(0, max_possible - current_max)
    
    return (
        HeraldEmojis.HEALTH_FULL * undamaged +
        HeraldEmojis.HEALTH_SUPERFICIAL * superficial +
        HeraldEmojis.HEALTH_AGGRAVATED * aggravated +
        HeraldEmojis.HEALTH_EMPTY * potential
    )

def create_willpower_bar(current_max: int, superficial: int, aggravated: int, max_possible: int = 10) -> str:
    """Create willpower bar with distinct emoji system"""
    undamaged = max(0, current_max - superficial - aggravated)
    potential = max(0, max_possible - current_max)
    
    return (
        HeraldEmojis.WILLPOWER_FULL * undamaged +
        HeraldEmojis.WILLPOWER_SUPERFICIAL * superficial +
        HeraldEmojis.WILLPOWER_AGGRAVATED * aggravated +
        HeraldEmojis.WILLPOWER_EMPTY * potential
    )

def create_edge_bar(edge: int, max_edge: int = 5) -> str:
    """Create edge rating display"""
    return (
        HeraldEmojis.EDGE * edge + 
        HeraldEmojis.EDGE_EMPTY * (max_edge - edge)
    )

def create_desperation_bar(desperation: int, max_desperation: int = 10) -> str:
    """Create desperation level display"""
    return (
        HeraldEmojis.DESPERATION * desperation + 
        HeraldEmojis.DESPERATION_EMPTY * (max_desperation - desperation)
    )

def create_skill_display(dots: int, max_dots: int = 5) -> str:
    """Create skill dots display"""
    return (
        HeraldEmojis.SKILL_FILLED * dots + 
        HeraldEmojis.SKILL_EMPTY * (max_dots - dots)
    )

# Legacy functions for backward compatibility (will be phased out)
def damage_bar(current_max: int, superficial: int, aggravated: int, absolute_max: int = 8) -> str:
    """Legacy damage bar - use create_health_bar instead"""
    logger.warning("damage_bar() is deprecated, use create_health_bar() instead")
    return create_health_bar(current_max, superficial, aggravated, absolute_max)

def willpower_bar(current_max: int, superficial: int, aggravated: int, absolute_max: int = 10) -> str:
    """Legacy willpower bar - use create_willpower_bar instead"""
    logger.warning("willpower_bar() is deprecated, use create_willpower_bar() instead")
    return create_willpower_bar(current_max, superficial, aggravated, absolute_max)

def create_desperation_bar_legacy(desperation: int) -> str:
    """Legacy desperation bar - use create_desperation_bar instead"""
    logger.warning("create_desperation_bar_legacy() is deprecated, use create_desperation_bar() instead")
    filled = "🔴" * desperation  # Fixed encoding
    empty = "⚫" * (10 - desperation)  # Fixed encoding
    return f"`[{filled}{empty}]` {desperation}/10"


# ===== ENHANCED EMBED CREATION FUNCTIONS =====

def create_success_embed(title: str, description: str, details: str = None, color: int = 0x228B22) -> discord.Embed:
    """Standardized success message embed"""
    embed = discord.Embed(
        title=f"{HeraldEmojis.SUCCESS} {title}",
        description=description,
        color=color
    )
    
    if details:
        embed.add_field(name="Details", value=details, inline=False)
    
    return embed

def create_error_embed(title: str, description: str, suggestion: str = None, color: int = 0x8B0000) -> discord.Embed:
    """Standardized error message embed"""
    embed = discord.Embed(
        title=f"{HeraldEmojis.ERROR} {title}",
        description=description,
        color=color
    )
    
    if suggestion:
        embed.add_field(name="💡 Suggestion", value=suggestion, inline=False)
    
    return embed

def create_info_embed(title: str, description: str, color: int = 0x4169E1) -> discord.Embed:
    """Standardized info message embed"""
    return discord.Embed(
        title=f"{HeraldEmojis.INFO} {title}",
        description=description,
        color=color
    )

def create_warning_embed(title: str, description: str, suggestion: str = None, color: int = 0xFF8C00) -> discord.Embed:
    """Standardized warning message embed"""
    embed = discord.Embed(
        title=f"{HeraldEmojis.WARNING} {title}",
        description=description,
        color=color
    )
    
    if suggestion:
        embed.add_field(name="💡 Tip", value=suggestion, inline=False)
    
    return embed


# ===== ENHANCED CHARACTER SHEET CREATION =====

def create_enhanced_character_sheet(character: dict, skills: List[dict]) -> discord.Embed:
    """Create an enhanced, visually appealing character sheet"""
    
    name = character.get('name', 'Unknown')
    concept = character.get('concept', 'Hunter of the Supernatural')
    creed = character.get('creed', 'No creed set')
    
    # Create main embed with Herald theme
    embed = discord.Embed(
        title=f"🏹 {name}",
        description=f"*{concept}*",
        color=0x8B0000  # Dark red theme for Hunter
    )
    
    # === CORE STATS (Top Priority) ===
    health_current = character.get('health', 0)
    health_sup = character.get('health_sup', 0)
    health_agg = character.get('health_agg', 0)
    health_bar = create_health_bar(health_current, health_sup, health_agg)
    
    willpower_current = character.get('willpower', 0)
    willpower_sup = character.get('willpower_sup', 0)
    willpower_agg = character.get('willpower_agg', 0)
    willpower_bar = create_willpower_bar(willpower_current, willpower_sup, willpower_agg)
    
    # Side-by-side layout for health/willpower
    embed.add_field(
        name=f"{HeraldEmojis.HEALTH_FULL} Health",
        value=f"{health_bar}\n`{health_current - health_sup - health_agg}/{health_current} remaining`",
        inline=True
    )
    embed.add_field(
        name=f"{HeraldEmojis.WILLPOWER_FULL} Willpower",
        value=f"{willpower_bar}\n`{willpower_current - willpower_sup - willpower_agg}/{willpower_current} remaining`",
        inline=True
    )
    
    # Edge and Desperation on same row
    edge = character.get('edge', 0)
    desperation = character.get('desperation', 0)
    
    edge_display = create_edge_bar(edge)
    desperation_display = create_desperation_bar(desperation)
    
    embed.add_field(
        name=f"{HeraldEmojis.EDGE} Edge",
        value=f"{edge_display}\n`{edge}/5`",
        inline=True
    )
    embed.add_field(
        name=f"{HeraldEmojis.DESPERATION} Desperation",
        value=f"{desperation_display}\n`{desperation}/10`",
        inline=True
    )
    
    # Add creed in remaining space
    embed.add_field(
        name=f"{HeraldEmojis.CREED} Creed",
        value=creed,
        inline=True
    )
    
    # Add visual separator
    embed.add_field(name=HeraldEmojis.SEPARATOR, value="", inline=False)
    
    # === ATTRIBUTES (Compact 3-column layout) ===
    physical_attrs = [
        f"**Strength:** {character.get('strength', 1)}",
        f"**Dexterity:** {character.get('dexterity', 1)}",
        f"**Stamina:** {character.get('stamina', 1)}"
    ]
    
    social_attrs = [
        f"**Charisma:** {character.get('charisma', 1)}",
        f"**Manipulation:** {character.get('manipulation', 1)}",
        f"**Composure:** {character.get('composure', 1)}"
    ]
    
    mental_attrs = [
        f"**Intelligence:** {character.get('intelligence', 1)}",
        f"**Wits:** {character.get('wits', 1)}",
        f"**Resolve:** {character.get('resolve', 1)}"
    ]
    
    embed.add_field(
        name=f"{HeraldEmojis.PHYSICAL} Physical",
        value="\n".join(physical_attrs),
        inline=True
    )
    embed.add_field(
        name=f"{HeraldEmojis.SOCIAL} Social",
        value="\n".join(social_attrs),
        inline=True
    )
    embed.add_field(
        name=f"{HeraldEmojis.MENTAL} Mental",
        value="\n".join(mental_attrs),
        inline=True
    )
    
    # === SKILLS (Smart display with specialties integration) ===
    if skills:
        # Get skills with dots > 0
        trained_skills = [skill for skill in skills if skill['dots'] > 0]
        
        if trained_skills:
            skill_text = []
            for skill in trained_skills[:15]:  # Limit to prevent overflow
                dots = skill['dots']
                skill_display = create_skill_display(dots)
                skill_text.append(f"**{skill['skill_name']}:** {skill_display} `{dots}`")
            
            # Handle long skill lists
            skills_display = "\n".join(skill_text)
            if len(trained_skills) > 15:
                skills_display += f"\n*...and {len(trained_skills) - 15} more*"
            
            embed.add_field(
                name="🎯 Trained Skills",
                value=skills_display,
                inline=False
            )
    
    # === HUNTER MECHANICS ===
    h5e_mechanics = []
    
    if character.get('ambition'):
        h5e_mechanics.append(f"{HeraldEmojis.AMBITION} **Ambition:** {character['ambition']}")
    if character.get('desire'):
        h5e_mechanics.append(f"{HeraldEmojis.DESIRE} **Desire:** {character['desire']}")
    if character.get('drive'):
        drive_text = f"{HeraldEmojis.DRIVE} **Drive:** {character['drive']}"
        if character.get('redemption'):
            drive_text += f"\n{HeraldEmojis.REDEMPTION} *Redemption:* {character['redemption']}"
        h5e_mechanics.append(drive_text)
    
    if h5e_mechanics:
        embed.add_field(
            name="🎭 Hunter Traits",
            value="\n\n".join(h5e_mechanics),
            inline=False
        )
    
    # Footer with helpful tips
    embed.set_footer(text="💡 Use /damage and /heal to manage health • Use /edge and /desperation for H5E mechanics")
    
    return embed


# ===== DATABASE HELPER FUNCTIONS =====

async def find_character(user_id: str, character_name: str) -> Optional[dict]:
    """
    Helper function to find character with fuzzy name matching.
    Enhanced with better error handling and logging.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
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
        
        return character
        
    except Exception as e:
        logger.error(f"Error finding character '{character_name}' for user {user_id}: {e}")
        return None
    finally:
        conn.close()

async def get_character_and_skills(user_id: str, character_name: str) -> Tuple[Optional[dict], List[dict]]:
    """
    Helper function to get character and skills data with fuzzy name matching.
    Enhanced with better error handling.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
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
                "SELECT skill_name, dots FROM skills WHERE user_id = ? AND character_name = ? ORDER BY dots DESC, skill_name",
                (user_id, character['name'])
            )
            skills = cur.fetchall()
        
        return character, skills
        
    except Exception as e:
        logger.error(f"Error getting character and skills for '{character_name}' (user {user_id}): {e}")
        return None, []
    finally:
        conn.close()

async def get_character_attribute(user_id: str, character_name: str, attribute: str) -> Optional[int]:
    """
    Get a specific attribute value for a character (for roll integration).
    Enhanced with better error handling.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute(f"SELECT {attribute.lower()} FROM characters WHERE user_id = ? AND name = ?", (user_id, character_name))
        result = cur.fetchone()
        conn.close()
        
        return result[attribute.lower()] if result else None
    except Exception as e:
        logger.error(f"Error getting attribute {attribute} for character '{character_name}' (user {user_id}): {e}")
        return None

async def get_character_skill(user_id: str, character_name: str, skill_name: str) -> Optional[int]:
    """
    Get a specific skill value for a character (for roll integration).
    Enhanced with better error handling.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT dots FROM skills WHERE user_id = ? AND character_name = ? AND skill_name = ?", 
                   (user_id, character_name, skill_name))
        result = cur.fetchone()
        conn.close()
        
        return result['dots'] if result else None
    except Exception as e:
        logger.error(f"Error getting skill {skill_name} for character '{character_name}' (user {user_id}): {e}")
        return None

async def character_autocomplete(interaction, current: str) -> List[app_commands.Choice[str]]:
    """
    Standard character name autocomplete for commands.
    Enhanced with better error handling and logging.
    """
    try:
        user_id = str(interaction.user.id)
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT name FROM characters WHERE user_id = ? ORDER BY name", (user_id,))
        characters = cur.fetchall()
        conn.close()
        
        # Filter based on current input
        filtered = [
            char['name'] for char in characters 
            if current.lower() in char['name'].lower()
        ]
        
        return [
            app_commands.Choice(name=char_name, value=char_name)
            for char_name in filtered[:25]  # Discord limit
        ]
    except Exception as e:
        logger.error(f"Error in character autocomplete for user {interaction.user.id}: {e}")
        return []

def ensure_h5e_columns():
    """
    Ensure all H5E mechanics columns exist in the characters table.
    Enhanced with better error handling.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check existing columns
        cur.execute("PRAGMA table_info(characters)")
        columns = [row[1] for row in cur.fetchall()]
        
        # H5E mechanics columns
        h5e_columns = {
            'ambition': 'TEXT DEFAULT NULL',
            'desire': 'TEXT DEFAULT NULL', 
            'drive': 'TEXT DEFAULT NULL',
            'redemption': 'TEXT DEFAULT NULL'
        }
        
        # Add missing columns
        for column, definition in h5e_columns.items():
            if column not in columns:
                logger.info(f"Adding {column} column to characters table")
                cur.execute(f"ALTER TABLE characters ADD COLUMN {column} {definition}")
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        logger.error(f"Error ensuring H5E columns: {e}")
        raise


# ===== LOADING INDICATOR HELPER =====

async def with_loading_indicator(interaction: discord.Interaction, operation_func, loading_message: str = "Processing..."):
    """Add loading indicator for operations that might take time"""
    try:
        # Send initial loading message
        await interaction.response.send_message(
            f"{HeraldEmojis.LOADING} {loading_message}", 
            ephemeral=True
        )
        
        # Perform the operation
        result = await operation_func()
        
        # Edit with final result
        if isinstance(result, discord.Embed):
            await interaction.edit_original_response(content=None, embed=result)
        else:
            await interaction.edit_original_response(content=result)
            
        return result
        
    except Exception as e:
        error_msg = f"{HeraldEmojis.ERROR} Operation failed: {str(e)}"
        await interaction.edit_original_response(content=error_msg)
        logger.error(f"Loading indicator operation failed: {e}")
        raise
