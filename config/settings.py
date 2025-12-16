import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Critical settings - will fail if not present
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN environment variable is required")

# Database configuration
# For development: SQLite file
# For production: PostgreSQL connection string
DATABASE_URL = os.getenv("DATABASE_URL")
DATABASE_PATH = os.getenv("DATABASE_PATH", "herald.db")  # Fallback for local development

# Use PostgreSQL if DATABASE_URL is provided, SQLite otherwise
USE_POSTGRESQL = bool(DATABASE_URL)

# Development vs Production settings
GUILD_ID = int(os.getenv("ADMIN_SERVER")) if os.getenv("ADMIN_SERVER") else None
DEBUG_MODE = os.getenv("DEBUG", "false").lower() == "true"
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")  # development, production

# Optional settings with defaults
OWNER_ID = int(os.getenv("OWNER_ID")) if os.getenv("OWNER_ID") else None
LOG_CHANNEL = int(os.getenv("LOG_CHANNEL")) if os.getenv("LOG_CHANNEL") else None
EMOJI_GUILD = int(os.getenv("EMOJI_GUILD")) if os.getenv("EMOJI_GUILD") else None

# Production-specific settings
SENTRY_DSN = os.getenv("SENTRY_DSN")  # For error monitoring
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # For logging to Discord
MAX_GUILDS = int(os.getenv("MAX_GUILDS", "0"))  # 0 = no limit
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"

# Feature flags
MAINTENANCE_MODE = os.getenv("MAINTENANCE_MODE", "false").lower() == "true"
BETA_FEATURES = os.getenv("BETA_FEATURES", "false").lower() == "true"

# Validate critical settings
def validate_config():
    """Validate configuration settings and raise errors for invalid configs"""
    import os
    from pathlib import Path

    # Check Discord token format (basic validation)
    if DISCORD_TOKEN and len(DISCORD_TOKEN) < 50:
        raise ValueError("DISCORD_TOKEN appears to be invalid (too short)")

    # Production-specific validations
    if ENVIRONMENT == "production":
        if not DATABASE_URL:
            raise ValueError("DATABASE_URL is required for production environment")
        if GUILD_ID:
            raise ValueError("GUILD_ID should not be set in production (use global slash commands)")

    # Development-specific validations
    elif ENVIRONMENT == "development":
        if not USE_POSTGRESQL and not DATABASE_PATH:
            raise ValueError("DATABASE_PATH is required for SQLite in development mode")

        # Ensure database directory exists for SQLite
        if not USE_POSTGRESQL:
            db_path = Path(DATABASE_PATH)
            db_dir = db_path.parent
            if not db_dir.exists():
                try:
                    db_dir.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    raise ValueError(f"Cannot create database directory {db_dir}: {e}")

    # Validate numeric settings
    if OWNER_ID is not None and OWNER_ID <= 0:
        raise ValueError("OWNER_ID must be a positive integer (Discord user ID)")

    if GUILD_ID is not None and GUILD_ID <= 0:
        raise ValueError("GUILD_ID must be a positive integer (Discord server ID)")

    if MAX_GUILDS < 0:
        raise ValueError("MAX_GUILDS cannot be negative")

    return True


# Run validation
try:
    validate_config()
except ValueError as e:
    print(f"❌ Configuration Error: {e}")
    print(f"💡 Check your .env file and environment variables")
    raise

print(f"🔧 Herald configured for {ENVIRONMENT} environment")
print(f"🗄️ Database: {'PostgreSQL' if USE_POSTGRESQL else 'SQLite'}")
print(f"⚙️ Command scope: {'Guild-specific' if GUILD_ID else 'Global'}")
