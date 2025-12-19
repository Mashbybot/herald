import discord
import logging
import asyncio
from discord.ext import commands
from config.settings import DISCORD_TOKEN, GUILD_ID, DEBUG_MODE
from core.db import init_database

# Configure logging for production
def setup_logging():
    """Configure logging for production environment"""
    
    # Clean formatter
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
    """Herald - Hunter: The Reckoning 5E Discord Bot - Production Ready"""
    
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
        self.logger.info("🏹 Starting Herald bot setup...")

        # Initialize database
        try:
            await init_database()
            self.logger.info("✅ Database initialized successfully")
        except Exception as e:
            self.logger.error(f"❌ Database initialization failed: {e}")
            raise

        # Ensure H5E columns exist (migration for existing databases)
        try:
            from core.character_utils import ensure_h5e_columns
            await ensure_h5e_columns()
            self.logger.info("✅ H5E database schema verified")
        except Exception as e:
            self.logger.error(f"❌ H5E schema verification failed: {e}")
            raise

        # Load all cogs
        cogs_to_load = [
            'cogs.system',
            'cogs.character_management',
            'cogs.character_gameplay',
            'cogs.character_progression',
            'cogs.character_inventory',
            'cogs.dice_rolling',
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
        
        self.logger.info(f"📦 Cog loading complete: {loaded_cogs} loaded, {failed_cogs} failed")
        
        # Sync commands
        try:
            if GUILD_ID:
                # Development mode - sync to specific guild (instant updates)
                guild = discord.Object(id=GUILD_ID)
                synced = await self.tree.sync(guild=guild)
                self.logger.info(f"⚡ Synced {len(synced)} commands to guild {GUILD_ID} (instant)")
            else:
                # Production mode - sync globally (may take up to 1 hour)
                synced = await self.tree.sync()
                self.logger.info(f"🌍 Synced {len(synced)} commands globally")
                self.logger.warning(f"⏰ Global command sync can take up to 1 hour to propagate to all servers")
        except Exception as e:
            self.logger.error(f"❌ Command sync failed: {e}")

    async def on_ready(self):
        """Called when the bot has successfully connected to Discord"""
        from config.settings import MAINTENANCE_MODE

        self.logger.info(f"🏹 {self.user} has connected to Discord!")
        self.logger.info(f"🆔 Bot ID: {self.user.id}")
        self.logger.info(f"🏰 Guilds: {len(self.guilds)}")
        self.logger.info(f"👥 Users: {len(set(self.get_all_members()))}")

        # Start rotating presence messages (respects maintenance mode)
        self.loop.create_task(self.rotate_presence())
        self.logger.info("🎯 Bot status rotation started")

    async def rotate_presence(self):
        """Rotate presence messages every 5 minutes with Herald's voice"""
        from config.settings import MAINTENANCE_MODE

        presence_messages = [
            "🔸 Tracking patterns",
            "🔸 Protocol established",
            "🔸 What are we Hunting?",
            "🔸 /help | Herald the Reckoning"
        ]

        index = 0
        await self.wait_until_ready()

        while not self.is_closed():
            try:
                # Check maintenance mode on each iteration
                if MAINTENANCE_MODE:
                    activity = discord.Activity(
                        type=discord.ActivityType.watching,
                        name="🚧 Maintenance Mode"
                    )
                else:
                    activity = discord.Activity(
                        type=discord.ActivityType.playing,
                        name=presence_messages[index]
                    )

                await self.change_presence(activity=activity)

                # Only rotate index in normal mode
                if not MAINTENANCE_MODE:
                    index = (index + 1) % len(presence_messages)

                await asyncio.sleep(300)  # 5 minutes

            except Exception as e:
                self.logger.error(f"Error rotating presence: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error before retrying

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Global check for all interactions - handle maintenance mode"""
        from config.settings import MAINTENANCE_MODE, OWNER_ID

        # Allow owner to bypass maintenance mode
        if MAINTENANCE_MODE and (OWNER_ID is None or interaction.user.id != OWNER_ID):
            await interaction.response.send_message(
                "🚧 **Maintenance Mode**\n\n"
                "Herald is currently undergoing maintenance. Please check back soon!\n\n"
                "For updates, visit our support server.",
                ephemeral=True
            )
            return False

        return True

    async def on_app_command_error(self, interaction: discord.Interaction, error: Exception):
        """Global error handler for slash commands"""
        self.logger.error(f"❌ Command error in {interaction.command}: {error}")
        
        # Try to respond to the user
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "⚠️ An error occurred while processing your command. Please try again.", 
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    "⚠️ An error occurred while processing your command. Please try again.", 
                    ephemeral=True
                )
        except:
            # If we can't respond, just log it
            self.logger.error(f"❌ Could not send error message to user for command {interaction.command}")

    async def on_guild_join(self, guild):
        """Called when the bot joins a new guild"""
        self.logger.info(f"🎉 Joined new guild: {guild.name} (ID: {guild.id}) | Members: {guild.member_count}")

    async def on_guild_remove(self, guild):
        """Called when the bot leaves a guild"""
        self.logger.info(f"👋 Left guild: {guild.name} (ID: {guild.id})")

    async def close(self):
        """Clean shutdown"""
        self.logger.info("🔄 Shutting down Herald bot...")

        # Close database connections
        from core.db import close_database
        try:
            await close_database()
        except Exception as e:
            self.logger.error(f"❌ Error closing database: {e}")

        await super().close()


def main():
    """Main entry point for production"""
    # Set up logging
    setup_logging()
    
    # Create and run bot
    bot = HeraldBot()
    
    try:
        asyncio.run(bot.start(DISCORD_TOKEN))
    except discord.LoginFailure:
        logging.getLogger('Herald.Bot').error("❌ Invalid Discord token. Check your environment variables.")
    except KeyboardInterrupt:
        logging.getLogger('Herald.Bot').info("🛑 Bot shutdown requested by user")
    except Exception as e:
        logging.getLogger('Herald.Bot').error(f"❌ Bot startup failed: {e}")


if __name__ == '__main__':
    main()
