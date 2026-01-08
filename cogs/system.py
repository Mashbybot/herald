"""
System Commands Cog for Herald Bot
Handles health checks, status, and administrative commands
"""

import discord
from discord import app_commands
from discord.ext import commands
import logging
import sys
import platform
from datetime import datetime

from config.settings import ENVIRONMENT, MAINTENANCE_MODE
from core.version import get_version_string, INSTANCE_ID, GIT_BRANCH

logger = logging.getLogger('Herald.System')


class System(commands.Cog):
    """System commands for health checks and bot status"""

    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger('Herald.System')
        self.start_time = datetime.utcnow()

    @app_commands.command(name="status", description="Check bot health and system status")
    async def status(self, interaction: discord.Interaction):
        """Display bot health and system information"""

        # Calculate uptime
        uptime = datetime.utcnow() - self.start_time
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{hours}h {minutes}m {seconds}s"

        # Check database connectivity
        db_status = "✅ Connected"
        try:
            from core.db import get_async_db
            async with get_async_db() as conn:
                await conn.fetchval("SELECT 1")
        except Exception as e:
            db_status = f"❌ Error: {str(e)[:50]}"
            logger.error(f"Database health check failed: {e}")

        # Create status embed
        embed = discord.Embed(
            title="🏹 Herald Bot Status",
            description="System health and information",
            color=0x228B22 if "✅" in db_status else 0xDC143C,
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="📊 Bot Information",
            value=f"**Uptime:** {uptime_str}\n"
                  f"**Environment:** {ENVIRONMENT}\n"
                  f"**Servers:** {len(self.bot.guilds)}\n"
                  f"**Users:** {len(set(self.bot.get_all_members()))}",
            inline=True
        )

        embed.add_field(
            name="🗄️ Database",
            value=f"**Type:** PostgreSQL\n"
                  f"**Status:** {db_status}",
            inline=True
        )

        embed.add_field(
            name="⚙️ System",
            value=f"**Python:** {platform.python_version()}\n"
                  f"**Discord.py:** {discord.__version__}\n"
                  f"**Platform:** {platform.system()}",
            inline=True
        )

        embed.add_field(
            name="🤖 Bot Version",
            value=f"**Version:** {get_version_string()}\n"
                  f"**Branch:** {GIT_BRANCH}\n"
                  f"**Instance:** `{INSTANCE_ID}`",
            inline=False
        )

        # Add maintenance mode warning if active
        if MAINTENANCE_MODE:
            embed.add_field(
                name="🚧 Maintenance Mode",
                value="Bot is currently in maintenance mode",
                inline=False
            )

        embed.set_footer(text=f"Latency: {round(self.bot.latency * 1000)}ms")

        await interaction.response.send_message(embed=embed)
        logger.info(f"Status check requested by {interaction.user}")

    @app_commands.command(name="ping", description="Check bot latency")
    async def ping(self, interaction: discord.Interaction):
        """Simple ping command to check bot responsiveness"""
        latency_ms = round(self.bot.latency * 1000)

        # Color based on latency
        if latency_ms < 100:
            color = 0x228B22  # Green
            status = "Excellent"
        elif latency_ms < 200:
            color = 0xFFA500  # Orange
            status = "Good"
        else:
            color = 0xDC143C  # Red
            status = "Poor"

        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"**Latency:** {latency_ms}ms ({status})",
            color=color
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    """Setup function for loading the cog"""
    await bot.add_cog(System(bot))
