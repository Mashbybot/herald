"""
Core constants for Herald bot.
Centralizes magic numbers, colors, limits, and configuration values.
"""

# ===== CACHE CONFIGURATION =====
CACHE_MAX_SIZE = 100
CACHE_TTL_SECONDS = 300  # 5 minutes
AUTOCOMPLETE_CACHE_TTL = 60  # 1 minute for autocomplete

# ===== DICE MECHANICS =====
MAX_EDGE_EXPLOSION_DEPTH = 10  # Maximum times edge dice can explode
MAX_DICE_POOL = 100  # Safety limit for total dice in a pool

# ===== CHARACTER LIMITS =====
CHAR_NAME_MIN_LENGTH = 2
CHAR_NAME_MAX_LENGTH = 32
TEXT_FIELD_MAX_LENGTH = 200  # For ambition, desire, drive, etc.
SPECIALTY_NAME_MAX_LENGTH = 50

# ===== ATTRIBUTE/SKILL RANGES =====
ATTRIBUTE_MIN = 1
ATTRIBUTE_MAX = 5
SKILL_MIN = 0
SKILL_MAX = 5
EDGE_MIN = 0
EDGE_MAX = 5
DESPERATION_MIN = 0
DESPERATION_MAX = 10
DANGER_MIN = 0
DANGER_MAX = 5

# ===== DISCORD EMBED LIMITS =====
# Official Discord limits
EMBED_TITLE_LIMIT = 256
EMBED_DESCRIPTION_LIMIT = 4096
EMBED_FIELD_NAME_LIMIT = 256
EMBED_FIELD_VALUE_LIMIT = 1024
EMBED_FOOTER_LIMIT = 2048
EMBED_AUTHOR_LIMIT = 256
EMBED_TOTAL_LIMIT = 6000
MAX_EMBEDS_PER_MESSAGE = 10

# ===== UI DISPLAY LIMITS =====
MAX_SKILLS_DISPLAY = 20  # Maximum skills to show before truncating
MAX_AUTOCOMPLETE_RESULTS = 25  # Discord's autocomplete limit
MAX_EQUIPMENT_DISPLAY = 15
MAX_NOTES_DISPLAY = 10
MAX_XP_LOG_DISPLAY = 15

# ===== COLORS =====
# Theme colors for embeds
COLOR_HUNTER_RED = 0x8B0000      # Dark red - main Herald theme
COLOR_SUCCESS = 0x228B22         # Forest green
COLOR_ERROR = 0xDC143C           # Crimson red
COLOR_WARNING = 0xFFA500         # Orange
COLOR_INFO = 0x4169E1            # Royal blue
COLOR_NEUTRAL = 0x808080         # Gray

# Dice result colors
COLOR_CRITICAL_SUCCESS = 0xFFD700  # Gold
COLOR_SUCCESS_DICE = 0x32CD32      # Lime green
COLOR_FAILURE = 0xB22222           # Firebrick red
COLOR_MESSY_CRITICAL = 0x8B0000    # Dark red

# ===== DATABASE =====
DB_POOL_MIN_SIZE = 1
DB_POOL_MAX_SIZE = 5
DB_COMMAND_TIMEOUT = 60  # seconds
DB_RETRY_ATTEMPTS = 3
DB_RETRY_DELAY = 1  # seconds

# ===== PAGINATION =====
CHARACTERS_PER_PAGE = 10
XP_LOG_PER_PAGE = 10
EQUIPMENT_PER_PAGE = 10
NOTES_PER_PAGE = 5

# ===== BUTTON TIMEOUTS =====
CONFIRMATION_TIMEOUT = 30  # seconds for deletion confirmations
PAGINATION_TIMEOUT = 180   # 3 minutes for pagination
SELECTION_TIMEOUT = 60     # 1 minute for selection menus

# ===== VALID ATTRIBUTES =====
VALID_ATTRIBUTES = frozenset([
    'strength', 'dexterity', 'stamina',
    'charisma', 'manipulation', 'composure',
    'intelligence', 'wits', 'resolve'
])

# ===== EMOJI IDENTIFIERS =====
# Used for consistency across the bot
EMOJI_SUCCESS = "✅"
EMOJI_ERROR = "❌"
EMOJI_WARNING = "⚠️"
EMOJI_INFO = "ℹ️"
EMOJI_LOADING = "⏳"
EMOJI_HUNTER = "🏹"
EMOJI_HEALTH = "❤️"
EMOJI_WILLPOWER = "💙"
EMOJI_EDGE = "⭐"
EMOJI_DESPERATION = "🔥"
EMOJI_XP = "✨"
EMOJI_DICE = "🎲"
EMOJI_SEPARATOR = "─────────────────"

# ===== VALIDATION PATTERNS =====
# Regex patterns for input validation (if needed in the future)
# Currently using simple length/range checks, but these are here for reference
CHAR_NAME_PATTERN = r"^[a-zA-Z0-9\s\-'\.]+$"  # Alphanumeric, spaces, hyphens, apostrophes, periods
