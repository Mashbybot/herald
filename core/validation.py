"""
Input validation utilities for Herald bot.
Centralizes validation logic to ensure consistency and security.
"""

import re
import logging
from typing import Tuple, Optional
from core.constants import (
    CHAR_NAME_MIN_LENGTH, CHAR_NAME_MAX_LENGTH,
    TEXT_FIELD_MAX_LENGTH, SPECIALTY_NAME_MAX_LENGTH,
    ATTRIBUTE_MIN, ATTRIBUTE_MAX,
    SKILL_MIN, SKILL_MAX,
    EDGE_MIN, EDGE_MAX,
    DESPERATION_MIN, DESPERATION_MAX,
    DANGER_MIN, DANGER_MAX,
    CHAR_NAME_PATTERN,
    EMBED_TITLE_LIMIT, EMBED_DESCRIPTION_LIMIT,
    EMBED_FIELD_VALUE_LIMIT
)

logger = logging.getLogger('Herald.Validation')


class ValidationError(Exception):
    """Custom exception for validation errors with user-friendly messages"""
    pass


def validate_character_name(name: str) -> Tuple[bool, Optional[str]]:
    """
    Validate character name.

    Returns:
        (is_valid, error_message)
    """
    if not name or not isinstance(name, str):
        return False, "Character name is required"

    name = name.strip()

    if len(name) < CHAR_NAME_MIN_LENGTH:
        return False, f"Character name must be at least {CHAR_NAME_MIN_LENGTH} characters"

    if len(name) > CHAR_NAME_MAX_LENGTH:
        return False, f"Character name must be {CHAR_NAME_MAX_LENGTH} characters or less"

    # Check for potentially problematic characters that might break Discord formatting
    if name.startswith(('`', '*', '_', '~', '|', '>', '@', '#')):
        return False, "Character name cannot start with special Discord formatting characters"

    return True, None


def validate_attribute(value: int, attribute_name: str = "Attribute") -> Tuple[bool, Optional[str]]:
    """
    Validate attribute value (1-5 range).

    Returns:
        (is_valid, error_message)
    """
    if not isinstance(value, int):
        return False, f"{attribute_name} must be a number"

    if value < ATTRIBUTE_MIN or value > ATTRIBUTE_MAX:
        return False, f"{attribute_name} must be between {ATTRIBUTE_MIN} and {ATTRIBUTE_MAX}"

    return True, None


def validate_skill(value: int, skill_name: str = "Skill") -> Tuple[bool, Optional[str]]:
    """
    Validate skill value (0-5 range).

    Returns:
        (is_valid, error_message)
    """
    if not isinstance(value, int):
        return False, f"{skill_name} must be a number"

    if value < SKILL_MIN or value > SKILL_MAX:
        return False, f"{skill_name} must be between {SKILL_MIN} and {SKILL_MAX}"

    return True, None


def validate_text_field(text: Optional[str], field_name: str, required: bool = False, max_length: int = TEXT_FIELD_MAX_LENGTH) -> Tuple[bool, Optional[str]]:
    """
    Validate text fields like ambition, desire, drive.

    Args:
        text: The text to validate
        field_name: Name of the field for error messages
        required: Whether the field is required
        max_length: Maximum allowed length

    Returns:
        (is_valid, error_message)
    """
    if not text or text.strip() == "":
        if required:
            return False, f"{field_name} is required"
        return True, None

    if len(text) > max_length:
        return False, f"{field_name} must be {max_length} characters or less"

    return True, None


def validate_specialty_name(name: str) -> Tuple[bool, Optional[str]]:
    """
    Validate specialty name.

    Returns:
        (is_valid, error_message)
    """
    if not name or not isinstance(name, str):
        return False, "Specialty name is required"

    name = name.strip()

    if len(name) < 2:
        return False, "Specialty name must be at least 2 characters"

    if len(name) > SPECIALTY_NAME_MAX_LENGTH:
        return False, f"Specialty name must be {SPECIALTY_NAME_MAX_LENGTH} characters or less"

    return True, None


def validate_edge(value: int) -> Tuple[bool, Optional[str]]:
    """Validate Edge value (0-5)"""
    if value < EDGE_MIN or value > EDGE_MAX:
        return False, f"Edge must be between {EDGE_MIN} and {EDGE_MAX}"
    return True, None


def validate_desperation(value: int) -> Tuple[bool, Optional[str]]:
    """Validate Desperation value (0-10)"""
    if value < DESPERATION_MIN or value > DESPERATION_MAX:
        return False, f"Desperation must be between {DESPERATION_MIN} and {DESPERATION_MAX}"
    return True, None


def validate_danger(value: int) -> Tuple[bool, Optional[str]]:
    """Validate Danger value (0-5)"""
    if value < DANGER_MIN or value > DANGER_MAX:
        return False, f"Danger must be between {DANGER_MIN} and {DANGER_MAX}"
    return True, None


def validate_xp_amount(amount: int) -> Tuple[bool, Optional[str]]:
    """Validate XP amount (must be non-negative for gains, can be negative for spending)"""
    if not isinstance(amount, int):
        return False, "XP amount must be a whole number"

    # Allow negative for spending, but check for unreasonable values
    if amount < -10000 or amount > 10000:
        return False, "XP amount is unreasonably large"

    return True, None


def sanitize_embed_text(text: str, limit: int = EMBED_FIELD_VALUE_LIMIT) -> str:
    """
    Sanitize and truncate text to fit within Discord embed limits.

    Args:
        text: Text to sanitize
        limit: Character limit

    Returns:
        Sanitized text that fits within the limit
    """
    if not text:
        return ""

    # Remove null bytes and other problematic characters
    text = text.replace('\x00', '')

    # Truncate if needed
    if len(text) > limit:
        text = text[:limit - 3] + "..."

    return text


def validate_embed_field(name: str, value: str) -> Tuple[bool, Optional[str]]:
    """
    Validate that embed field fits within Discord limits.

    Returns:
        (is_valid, error_message)
    """
    if len(name) > 256:
        return False, "Field name is too long (max 256 characters)"

    if len(value) > EMBED_FIELD_VALUE_LIMIT:
        return False, f"Field value is too long (max {EMBED_FIELD_VALUE_LIMIT} characters)"

    return True, None


def clamp(value: int, min_val: int, max_val: int) -> int:
    """Clamp a value between min and max"""
    return max(min_val, min(value, max_val))


def clamp_attribute(value: int) -> int:
    """Clamp attribute to valid range (1-5)"""
    return clamp(value, ATTRIBUTE_MIN, ATTRIBUTE_MAX)


def clamp_skill(value: int) -> int:
    """Clamp skill to valid range (0-5)"""
    return clamp(value, SKILL_MIN, SKILL_MAX)


def clamp_edge(value: int) -> int:
    """Clamp edge to valid range (0-5)"""
    return clamp(value, EDGE_MIN, EDGE_MAX)


def clamp_desperation(value: int) -> int:
    """Clamp desperation to valid range (0-10)"""
    return clamp(value, DESPERATION_MIN, DESPERATION_MAX)
