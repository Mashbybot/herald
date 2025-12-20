"""
UI utilities for Herald character management system.
Contains emojis, colors, and visual display components.
"""

import discord
import logging
from typing import Dict, Any

logger = logging.getLogger('Herald.UI')


# ===== EMOJI SYSTEM =====

class HeraldEmojis:
    """Centralized emoji system for consistent Herald bot styling"""
    
    # Status & Results
    SUCCESS = "✅"
    ERROR = "❌"
    WARNING = "⚠️"
    INFO = "ℹ️"
    LOADING = "⏳"
    NEW = "✨"
    
    # Health & Damage (Emoji diamonds - large and prominent)
    HEALTH_FULL = "🔶"          # Large Orange Diamond (undamaged/healthy)
    HEALTH_SUPERFICIAL = "⛛"    # Heavy Chevron (superficial damage)
    HEALTH_AGGRAVATED = "🔻"    # Red Triangle Pointed Down (aggravated damage)
    HEALTH_EMPTY = "◾"          # Black Medium-Small Square (no capacity)

    # Willpower (Emoji diamonds - large and prominent)
    WILLPOWER_FULL = "🔷"       # Large Blue Diamond (undamaged)
    WILLPOWER_SUPERFICIAL = "⛛" # Heavy Chevron (superficial damage)
    WILLPOWER_AGGRAVATED = "🔻"  # Red Triangle Pointed Down (aggravated damage)
    WILLPOWER_EMPTY = "◾"       # Black Medium-Small Square (no capacity)
    
    # H5E Mechanics
    EDGE = "⚡"
    EDGE_EMPTY = "🔹"
    DESPERATION = "😰"           # Anxious Face with Sweat

    # Desperation Tracker (10 dots)
    DESPERATION_FULL = "🟨"      # Yellow Square (filled)
    DESPERATION_EMPTY = "◾"      # Black Medium-Small Square (empty)

    # Danger Tracker (10 dots)
    DANGER_FULL = "🟥"           # Red Square (filled)
    DANGER_EMPTY = "◾"           # Black Medium-Small Square (empty)
    
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
    NOTES = "📔"
    
    # Dice Rolling
    DICE = "🎲"
    CRITICAL = "💥"
    SUCCESS_DIE = "🎯"
    
    # Visual Separators
    SEPARATOR = "🟨⬛🟨⬛🟨⬛🟨⬛🟨⬛🟨⬛🟨⬛🟨⬛🟨⬛🟨⬛🟨⬛"  # Warning tape style
    DIVIDER = "▫️"
    
    # === DICE EMOJIS (Easy to customize) ===

    # Check environment variable for emoji mode
    import os
    _USE_CUSTOM_EMOJIS = os.getenv("USE_CUSTOM_EMOJIS", "true").lower() == "true"

    # Custom Discord Emojis (from your server)
    _CUSTOM_REGULAR_BOTCH = "<:Dice_reg_over:1413720433462612121>"
    _CUSTOM_REGULAR_FAILURE = "<:Dice_reg_fail:1413720432527413279>"
    _CUSTOM_REGULAR_SUCCESS = "<:Dice_reg_succ:1413720435371282463>"
    _CUSTOM_REGULAR_CRITICAL = "<:Dice_reg_crit:1413720431130705950>"
    _CUSTOM_DESPERATION_BOTCH = "<:Dice_des_over:1413720427183865887>"
    _CUSTOM_DESPERATION_FAILURE = "<:Dice_des_fail:1413720425678241862>"
    _CUSTOM_DESPERATION_SUCCESS = "<:Dice_des_succ:1413720429763498104>"
    _CUSTOM_DESPERATION_CRITICAL = "<:Dice_des_crit:1413720424688390285>"

    # Unicode Fallback Emojis (always work)
    _UNICODE_REGULAR_BOTCH = "💥"       # 1 - botch/overreach
    _UNICODE_REGULAR_FAILURE = "⚫"     # 2-5 - failure
    _UNICODE_REGULAR_SUCCESS = "🎯"     # 6-9 - success
    _UNICODE_REGULAR_CRITICAL = "⭐"    # 10 - critical
    _UNICODE_DESPERATION_BOTCH = "🔥"   # 1 - desperation botch
    _UNICODE_DESPERATION_FAILURE = "🟠" # 2-5 - desperation failure
    _UNICODE_DESPERATION_SUCCESS = "🟡" # 6-9 - desperation success
    _UNICODE_DESPERATION_CRITICAL = "✨" # 10 - desperation critical

    # Active Dice Emojis (switch based on environment variable)
    REGULAR_BOTCH = _CUSTOM_REGULAR_BOTCH if _USE_CUSTOM_EMOJIS else _UNICODE_REGULAR_BOTCH
    REGULAR_FAILURE = _CUSTOM_REGULAR_FAILURE if _USE_CUSTOM_EMOJIS else _UNICODE_REGULAR_FAILURE
    REGULAR_SUCCESS = _CUSTOM_REGULAR_SUCCESS if _USE_CUSTOM_EMOJIS else _UNICODE_REGULAR_SUCCESS
    REGULAR_CRITICAL = _CUSTOM_REGULAR_CRITICAL if _USE_CUSTOM_EMOJIS else _UNICODE_REGULAR_CRITICAL

    DESPERATION_BOTCH = _CUSTOM_DESPERATION_BOTCH if _USE_CUSTOM_EMOJIS else _UNICODE_DESPERATION_BOTCH
    DESPERATION_FAILURE = _CUSTOM_DESPERATION_FAILURE if _USE_CUSTOM_EMOJIS else _UNICODE_DESPERATION_FAILURE
    DESPERATION_SUCCESS = _CUSTOM_DESPERATION_SUCCESS if _USE_CUSTOM_EMOJIS else _UNICODE_DESPERATION_SUCCESS
    DESPERATION_CRITICAL = _CUSTOM_DESPERATION_CRITICAL if _USE_CUSTOM_EMOJIS else _UNICODE_DESPERATION_CRITICAL

    # Edge Dice (using Unicode for now)
    EDGE_BOTCH = "❗"
    EDGE_FAILURE = "⚫"
    EDGE_SUCCESS = "🎯"
    EDGE_CRITICAL = "⭐"        
    
    # === DICE RESULT COLORS ===
    COLOR_CRITICAL = 0x00FF00      # Green - Critical success
    COLOR_MESSY_CRITICAL = 0xEA3323 # Red-orange - Messy critical  
    COLOR_SUCCESS = 0x7777FF       # Blue - Standard success
    COLOR_FAILURE = 0x808080       # Gray - Failure
    COLOR_TOTAL_FAILURE = 0x000000 # Black - Total failure
    COLOR_DESPERATION_FAILURE = 0x5C0700 # Dark red - Desperation failure


