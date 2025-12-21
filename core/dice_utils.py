"""
Dice utilities for Herald bot
Handles dice emoji display and result formatting for H5E dice mechanics
"""

import logging
from typing import List

# Import from ui_utils to avoid circular dependencies
from core.ui_utils import HeraldEmojis

logger = logging.getLogger('Herald.Dice.Utils')


def get_die_emoji(value: int, die_type: str = "regular") -> str:
    """
    Get emoji representation for a die value
    
    Args:
        value: Die value (1-10)
        die_type: "regular" or "desperation"
    
    Returns:
        Emoji string representing the die
    """
    # Validate input
    if not isinstance(value, int) or not 1 <= value <= 10:
        logger.warning(f"Invalid die value: {value}, using fallback")
        return "❓"
    
    if die_type not in ["regular", "desperation", "edge"]:
        logger.warning(f"Invalid die type: {die_type}, defaulting to regular")
        die_type = "regular"
    
    try:
        if die_type == "desperation":
            if value == 1:
                return HeraldEmojis.DESPERATION_BOTCH
            elif 2 <= value <= 5:
                return HeraldEmojis.DESPERATION_FAILURE
            elif 6 <= value <= 9:
                return HeraldEmojis.DESPERATION_SUCCESS
            elif value == 10:
                return HeraldEmojis.DESPERATION_CRITICAL
        else:  # regular or edge
            if value == 1:
                return HeraldEmojis.REGULAR_BOTCH
            elif 2 <= value <= 5:
                return HeraldEmojis.REGULAR_FAILURE
            elif 6 <= value <= 9:
                return HeraldEmojis.REGULAR_SUCCESS
            elif value == 10:
                return HeraldEmojis.REGULAR_CRITICAL
    except Exception as e:
        logger.error(f"Error getting die emoji: {e}")
        return "❓"
    
    return "❓"  # Fallback


def format_dice_display(dice_list: List[int], die_type: str = "regular") -> str:
    """
    Format a list of dice into an emoji display string

    Args:
        dice_list: List of die values
        die_type: "regular" or "desperation"

    Returns:
        String of emoji representations
    """
    if not dice_list:
        return ""

    if not isinstance(dice_list, list):
        logger.warning(f"Expected list for dice_list, got {type(dice_list)}")
        return "❓"

    try:
        # Filter out invalid dice
        valid_dice = [d for d in dice_list if isinstance(d, int) and 1 <= d <= 10]
        if len(valid_dice) != len(dice_list):
            logger.warning(f"Filtered out {len(dice_list) - len(valid_dice)} invalid dice")

        return "".join([get_die_emoji(die, die_type) for die in valid_dice])
    except Exception as e:
        logger.error(f"Error formatting dice display: {e}")
        return "❓"


def get_result_color(total_successes: int, crits: int, messy_critical: bool = False) -> int:
    """
    Get color for result embed based on outcome
    
    Args:
        total_successes: Total number of successes
        crits: Number of critical successes
        messy_critical: Whether this was a messy critical
    
    Returns:
        Color integer for Discord embed
    """
    try:
        if total_successes == 0:
            return HeraldEmojis.COLOR_TOTAL_FAILURE
        elif messy_critical:
            return HeraldEmojis.COLOR_MESSY_CRITICAL
        elif crits > 0:
            return HeraldEmojis.COLOR_CRITICAL
        elif total_successes >= 5:
            return 0x00FF00  # Bright green for exceptional
        elif total_successes >= 3:
            return 0x228B22  # Forest green for complete success
        elif total_successes >= 2:
            return HeraldEmojis.COLOR_SUCCESS
        else:
            return 0xFF8C00  # Orange for marginal
    except Exception as e:
        logger.error(f"Error determining result color: {e}")
        return 0x808080  # Default gray


def create_success_description(total_successes: int, crits: int, messy_critical: bool = False) -> str:
    """
    Create description text for success level
    
    Args:
        total_successes: Total number of successes
        crits: Number of critical successes
        messy_critical: Whether this was a messy critical
    
    Returns:
        Formatted success description
    """
    try:
        if total_successes == 0:
            return "TOTAL FAILURE"
        elif messy_critical:
            return f"MESSY CRITICAL ({total_successes})"
        elif crits > 0:
            return f"CRITICAL SUCCESS ({total_successes})"
        elif total_successes >= 6:
            return f"EXCEPTIONAL SUCCESS ({total_successes})"
        elif total_successes >= 4:
            return f"COMPLETE SUCCESS ({total_successes})"
        elif total_successes >= 2:
            return f"SUCCESS ({total_successes})"
        elif total_successes == 1:
            return f"MARGINAL SUCCESS ({total_successes})"
        else:
            return "TOTAL FAILURE"
    except Exception as e:
        logger.error(f"Error creating success description: {e}")
        return "UNKNOWN RESULT"


def format_margin_display(margin: int) -> str:
    """
    Format margin with appropriate color indicator
    
    Args:
        margin: Success margin (successes - difficulty)
    
    Returns:
        Formatted margin string with color indicator
    """
    try:
        if margin > 0:
            return f"🟢 **Margin:** +{margin}"
        elif margin < 0:
            return f"🔴 **Margin:** {margin}"
        else:
            return f"⚪ **Margin:** {margin}"
    except Exception as e:
        logger.error(f"Error formatting margin display: {e}")
        return f"**Margin:** {margin}"


def sort_dice_for_display(dice: List[int]) -> List[int]:
    """
    Sort dice for optimal display (successes first, then failures, all high to low)
    
    Args:
        dice: List of die values
    
    Returns:
        Sorted list with successes first, then failures
    """
    if not dice:
        return []
    
    try:
        successes = [d for d in dice if d >= 6]
        failures = [d for d in dice if d < 6]
        
        # Sort within each group: high to low
        successes.sort(reverse=True)
        failures.sort(reverse=True)
        
        # Return successes first, then failures
        return successes + failures
    except Exception as e:
        logger.error(f"Error sorting dice for display: {e}")
        return dice  # Return original list if sorting fails
