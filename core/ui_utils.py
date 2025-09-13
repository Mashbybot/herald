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
    
    # Health & Damage
    HEALTH_FULL = "❤️"
    HEALTH_SUPERFICIAL = "🧡" 
    HEALTH_AGGRAVATED = "💔"
    HEALTH_EMPTY = "🖤"
    
    # Willpower
    WILLPOWER_FULL = "🟢"
    WILLPOWER_SUPERFICIAL = "🟡"
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
    NOTES = "📔"
    
    # Dice Rolling
    DICE = "🎲"
    CRITICAL = "💥"
    SUCCESS_DIE = "🎯"
    
    # Visual Separators
    SEPARATOR = "━━━━━━━━━━━━━━━━━━━━━━━"
    DIVIDER = "▫️"
    
    # === DICE EMOJIS (Easy to customize) ===
    
    # Regular Dice (Gray/Dark theme)
    REGULAR_BOTCH = "<:Dice_reg_over:1413720433462612121>"        # 1 - botch/overreach 
    REGULAR_FAILURE = "<:Dice_reg_fail:1413720432527413279>"      # 2-5 - failure
    REGULAR_SUCCESS = "<:Dice_reg_succ:1413720435371282463>"      # 6-9 - success
    REGULAR_CRITICAL = "<:Dice_reg_crit:1413720431130705950>"     # 10 - potential critical
    
    # Desperation Dice (Orange theme) 
    # NOTE: Replace these with your custom orange-tinted emojis when ready
    DESPERATION_BOTCH = "<:Dice_des_over:1413720427183865887>"    # 1 - desperation botch
    DESPERATION_FAILURE = "<:Dice_des_fail:1413720425678241862>"  # 2-5 - desperation failure
    DESPERATION_SUCCESS = "<:Dice_des_succ:1413720429763498104>"  # 6-9 - desperation success
    DESPERATION_CRITICAL = "<:Dice_des_crit:1413720424688390285>" # 10 - desperation critical
    
    # Edge Dice (grouped with regular for now)
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

def create_health_bar(current_max: int, superficial: int, aggravated: int, max_possible: int = 8) -> str:
    """Create health bar with validation and error handling"""
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
            HeraldEmojis.DESPERATION * desperation + 
            HeraldEmojis.DESPERATION_EMPTY * (max_desperation - desperation)
        )
    except Exception as e:
        logger.error(f"Error creating desperation bar: {e}")
        return "❓" * max_desperation


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


# ===== MESSAGE SYSTEM =====

class HeraldMessages:
    """Centralized user-friendly messages with actionable suggestions"""
    
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