# ===== VISUAL DISPLAY FUNCTIONS =====

def create_health_bar(current_max: int, superficial: int, aggravated: int, max_possible: int = 10) -> str:
    """Create health bar with validation and error handling (always 10 dots)"""
    try:
        # Validate inputs
        current_max = max(0, min(current_max, max_possible))
        superficial = max(0, min(superficial, current_max))
        aggravated = max(0, min(aggravated, current_max))
        
        # Ensure damage doesn't exceed max
        total_damage = superficial + aggravated
        if total_damage > current_max:
            ratio = current_max / total_damage
            superficial = int(superficial * ratio)
            aggravated = current_max - superficial
        
        undamaged = max(0, current_max - superficial - aggravated)
        potential = max(0, max_possible - current_max)
        
        return (
            HeraldEmojis.HEALTH_FULL * undamaged +
            HeraldEmojis.HEALTH_SUPERFICIAL * superficial +
            HeraldEmojis.HEALTH_AGGRAVATED * aggravated +
            HeraldEmojis.HEALTH_EMPTY * potential
        )
    except Exception as e:
        logger.error(f"Error creating health bar: {e}")
        return "❓" * max_possible


def create_willpower_bar(current_max: int, superficial: int, aggravated: int, max_possible: int = 10) -> str:
    """Create willpower bar with validation and error handling"""
    try:
        # Validate inputs
        current_max = max(0, min(current_max, max_possible))
        superficial = max(0, min(superficial, current_max))
        aggravated = max(0, min(aggravated, current_max))
        
        # Ensure damage doesn't exceed max
        total_damage = superficial + aggravated
        if total_damage > current_max:
            ratio = current_max / total_damage
            superficial = int(superficial * ratio)
            aggravated = current_max - superficial
        
        undamaged = max(0, current_max - superficial - aggravated)
        potential = max(0, max_possible - current_max)
        
        return (
            HeraldEmojis.WILLPOWER_FULL * undamaged +
            HeraldEmojis.WILLPOWER_SUPERFICIAL * superficial +
            HeraldEmojis.WILLPOWER_AGGRAVATED * aggravated +
            HeraldEmojis.WILLPOWER_EMPTY * potential
        )
    except Exception as e:
        logger.error(f"Error creating willpower bar: {e}")
        return "❓" * max_possible


