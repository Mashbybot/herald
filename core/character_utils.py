"""
Core character utilities for Herald character management system.
Contains character database operations, caching, and business logic.
"""

import discord
import logging
from typing import Optional, List, Tuple, Dict, Any
from discord import app_commands
import time

logger = logging.getLogger('Herald.Character.Utils')


# ===== DATABASE UTILITIES =====

class DatabaseError(Exception):
    """Custom exception for database-related errors"""
    pass


# ===== CACHING SYSTEM =====

class CharacterCache:
    """Simple LRU-style cache for character data"""

    def __init__(self, max_size: int = None, ttl_seconds: int = None):
        from core.constants import CACHE_MAX_SIZE, CACHE_TTL_SECONDS

        self.cache: Dict[str, Tuple[Any, float]] = {}
        self.max_size = max_size or CACHE_MAX_SIZE
        self.ttl = ttl_seconds or CACHE_TTL_SECONDS
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached value if valid"""
        if key in self.cache:
            value, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return value
            else:
                # Expired, remove
                del self.cache[key]
        return None
    
    def set(self, key: str, value: Any):
        """Set cached value with cleanup"""
        # Simple cleanup if cache is full
        if len(self.cache) >= self.max_size:
            # Remove oldest entry
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][1])
            del self.cache[oldest_key]
        
        self.cache[key] = (value, time.time())
    
    def invalidate(self, pattern: str = None):
        """Invalidate cache entries"""
        if pattern:
            # Remove entries matching pattern
            keys_to_remove = [k for k in self.cache.keys() if pattern in k]
            for key in keys_to_remove:
                del self.cache[key]
        else:
            # Clear all
            self.cache.clear()


# Global cache instance
_character_cache = CharacterCache()


# ===== SKILLS SYSTEM =====

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


# ===== ENHANCED DATABASE FUNCTIONS =====

async def find_character(user_id: str, character_name: str) -> Optional[Dict[str, Any]]:
    """
    Find character with fuzzy name matching, caching, and enhanced error handling.
    """
    cache_key = f"char:{user_id}:{character_name.lower()}"
    cached_char = _character_cache.get(cache_key)
    
    if cached_char is not None:
        return cached_char
    
    try:
        from core.db import get_async_db
        async with get_async_db() as conn:
            # First try exact match - PostgreSQL syntax
            character = await conn.fetchrow(
                "SELECT * FROM characters WHERE user_id = $1 AND name = $2", 
                user_id, character_name
            )
            
            # If no exact match, try case-insensitive
            if not character:
                character = await conn.fetchrow(
                    "SELECT * FROM characters WHERE user_id = $1 AND LOWER(name) = LOWER($2)",
                    user_id, character_name
                )
            
            # Convert to dict and cache
            if character:
                char_dict = dict(character)
                _character_cache.set(cache_key, char_dict)
                return char_dict
            
            return None
            
    except Exception as e:
        logger.error(f"Error finding character '{character_name}' for user {user_id}: {e}")
        raise DatabaseError(f"Failed to find character: {e}")


async def get_character_and_skills(user_id: str, character_name: str) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Get character and skills with caching and enhanced error handling.
    """
    cache_key = f"char_skills:{user_id}:{character_name.lower()}"
    cached_data = _character_cache.get(cache_key)

    if cached_data is not None:
        return cached_data

    try:
        # Get character first
        character = await find_character(user_id, character_name)

        skills = []
        if character:
            from core.db import get_async_db
            async with get_async_db() as conn:
                # Get skills using PostgreSQL syntax
                skill_rows = await conn.fetch(
                    "SELECT skill_name, dots FROM skills WHERE user_id = $1 AND character_name = $2 ORDER BY dots DESC, skill_name",
                    user_id, character['name']
                )
                skills = [dict(row) for row in skill_rows]

        result = (character, skills)
        _character_cache.set(cache_key, result)
        return result

    except Exception as e:
        logger.error(f"Error getting character and skills for '{character_name}' (user {user_id}): {e}")
        raise DatabaseError(f"Failed to get character and skills: {e}")


