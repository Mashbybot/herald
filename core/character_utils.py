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
    
    def __init__(self, max_size: int = 100, ttl_seconds: int = 300):
        self.cache: Dict[str, Tuple[Any, float]] = {}
        self.max_size = max_size
        self.ttl = ttl_seconds
    
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


async def get_character_attribute(user_id: str, character_name: str, attribute: str) -> Optional[int]:
    """Get character attribute with caching and validation."""
    if attribute.lower() not in ['strength', 'dexterity', 'stamina', 'charisma', 'manipulation', 'composure', 'intelligence', 'wits', 'resolve']:
        logger.warning(f"Invalid attribute requested: {attribute}")
        return None
    
    cache_key = f"attr:{user_id}:{character_name.lower()}:{attribute.lower()}"
    cached_value = _character_cache.get(cache_key)
    
    if cached_value is not None:
        return cached_value
    
    try:
        from core.db import get_async_db
        async with get_async_db() as conn:
            result = await conn.fetchrow(
                f"SELECT {attribute.lower()} FROM characters WHERE user_id = $1 AND name = $2", 
                user_id, character_name
            )
            
            if result:
                value = result[attribute.lower()]
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

def create_enhanced_character_sheet(character: Dict[str, Any], skills: List[Dict[str, Any]]) -> discord.Embed:
    """Create an enhanced character sheet with full validation and error handling."""
    # Import here to avoid circular dependency
    from core.ui_utils import HeraldEmojis, create_health_bar, create_willpower_bar, create_edge_bar, create_desperation_bar, create_skill_display
    
    try:
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
        health_current = max(0, character.get('health', 0))
        health_sup = max(0, character.get('health_sup', 0))
        health_agg = max(0, character.get('health_agg', 0))
        health_bar = create_health_bar(health_current, health_sup, health_agg)
        
        willpower_current = max(0, character.get('willpower', 0))
        willpower_sup = max(0, character.get('willpower_sup', 0))
        willpower_agg = max(0, character.get('willpower_agg', 0))
        willpower_bar = create_willpower_bar(willpower_current, willpower_sup, willpower_agg)
        
        # Side-by-side layout for health/willpower
        health_remaining = max(0, health_current - health_sup - health_agg)
        willpower_remaining = max(0, willpower_current - willpower_sup - willpower_agg)
        
        embed.add_field(
            name=f"{HeraldEmojis.HEALTH_FULL} Health",
            value=f"{health_bar}\n`{health_remaining}/{health_current} remaining`",
            inline=True
        )
        embed.add_field(
            name=f"{HeraldEmojis.WILLPOWER_FULL} Willpower",
            value=f"{willpower_bar}\n`{willpower_remaining}/{willpower_current} remaining`",
            inline=True
        )
        
        # Edge and Desperation on same row
        edge = max(0, min(5, character.get('edge', 0)))
        desperation = max(0, min(10, character.get('desperation', 0)))
        
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