def create_edge_bar(edge: int, max_edge: int = 5) -> str:
    """Create edge rating display with validation"""
    try:
        edge = max(0, min(edge, max_edge))
        return (
            HeraldEmojis.EDGE * edge + 
            HeraldEmojis.EDGE_EMPTY * (max_edge - edge)
        )
    except Exception as e:
        logger.error(f"Error creating edge bar: {e}")
        return "❓" * max_edge


def create_desperation_bar(desperation: int, max_desperation: int = 10) -> str:
    """Create desperation level display with validation"""
    try:
        desperation = max(0, min(desperation, max_desperation))
        return (
            HeraldEmojis.DESPERATION_FULL * desperation +
            HeraldEmojis.DESPERATION_EMPTY * (max_desperation - desperation)
        )
    except Exception as e:
        logger.error(f"Error creating desperation bar: {e}")
        return "❓" * max_desperation


def create_danger_bar(danger: int, max_danger: int = 10) -> str:
    """Create danger level display with validation"""
    try:
        danger = max(0, min(danger, max_danger))
        return (
            HeraldEmojis.DANGER_FULL * danger +
            HeraldEmojis.DANGER_EMPTY * (max_danger - danger)
        )
    except Exception as e:
        logger.error(f"Error creating danger bar: {e}")
        return "❓" * max_danger


def create_skill_display(dots: int, max_dots: int = 5) -> str:
    """Create skill dots display with validation"""
    try:
        dots = max(0, min(dots, max_dots))
        return (
            HeraldEmojis.SKILL_FILLED * dots + 
            HeraldEmojis.SKILL_EMPTY * (max_dots - dots)
        )
    except Exception as e:
        logger.error(f"Error creating skill display: {e}")
        return "❓" * max_dots


# ===== EMBED CREATION FUNCTIONS =====

def create_success_embed(title: str, description: str, details: str = None, color: int = 0x228B22) -> discord.Embed:
    """Create standardized success embed with validation."""
    try:
        embed = discord.Embed(
            title=f"{HeraldEmojis.SUCCESS} {title}",
            description=description,
            color=color
        )
        
        if details:
            embed.add_field(name="Details", value=details, inline=False)
        
        return embed
    except Exception as e:
        logger.error(f"Error creating success embed: {e}")
        return discord.Embed(title="Success", description=description, color=0x228B22)


def create_error_embed(title: str, description: str, suggestion: str = None, color: int = 0x8B0000) -> discord.Embed:
    """Create standardized error embed with validation."""
    try:
        embed = discord.Embed(
            title=f"{HeraldEmojis.ERROR} {title}",
            description=description,
            color=color
        )
        
        if suggestion:
            embed.add_field(name="💡 Suggestion", value=suggestion, inline=False)
        
        return embed
    except Exception as e:
        logger.error(f"Error creating error embed: {e}")
        return discord.Embed(title="Error", description=description, color=0x8B0000)