async def get_character_edges(user_id: str, character_name: str) -> List[Dict[str, Any]]:
    """Get character's Edge abilities."""
    try:
        from core.db import get_async_db
        async with get_async_db() as conn:
            edge_rows = await conn.fetch(
                "SELECT edge_name, description FROM edges WHERE user_id = $1 AND character_name = $2 ORDER BY edge_name",
                user_id, character_name
            )
            return [dict(row) for row in edge_rows]
    except Exception as e:
        logger.error(f"Error getting edges for '{character_name}' (user {user_id}): {e}")
        return []


async def get_character_perks(user_id: str, character_name: str) -> List[Dict[str, Any]]:
    """Get character's Perk abilities."""
    try:
        from core.db import get_async_db
        async with get_async_db() as conn:
            perk_rows = await conn.fetch(
                "SELECT perk_name, description FROM perks WHERE user_id = $1 AND character_name = $2 ORDER BY perk_name",
                user_id, character_name
            )
            return [dict(row) for row in perk_rows]
    except Exception as e:
        logger.error(f"Error getting perks for '{character_name}' (user {user_id}): {e}")
        return []


async def get_character_attribute(user_id: str, character_name: str, attribute: str) -> Optional[int]:
    """Get character attribute with caching and validation."""
    from core.constants import VALID_ATTRIBUTES

    attribute_lower = attribute.lower()
    if attribute_lower not in VALID_ATTRIBUTES:
        logger.warning(f"Invalid attribute requested: {attribute}")
        return None

    cache_key = f"attr:{user_id}:{character_name.lower()}:{attribute_lower}"
    cached_value = _character_cache.get(cache_key)

    if cached_value is not None:
        return cached_value

    # Build safe SQL query using whitelist - attribute is validated above
    # We use a dict to map validated attributes to SQL columns
    try:
        from core.db import get_async_db
        async with get_async_db() as conn:
            # Fetch entire character row to avoid SQL injection risk
            result = await conn.fetchrow(
                "SELECT strength, dexterity, stamina, charisma, manipulation, composure, intelligence, wits, resolve FROM characters WHERE user_id = $1 AND name = $2",
                user_id, character_name
            )

            if result:
                value = result[attribute_lower]
                _character_cache.set(cache_key, value)
                return value

            return None

    except Exception as e:
        logger.error(f"Error getting attribute {attribute} for character '{character_name}' (user {user_id}): {e}")
        raise DatabaseError(f"Failed to get character attribute: {e}")


async def get_character_skill(user_id: str, character_name: str, skill_name: str) -> Optional[int]:
    """Get character skill with caching and validation."""
    if skill_name not in ALL_SKILLS:
        logger.warning(f"Invalid skill requested: {skill_name}")
        return None
    
    cache_key = f"skill:{user_id}:{character_name.lower()}:{skill_name}"
    cached_value = _character_cache.get(cache_key)
    
    if cached_value is not None:
        return cached_value
    
    try:
        from core.db import get_async_db
        async with get_async_db() as conn:
            result = await conn.fetchrow(
                "SELECT dots FROM skills WHERE user_id = $1 AND character_name = $2 AND skill_name = $3", 
                user_id, character_name, skill_name
            )
            
            if result:
                value = result['dots']
                _character_cache.set(cache_key, value)
                return value
            
            return None
            
    except Exception as e:
        logger.error(f"Error getting skill {skill_name} for character '{character_name}' (user {user_id}): {e}")
        raise DatabaseError(f"Failed to get character skill: {e}")


