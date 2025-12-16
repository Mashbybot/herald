"""
Tests for input validation utilities
"""

import pytest
from core.validation import (
    validate_character_name,
    validate_attribute,
    validate_skill,
    validate_text_field,
    validate_xp_amount,
    clamp,
    clamp_attribute,
    clamp_skill,
    sanitize_embed_text
)


class TestCharacterNameValidation:
    """Test character name validation"""

    def test_valid_name(self):
        """Test that valid names pass"""
        valid, error = validate_character_name("John Doe")
        assert valid is True
        assert error is None

    def test_short_name(self):
        """Test that short names are rejected"""
        valid, error = validate_character_name("X")
        assert valid is False
        assert "at least" in error

    def test_long_name(self):
        """Test that overly long names are rejected"""
        valid, error = validate_character_name("X" * 100)
        assert valid is False
        assert "or less" in error

    def test_empty_name(self):
        """Test that empty names are rejected"""
        valid, error = validate_character_name("")
        assert valid is False


class TestAttributeValidation:
    """Test attribute validation"""

    def test_valid_attributes(self):
        """Test that attributes 1-5 are valid"""
        for value in range(1, 6):
            valid, error = validate_attribute(value)
            assert valid is True
            assert error is None

    def test_attribute_too_low(self):
        """Test that attributes below 1 are rejected"""
        valid, error = validate_attribute(0)
        assert valid is False

    def test_attribute_too_high(self):
        """Test that attributes above 5 are rejected"""
        valid, error = validate_attribute(6)
        assert valid is False


class TestSkillValidation:
    """Test skill validation"""

    def test_valid_skills(self):
        """Test that skills 0-5 are valid"""
        for value in range(0, 6):
            valid, error = validate_skill(value)
            assert valid is True
            assert error is None

    def test_skill_too_high(self):
        """Test that skills above 5 are rejected"""
        valid, error = validate_skill(6)
        assert valid is False


class TestTextFieldValidation:
    """Test text field validation"""

    def test_valid_text(self):
        """Test that reasonable text passes"""
        valid, error = validate_text_field("My character's ambition", "Ambition")
        assert valid is True
        assert error is None

    def test_empty_optional_field(self):
        """Test that empty optional fields are accepted"""
        valid, error = validate_text_field("", "Ambition", required=False)
        assert valid is True

    def test_empty_required_field(self):
        """Test that empty required fields are rejected"""
        valid, error = validate_text_field("", "Ambition", required=True)
        assert valid is False

    def test_too_long_text(self):
        """Test that overly long text is rejected"""
        long_text = "X" * 1000
        valid, error = validate_text_field(long_text, "Ambition", max_length=200)
        assert valid is False


class TestXPValidation:
    """Test XP amount validation"""

    def test_positive_xp(self):
        """Test that positive XP amounts are valid"""
        valid, error = validate_xp_amount(100)
        assert valid is True

    def test_negative_xp(self):
        """Test that reasonable negative XP amounts are valid (for spending)"""
        valid, error = validate_xp_amount(-50)
        assert valid is True

    def test_unreasonably_large_xp(self):
        """Test that absurdly large XP amounts are rejected"""
        valid, error = validate_xp_amount(100000)
        assert valid is False


class TestClampFunctions:
    """Test value clamping functions"""

    def test_clamp_within_range(self):
        """Test that values within range are unchanged"""
        assert clamp(5, 0, 10) == 5

    def test_clamp_below_min(self):
        """Test that values below min are clamped"""
        assert clamp(-5, 0, 10) == 0

    def test_clamp_above_max(self):
        """Test that values above max are clamped"""
        assert clamp(15, 0, 10) == 10

    def test_clamp_attribute(self):
        """Test attribute clamping to 1-5"""
        assert clamp_attribute(0) == 1
        assert clamp_attribute(3) == 3
        assert clamp_attribute(10) == 5

    def test_clamp_skill(self):
        """Test skill clamping to 0-5"""
        assert clamp_skill(-1) == 0
        assert clamp_skill(3) == 3
        assert clamp_skill(10) == 5


class TestEmbedSanitization:
    """Test embed text sanitization"""

    def test_sanitize_short_text(self):
        """Test that short text is unchanged"""
        text = "Hello world"
        result = sanitize_embed_text(text)
        assert result == text

    def test_sanitize_long_text(self):
        """Test that long text is truncated"""
        text = "X" * 2000
        result = sanitize_embed_text(text, limit=100)
        assert len(result) <= 100
        assert result.endswith("...")

    def test_sanitize_empty_text(self):
        """Test that empty text returns empty string"""
        result = sanitize_embed_text("")
        assert result == ""

    def test_sanitize_null_bytes(self):
        """Test that null bytes are removed"""
        text = "Hello\x00World"
        result = sanitize_embed_text(text)
        assert "\x00" not in result