def create_info_embed(title: str, description: str, color: int = 0x4169E1) -> discord.Embed:
    """Create standardized info embed with validation."""
    try:
        return discord.Embed(
            title=f"{HeraldEmojis.INFO} {title}",
            description=description,
            color=color
        )
    except Exception as e:
        logger.error(f"Error creating info embed: {e}")
        return discord.Embed(title="Info", description=description, color=0x4169E1)


def create_warning_embed(title: str, description: str, suggestion: str = None, color: int = 0xFF8C00) -> discord.Embed:
    """Create standardized warning embed with validation."""
    try:
        embed = discord.Embed(
            title=f"{HeraldEmojis.WARNING} {title}",
            description=description,
            color=color
        )
        
        if suggestion:
            embed.add_field(name="💡 Tip", value=suggestion, inline=False)
        
        return embed
    except Exception as e:
        logger.error(f"Error creating warning embed: {e}")
        return discord.Embed(title="Warning", description=description, color=0xFF8C00)


# ===== LOADING INDICATOR =====

async def with_loading_indicator(interaction, operation_func, loading_message: str = "Processing..."):
    """Loading indicator with enhanced error handling."""
    try:
        await interaction.response.send_message(
            f"{HeraldEmojis.LOADING} {loading_message}", 
            ephemeral=True
        )
        
        result = await operation_func()
        
        if isinstance(result, discord.Embed):
            await interaction.edit_original_response(content=None, embed=result)
        else:
            await interaction.edit_original_response(content=result)
            
        return result
        
    except Exception as e:
        error_msg = f"{HeraldEmojis.ERROR} Operation failed: {str(e)}"
        try:
            await interaction.edit_original_response(content=error_msg)
        except:
            # If edit fails, try followup
            await interaction.followup.send(content=error_msg, ephemeral=True)
        logger.error(f"Loading indicator operation failed: {e}")
        raise


# ===== COLOR SYSTEM =====

class HeraldColors:
    """Herald's signature color palette - Orange diamond theme"""

    # Core brand colors
    ORANGE = 0xFF8C00          # Signature orange (#FF8C00)
    DARK_ORANGE = 0xCC7000     # Darker shade for contrast
    BLOOD_RED = 0x8B0000       # Dark red for serious warnings

    # Semantic colors (using orange theme)
    SUCCESS = 0xFF8C00         # Orange for successful operations
    WARNING = 0xFFD700         # Gold for warnings
    ERROR = 0x8B0000           # Blood red for errors
    INFO = 0xFF8C00            # Orange for information

    # Keep existing dice colors for compatibility
    CRITICAL = 0x00FF00              # Green - Critical success
    MESSY_CRITICAL = 0xEA3323        # Red-orange - Messy critical
    DICE_SUCCESS = 0x7777FF          # Blue - Standard success
    DICE_FAILURE = 0x808080          # Gray - Failure


# ===== MESSAGE SYSTEM =====

class HeraldMessages:
    """Herald's analytical voice - short declarative statements, present tense"""

    # State change markers (🔸 usage)
    QUERY_RECOGNIZED = "🔸 Query recognized"
    PROTOCOL_ESTABLISHED = "🔸 Protocol established"
    PATTERN_LOGGED = "🔸 Pattern logged"
    SUCCESS_LOGGED = "🔸 Logged"
    QUERY_FAILED = "🔸 Query failed"
    INCOMPLETE_DATA = "🔸 Incomplete data stream"
    PATTERN_WARNING = "🔸 Pattern warning"
    PATTERN_RECOGNIZED = "🔸 Pattern recognized"

    # Herald's catchphrase
    CATCHPHRASE = "🔸 What are we Hunting?"

    # Legacy methods for backward compatibility
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
