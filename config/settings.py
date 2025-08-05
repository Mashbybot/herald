import os
from dotenv import load_dotenv

load_dotenv()

# Required settings
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN environment variable is required")

# Database
DATABASE_PATH = os.getenv("DATABASE_PATH", "herald.db")

# Development settings
GUILD_ID = int(os.getenv("ADMIN_SERVER")) if os.getenv("ADMIN_SERVER") else None
DEBUG_MODE = os.getenv("DEBUG", "false").lower() == "true"

# Optional settings with defaults
OWNER_ID = int(os.getenv("OWNER_ID")) if os.getenv("OWNER_ID") else None
LOG_CHANNEL = int(os.getenv("LOG_CHANNEL")) if os.getenv("LOG_CHANNEL") else None
EMOJI_GUILD = int(os.getenv("EMOJI_GUILD")) if os.getenv("EMOJI_GUILD") else None

# Validate critical settings
if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN is required in .env file")
