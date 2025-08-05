import discord
import logging
from discord.ext import commands
from config.settings import DISCORD_TOKEN, GUILD_ID, DEBUG_MODE
from core.db import init_db

# TODO: Add file logging later - for now console output is sufficient
# Configure clean logging
def setup_logging():
    """Configure logging with clean, minimal output"""
    
    # Create formatter for clean output
    formatter = logging.Formatter(
        '%(asctime)s | %(name)-12s | %(levelname)-7s | %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Set specific logger levels to reduce noise
    logging.getLogger('discord').setLevel(logging.WARNING)  # Only warnings/errors
    logging.getLogger('discord.client').setLevel(logging.WARNING)
    logging.getLogger('discord.gateway').setLevel(logging.WARNING)
    logging.getLogger('discord.http').setLevel(logging.WARNING)
    logging.getLogger('discord.webhook').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    
    # Keep Herald logs at INFO level
    logging.getLogger('Herald').setLevel(logging.INFO)
    logging.getLogger('Herald.Database').setLevel(logging.INFO)
    logging.getLogger('Herald.Character').setLevel(logging.INFO)

# Initialize logging and create logger
setup_logging()
logger = logging.getLogger('Herald.Bot')

# Bot setup
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
has_synced = False  # Flag to ensure syncing happens only once

@bot.event
async def on_ready():
    """Bot startup event handler"""
    global has_synced
    logger.info(f"Bot is live as {bot.user}")
    
    # Initialize database
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return
    
    # Sync commands (guild-specific for development, global for production)
    if not has_synced:
        try:
            await bot.application_info()  # Ensure application_id is set
            
            if GUILD_ID:
                # Development: Fast guild-specific syncing
                guild = discord.Object(id=GUILD_ID)
                synced = await bot.tree.sync(guild=guild)
                logger.info(f"Synced {len(synced)} commands to development guild {guild.id}")
            else:
                # Production: Global syncing (takes up to 1 hour to propagate)
                synced = await bot.tree.sync()
                logger.info(f"Synced {len(synced)} commands globally (may take up to 1 hour)")
                
            has_synced = True
        except Exception as e:
            logger.error(f"Error syncing commands: {e}")

@bot.event
async def on_interaction(interaction: discord.Interaction):
    """Debug interaction logging"""
    if DEBUG_MODE:
        logger.debug(f"Received interaction: {interaction.data}")

async def load_cogs():
    """Load all bot cogs with error handling"""
    cogs = [
        "cogs.roll",
        "cogs.character"
    ]
    
    for cog in cogs:
        try:
            logger.info(f"Loading {cog}")
            await bot.load_extension(cog)
            logger.info(f"✅ {cog} loaded successfully")
        except Exception as e:
            logger.error(f"❌ Failed to load {cog}: {e}")
            raise  # Exit completely if any cog fails to load

async def main():
    """Main bot startup function"""
    logger.info("Starting Herald bot...")
    
    try:
        await load_cogs()
        await bot.start(DISCORD_TOKEN)
    except KeyboardInterrupt:
        logger.info("Bot shutdown requested")
    except Exception as e:
        logger.error(f"Fatal error starting bot: {e}")
        raise
    finally:
        await bot.close()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