async def character_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    """Character name autocomplete with caching and error handling."""
    user_id = str(interaction.user.id)
    cache_key = f"autocomplete:{user_id}"
    
    try:
        characters = _character_cache.get(cache_key)
        
        if characters is None:
            from core.db import get_async_db
            async with get_async_db() as conn:
                rows = await conn.fetch(
                    "SELECT name FROM characters WHERE user_id = $1 ORDER BY name", 
                    user_id
                )
                characters = [row['name'] for row in rows]
                _character_cache.set(cache_key, characters)
        
        # Filter based on current input
        filtered = [
            char_name for char_name in characters 
            if current.lower() in char_name.lower()
        ]
        
        return [
            app_commands.Choice(name=char_name, value=char_name)
            for char_name in filtered[:25]  # Discord limit
        ]
        
    except Exception as e:
        logger.error(f"Error in character autocomplete for user {user_id}: {e}")
        return []


# ===== MESSAGE SYSTEM EXTENSIONS =====

async def character_not_found_message(user_id: str, character_name: str) -> str:
    """Enhanced character not found message with Herald's analytical voice"""
    # Import here to avoid circular dependency
    from core.ui_utils import HeraldMessages

    cache_key = f"user_chars:{user_id}"
    user_characters = _character_cache.get(cache_key)

    if user_characters is None:
        try:
            from core.db import get_async_db
            async with get_async_db() as conn:
                rows = await conn.fetch(
                    "SELECT name FROM characters WHERE user_id = $1 ORDER BY name",
                    user_id
                )
                user_characters = [row['name'] for row in rows]
                _character_cache.set(cache_key, user_characters)
        except Exception as e:
            logger.error(f"Error getting user characters: {e}")
            user_characters = []

    base_msg = f"{HeraldMessages.QUERY_FAILED}: No Hunter matches pattern \"{character_name}\""

    if user_characters:
        if len(user_characters) == 1:
            suggestion = f"\nAnalysis: Did you mean **{user_characters[0]}**?"
        elif len(user_characters) <= 3:
            names = "**, **".join(user_characters)
            suggestion = f"\nAnalysis: Your Hunters: **{names}**"
        else:
            suggestion = f"\nAnalysis: Use `/characters` to see your {len(user_characters)} Hunters"
    else:
        suggestion = f"\nAnalysis: Create your first Hunter with `/create name:\"Character Name\"`"

    return base_msg + suggestion


