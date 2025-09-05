import discord
import logging
from discord.ext import commands
from config.settings import DISCORD_TOKEN, GUILD_ID, DEBUG_MODE
from core.db import init_db

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


class HeraldBot(commands.Bot):
    """Herald - Hunter: The Reckoning 5E Discord Bot"""
    
    def __init__(self):
        # Set up intents
        intents = discord.Intents.default()
        intents.message_content = True  # Required for message content access
        
        super().__init__(
            command_prefix='!',  # Legacy prefix (slash commands are primary)
            intents=intents,
            help_command=None  # Disable default help (we have custom /help)
        )
        
        self.logger = logging.getLogger('Herald.Bot')

    async def setup_hook(self):
        """Called when the bot is starting up"""
        self.logger.info("Starting Herald bot setup...")
        
        # Initialize database
        try:
            init_db()
            self.logger.info("Database initialized successfully")
        except Exception as e:
            self.logger.error(f"Database initialization failed: {e}")
            raise
        
        # Load all cogs
        cogs_to_load = [
            'cogs.character_management',
            'cogs.character_gameplay', 
            'cogs.character_progression',
            'cogs.character_inventory',
            'cogs.dice_rolling',
            # Add other cogs here as you create them:
            # 'cogs.dice_rolling',
            # 'cogs.game_master',
            # etc.
        ]
        
        loaded_cogs = 0
        failed_cogs = 0
        
        for cog in cogs_to_load:
            try:
                await self.load_extension(cog)
                self.logger.info(f"✅ Loaded {cog}")
                loaded_cogs += 1
            except Exception as e:
                self.logger.error(f"❌ Failed to load {cog}: {e}")
                failed_cogs += 1
        
        self.logger.info(f"Cog loading complete: {loaded_cogs} loaded, {failed_cogs} failed")
        
        # Sync commands
        try:
            if GUILD_ID:
                # Development mode - sync to specific guild (faster)
                guild = discord.Object(id=GUILD_ID)
                self.tree.copy_global_to(guild=guild)
                synced = await self.tree.sync(guild=guild)
                self.logger.info(f"⚡ Synced {len(synced)} commands to development guild {GUILD_ID}")
            else:
                # Production mode - sync globally (slower, up to 1 hour)
                synced = await self.tree.sync()
                self.logger.info(f"🌍 Synced {len(synced)} commands globally (may take up to 1 hour to appear)")
        except Exception as e:
            self.logger.error(f"❌ Command sync failed: {e}")

    async def on_ready(self):
        """Called when the bot has successfully connected to Discord"""
        self.logger.info(f"🏹 {self.user} has connected to Discord!")
        self.logger.info(f"Bot ID: {self.user.id}")
        self.logger.info(f"Guilds: {len(self.guilds)}")
        self.logger.info(f"Users: {len(set(self.get_all_members()))}")
        
        # Set bot status
        activity = discord.Activity(
            type=discord.ActivityType.playing,
            name="Hunter: The Reckoning 5E | /help"
        )
        await self.change_presence(activity=activity)

    async def on_app_command_error(self, interaction: discord.Interaction, error: Exception):
        """Global error handler for slash commands"""
        self.logger.error(f"Command error in {interaction.command}: {error}")
        
        # Try to respond to the user
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ An error occurred while processing your command. Please try again.", 
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    "❌ An error occurred while processing your command. Please try again.", 
                    ephemeral=True
                )
        except:
            # If we can't respond, just log it
            self.logger.error(f"Could not send error message to user for command {interaction.command}")

    async def on_guild_join(self, guild):
        """Called when the bot joins a new guild"""
        self.logger.info(f"🎉 Joined new guild: {guild.name} (ID: {guild.id})")

    async def on_guild_remove(self, guild):
        """Called when the bot leaves a guild"""
        self.logger.info(f"👋 Left guild: {guild.name} (ID: {guild.id})")


def main():
    """Main entry point"""
    # Set up logging first
    setup_logging()
    
    # Create and run bot
    bot = HeraldBot()
    
    try:
        bot.run(DISCORD_TOKEN)
    except discord.LoginFailure:
        logging.getLogger('Herald.Bot').error("❌ Invalid Discord token. Check your settings.")
    except Exception as e:
        logging.getLogger('Herald.Bot').error(f"❌ Bot startup failed: {e}")


if __name__ == '__main__':
    main()
