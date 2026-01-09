import discord
import logging
import asyncio
import signal
import sys
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
        self.health_runner = None  # Will store the health check server runner

    async def setup_hook(self):
        """Called when the bot is starting up"""
        self.logger.info("🏹 Starting Herald bot setup...")

        # Start health check server first (so Railway can monitor startup)
        from core.health import start_health_server, set_bot_instance
        import os

        # Railway expects PORT env variable for web services
        # Try PORT first (Railway), then HEALTH_PORT, then default to 8080
        health_port = int(os.getenv('PORT', os.getenv('HEALTH_PORT', '8080')))
        try:
            self.health_runner = await start_health_server(port=health_port)
            set_bot_instance(self)
        except Exception as e:
            self.logger.warning(f"⚠️ Could not start health check server: {e}")

        # Test database connectivity first
        try:
            from core.db import test_database_connection
            await test_database_connection()
            self.logger.info("✅ Database connection verified")
        except Exception as e:
            self.logger.error(f"❌ Database connection test failed: {e}", exc_info=True)
            raise

        # Initialize database
        try:
            await init_database()
            self.logger.info("✅ Database initialized successfully")
        except Exception as e:
            self.logger.error(f"❌ Database initialization failed: {e}", exc_info=True)
            raise

        # Ensure H5E columns exist (migration for existing databases)
        try:
            from core.character_utils import ensure_h5e_columns
            await ensure_h5e_columns()
            self.logger.info("✅ H5E database schema verified")
        except Exception as e:
            self.logger.error(f"❌ H5E schema verification failed: {e}", exc_info=True)
            raise

        # Load all cogs
        cogs_to_load = [
            'cogs.system',  # Re-enabled - users need /status and /ping commands
            'cogs.character_management',
            'cogs.character_gameplay',
            'cogs.character_progression',
            # 'cogs.character_inventory',  # Disabled - notes command removed, journal system coming later
            'cogs.dice_rolling',
        ]

        # Define critical cogs that must load successfully
        critical_cogs = {
            'cogs.character_management',
            'cogs.dice_rolling'
        }

        loaded_cogs = 0
        failed_cogs = 0
        failed_critical_cogs = []

        for cog in cogs_to_load:
            try:
                await self.load_extension(cog)
                self.logger.info(f"✅ Loaded {cog}")
                loaded_cogs += 1
            except Exception as e:
                self.logger.error(f"❌ Failed to load {cog}: {e}", exc_info=True)
                failed_cogs += 1
                if cog in critical_cogs:
                    failed_critical_cogs.append(cog)

        self.logger.info(f"📦 Cog loading complete: {loaded_cogs} loaded, {failed_cogs} failed")

        # Fail startup if critical cogs didn't load
        if failed_critical_cogs:
            error_msg = f"Critical cogs failed to load: {', '.join(failed_critical_cogs)}"
            self.logger.critical(f"❌ {error_msg}")
            raise RuntimeError(error_msg)

        # Sync commands - manually clear Discord's cache to force parameter updates
        try:
            # ALWAYS clear global commands first (in case old global commands exist)
            self.logger.info(f"🧹 Clearing ALL old global commands from Discord API...")
            try:
                global_commands = await self.tree.fetch_commands()
                for cmd in global_commands:
                    try:
                        await self.http.delete_global_command(cmd.id)
                        self.logger.info(f"   🗑️ Deleted global command: {cmd.name}")
                    except Exception as e:
                        self.logger.warning(f"   ⚠️ Could not delete global command {cmd.name}: {e}")
                self.logger.info(f"🗑️ Removed {len(global_commands)} old global commands from Discord")
            except Exception as e:
                self.logger.warning(f"⚠️ Could not fetch/delete global commands: {e}")

            if GUILD_ID:
                # Development mode - sync to specific guild (instant updates)
                guild = discord.Object(id=GUILD_ID)

                # Clear all guild-specific commands
                self.logger.info(f"🧹 Clearing old guild commands from Discord API (Guild {GUILD_ID})...")
                try:
                    current_commands = await self.tree.fetch_commands(guild=guild)
                    for cmd in current_commands:
                        try:
                            await self.http.delete_guild_command(GUILD_ID, cmd.id)
                            self.logger.info(f"   🗑️ Deleted guild command: {cmd.name}")
                        except Exception as e:
                            self.logger.warning(f"   ⚠️ Could not delete guild command {cmd.name}: {e}")
                    self.logger.info(f"🗑️ Removed {len(current_commands)} old guild commands from Discord")
                except Exception as e:
                    self.logger.warning(f"⚠️ Could not fetch/delete guild commands: {e}")

                # Now sync new command signatures to guild
                synced = await self.tree.sync(guild=guild)
                self.logger.info(f"⚡ Synced {len(synced)} NEW commands to guild {GUILD_ID} (instant)")

                # Verify sync was successful
                if not synced:
                    raise RuntimeError("Command sync returned empty list - sync failed")

                # Log synced command names for verification
                command_names = [cmd.name for cmd in synced]
                self.logger.info(f"✅ Registered commands: {', '.join(command_names)}")
            else:
                # Production mode - sync globally (may take up to 1 hour)
                # Global commands were already cleared above

                # Now sync new command signatures globally
                synced = await self.tree.sync()
                self.logger.info(f"🌍 Synced {len(synced)} NEW commands globally")

                # Verify sync was successful
                if not synced:
                    raise RuntimeError("Global command sync returned empty list - sync failed")

                # Log synced command names for verification
                command_names = [cmd.name for cmd in synced]
                self.logger.info(f"✅ Registered commands: {', '.join(command_names)}")
                self.logger.warning(f"⏰ Global command sync can take up to 1 hour to propagate to all servers")

        except Exception as e:
            self.logger.error(f"❌ Command sync failed: {e}", exc_info=True)
            raise  # Make command sync failure fatal

    async def on_ready(self):
        """Called when the bot has successfully connected to Discord"""
        from config.settings import MAINTENANCE_MODE
        from core.version import get_version_string, INSTANCE_ID, GIT_BRANCH
        from core.health import set_ready
        import os

        self.logger.info(f"🏹 {self.user} has connected to Discord!")
        self.logger.info(f"🤖 Version: {get_version_string()} | Branch: {GIT_BRANCH} | Instance: {INSTANCE_ID}")
        self.logger.info(f"🆔 Bot ID: {self.user.id}")
        self.logger.info(f"🏰 Guilds: {len(self.guilds)}")
        self.logger.info(f"👥 Users: {len(set(self.get_all_members()))}")

        # Mark bot as ready for health checks
        set_ready(True)

        # Create readiness marker for health checks
        try:
            os.makedirs('/tmp', exist_ok=True)
            with open('/tmp/herald_ready', 'w') as f:
                f.write(f"{INSTANCE_ID}\n{get_version_string()}")
            self.logger.info("✅ Readiness marker created at /tmp/herald_ready")
        except Exception as e:
            self.logger.warning(f"⚠️ Could not create readiness marker: {e}")

        # Log structured startup complete message for monitoring
        self.logger.info(f"STARTUP_COMPLETE version={get_version_string()} instance={INSTANCE_ID} guilds={len(self.guilds)}")

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
                self.logger.error(f"Error rotating presence: {e}", exc_info=True)
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
        self.logger.error(
            f"❌ Command error in {interaction.command}: {error}",
            exc_info=True,
            extra={
                "user_id": interaction.user.id,
                "guild_id": interaction.guild_id,
                "command": interaction.command.name if interaction.command else "unknown"
            }
        )

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
        except Exception as e:
            # If we can't respond, log it with details
            self.logger.error(
                f"❌ Could not send error message to user for command {interaction.command}",
                exc_info=True
            )

    async def on_guild_join(self, guild):
        """Called when the bot joins a new guild"""
        self.logger.info(f"🎉 Joined new guild: {guild.name} (ID: {guild.id}) | Members: {guild.member_count}")

    async def on_guild_remove(self, guild):
        """Called when the bot leaves a guild"""
        self.logger.info(f"👋 Left guild: {guild.name} (ID: {guild.id})")

    async def close(self):
        """Clean shutdown"""
        from core.version import INSTANCE_ID
        from core.health import set_ready

        self.logger.info(f"🔄 Shutting down Herald bot (Instance: {INSTANCE_ID})...")

        # Mark as not ready for health checks
        set_ready(False)

        # Close health check server
        if self.health_runner:
            try:
                await self.health_runner.cleanup()
                self.logger.info("✅ Health check server stopped")
            except Exception as e:
                self.logger.error(f"❌ Error stopping health check server: {e}")

        # Close database connections
        from core.db import close_database
        try:
            await asyncio.wait_for(close_database(), timeout=5.0)
        except asyncio.TimeoutError:
            self.logger.error("❌ Database close timed out - force closing")
        except Exception as e:
            self.logger.error(f"❌ Error closing database: {e}", exc_info=True)

        await super().close()


def main():
    """Main entry point for production"""
    # Set up logging
    setup_logging()
    logger = logging.getLogger('Herald.Bot')

    # Create bot
    bot = HeraldBot()

    # Set up signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        """Handle shutdown signals from Railway or container orchestrator"""
        sig_name = signal.Signals(signum).name
        logger.info(f"🛑 Received {sig_name} signal, initiating graceful shutdown...")
        # Create a task to close the bot gracefully
        if bot.loop and not bot.loop.is_closed():
            bot.loop.create_task(bot.close())

    # Register signal handlers (Railway sends SIGTERM on deployment)
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        asyncio.run(bot.start(DISCORD_TOKEN))
    except discord.LoginFailure:
        logger.error("❌ Invalid Discord token. Check your environment variables.")
        sys.exit(1)  # Exit code 1: Authentication failure
    except KeyboardInterrupt:
        logger.info("🛑 Bot shutdown requested by user")
        sys.exit(0)  # Exit code 0: Clean shutdown
    except Exception as e:
        logger.error(f"❌ Bot startup failed: {e}", exc_info=True)
        sys.exit(2)  # Exit code 2: Startup failure


if __name__ == '__main__':
    main()