async def ensure_h5e_columns():
    """Ensure H5E columns exist with enhanced error handling."""
    try:
        from core.db import get_async_db
        async with get_async_db() as conn:
            # Check existing columns in PostgreSQL
            result = await conn.fetch("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'characters'
            """)
            
            columns = [row['column_name'] for row in result]
            
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
                    await conn.execute(f"ALTER TABLE characters ADD COLUMN {column} {definition}")
            
    except Exception as e:
        logger.error(f"Error ensuring H5E columns: {e}")
        raise DatabaseError(f"Failed to ensure H5E columns: {e}")


def invalidate_character_cache(user_id: str, character_name: str = None):
    """Invalidate cached character data when updates occur."""
    if character_name:
        # Invalidate specific character
        pattern = f"{user_id}:{character_name.lower()}"
    else:
        # Invalidate all data for user
        pattern = f"{user_id}:"
    
    _character_cache.invalidate(pattern)
    logger.debug(f"Invalidated character cache for pattern: {pattern}")


# ===== ENHANCED CHARACTER SHEET CREATION =====

def create_enhanced_character_sheet(character: Dict[str, Any], skills: List[Dict[str, Any]],
                                   edges: List[Dict[str, Any]] = None, perks: List[Dict[str, Any]] = None) -> discord.Embed:
    """Create an enhanced character sheet with full validation and error handling."""
    # Import here to avoid circular dependency
    from core.ui_utils import HeraldEmojis, create_health_bar, create_willpower_bar, create_desperation_bar, create_danger_bar, create_skill_display

    # Default to empty lists if not provided
    edges = edges or []
    perks = perks or []

    try:
        name = character.get('name', 'Unknown')
        creed = character.get('creed', 'No creed set')
        drive = character.get('drive', 'No drive set')

        # Create main embed with Herald theme
        embed = discord.Embed(
            title=f"🏹 {name}",
            color=0x8B0000  # Dark red theme for Hunter
        )

        # === CREED & DRIVE (Full width) ===
        embed.add_field(
            name="Creed",
            value=creed,
            inline=False
        )
        embed.add_field(
            name="Drive",
            value=drive,
            inline=False
        )

        # === CORE TRACKERS (All 10 dots) ===
        # Health
        health_current = max(0, min(10, character.get('health', 0)))
        health_sup = max(0, character.get('health_sup', 0))
        health_agg = max(0, character.get('health_agg', 0))
        health_bar = create_health_bar(health_current, health_sup, health_agg)
        health_remaining = max(0, health_current - health_sup - health_agg)

        # Willpower
        willpower_current = max(0, min(10, character.get('willpower', 0)))
        willpower_sup = max(0, character.get('willpower_sup', 0))
        willpower_agg = max(0, character.get('willpower_agg', 0))
        willpower_bar = create_willpower_bar(willpower_current, willpower_sup, willpower_agg)
        willpower_remaining = max(0, willpower_current - willpower_sup - willpower_agg)

        # Desperation
        desperation = max(0, min(10, character.get('desperation', 0)))
        desperation_bar = create_desperation_bar(desperation)
        in_despair = character.get('in_despair', False)

        # Danger
        danger = max(0, min(10, character.get('danger', 0)))
        danger_bar = create_danger_bar(danger)

        # Display trackers in 2x2 layout
        # Note: Discord embeds show 3 inline fields per row, so we need a spacer to force 2x2
        embed.add_field(
            name="__Health__",
            value=f"{health_bar}\n`{health_remaining}/{health_current}`",
            inline=True
        )
        embed.add_field(
            name="__Willpower__",
            value=f"{willpower_bar}\n`{willpower_remaining}/{willpower_current}`",
            inline=True
        )
        # Spacer to force next row (Discord shows 3 fields per row)
        embed.add_field(name="\u200b", value="\u200b", inline=True)

        embed.add_field(
            name="__Desperation__",
            value=f"{desperation_bar}\n`{desperation}/10`",
            inline=True
        )
        embed.add_field(
            name="__Danger__",
            value=f"{danger_bar}\n`{danger}/10`",
            inline=True
        )
        # Spacer to balance the row
        embed.add_field(name="\u200b", value="\u200b", inline=True)

        # Show Despair State if active
        if in_despair:
            embed.add_field(
                name="",
                value=f"💀 **IN DESPAIR** - Drive unusable until redeemed",
                inline=False
            )
            if character.get('redemption'):
                embed.add_field(
                    name="",
                    value=f"🕊️ *Redemption: {character['redemption']}*",
                    inline=False
                )

        # Add visual separator
        embed.add_field(name=HeraldEmojis.SEPARATOR, value="", inline=False)
        
        # === ATTRIBUTES (Compact 3-column layout) ===
        physical_attrs = [
            f"**Strength:** {max(1, min(5, character.get('strength', 1)))}",
            f"**Dexterity:** {max(1, min(5, character.get('dexterity', 1)))}",
            f"**Stamina:** {max(1, min(5, character.get('stamina', 1)))}"
        ]
        
        social_attrs = [
            f"**Charisma:** {max(1, min(5, character.get('charisma', 1)))}",
            f"**Manipulation:** {max(1, min(5, character.get('manipulation', 1)))}",
            f"**Composure:** {max(1, min(5, character.get('composure', 1)))}"
        ]
        
        mental_attrs = [
            f"**Intelligence:** {max(1, min(5, character.get('intelligence', 1)))}",
            f"**Wits:** {max(1, min(5, character.get('wits', 1)))}",
            f"**Resolve:** {max(1, min(5, character.get('resolve', 1)))}"
        ]
        
        embed.add_field(
            name="__Physical__",
            value="\n".join(physical_attrs),
            inline=True
        )
        embed.add_field(
            name="__Social__",
            value="\n".join(social_attrs),
            inline=True
        )
        embed.add_field(
            name="__Mental__",
            value="\n".join(mental_attrs),
            inline=True
        )
        
        # === SKILLS (Smart display with specialties integration) ===
        if skills:
            # Get skills with dots > 0
            trained_skills = [skill for skill in skills if skill.get('dots', 0) > 0]
            
            if trained_skills:
                skill_text = []
                for skill in trained_skills[:15]:  # Limit to prevent overflow
                    dots = max(0, min(5, skill.get('dots', 0)))
                    skill_display = create_skill_display(dots)
                    skill_text.append(f"**{skill.get('skill_name', 'Unknown')}:** {skill_display} `{dots}`")
                
                # Handle long skill lists
                skills_display = "\n".join(skill_text)
                if len(trained_skills) > 15:
                    skills_display += f"\n*...and {len(trained_skills) - 15} more*"
                
                embed.add_field(
                    name="__Trained Skills__",
                    value=skills_display,
                    inline=False
                )
        
        # === EDGE AND PERKS (Hunter Abilities) ===
        if edges:
            edge_text = []
            for edge in edges:
                edge_name = edge.get('edge_name', 'Unknown')
                edge_desc = edge.get('description', '')
                if edge_desc:
                    edge_text.append(f"**{edge_name}:** {edge_desc}")
                else:
                    edge_text.append(f"**{edge_name}**")

            embed.add_field(
                name=f"{HeraldEmojis.EDGE} Edge Abilities",
                value="\n".join(edge_text),
                inline=False
            )

        if perks:
            perk_text = []
            for perk in perks:
                perk_name = perk.get('perk_name', 'Unknown')
                perk_desc = perk.get('description', '')
                if perk_desc:
                    perk_text.append(f"**{perk_name}:** {perk_desc}")
                else:
                    perk_text.append(f"**{perk_name}**")

            embed.add_field(
                name="🎭 Perks",
                value="\n".join(perk_text),
                inline=False
            )

        # === HUNTER MECHANICS ===
        h5e_mechanics = []

        if character.get('ambition'):
            h5e_mechanics.append(f"**Ambition:** {character['ambition']}")
        if character.get('desire'):
            h5e_mechanics.append(f"**Desire:** {character['desire']}")
        # Note: Drive is already shown at the top of the sheet, so we don't repeat it here

        if h5e_mechanics:
            embed.add_field(
                name="Hunter Mechanics",
                value="\n\n".join(h5e_mechanics),
                inline=False
            )
        
        # Footer with helpful tips
        embed.set_footer(text="💡 Use /damage and /heal to manage health • Use /creed and /drive to set your Hunter's path")
        
        return embed
        
    except Exception as e:
        logger.error(f"Error creating enhanced character sheet: {e}")
        # Return a basic fallback embed
        return discord.Embed(
            title="Character Sheet Error",
            description="Unable to display character sheet properly",
            color=0x8B0000
        )


# ===== BACKWARD COMPATIBILITY ALIASES =====

# For existing code that expects HeraldMessages in character_utils
class HeraldMessages:
    """Legacy compatibility - import from ui_utils instead"""
    
    @staticmethod
    async def character_not_found(user_id: str, character_name: str) -> str:
        return await character_not_found_message(user_id, character_name)
    
    @staticmethod 
    def xp_insufficient(needed: int, available: int, improvement: str) -> str:
        from core.ui_utils import HeraldMessages as UIMessages
        return UIMessages.xp_insufficient(needed, available, improvement)
    
    @staticmethod
    def skill_at_maximum(skill_name: str, current_dots: int) -> str:
        from core.ui_utils import HeraldMessages as UIMessages
        return UIMessages.skill_at_maximum(skill_name, current_dots)
    
    @staticmethod
    def operation_success(title: str, description: str) -> str:
        from core.ui_utils import HeraldMessages as UIMessages
        return UIMessages.operation_success(title, description)
    
    @staticmethod
    def operation_failed(title: str, error: str, suggestion: str = None) -> str:
        from core.ui_utils import HeraldMessages as UIMessages
        return UIMessages.operation_failed(title, error, suggestion)
