"""
Character Gameplay Cog for Herald Bot
Handles game mechanics: damage, healing, Edge, Desperation, Creed, H5E character mechanics
"""

import discord
from discord import app_commands
from discord.ext import commands
from typing import List, Optional
import logging

from core.db import get_async_db
from core.character_utils import (
    find_character, character_autocomplete, get_character_and_skills,
    ensure_h5e_columns, ALL_SKILLS, H5E_SKILLS, HeraldMessages, resolve_character,
    get_active_character
)
from core.ui_utils import (
    HeraldEmojis, HeraldMessages, HeraldColors, create_health_bar, create_willpower_bar
)
from config.settings import GUILD_ID

logger = logging.getLogger('Herald.Character.Gameplay')


def safe_get_character_field(character, field, default=None):
    """Safely get a field from database record with default value"""
    try:
        value = character[field]
        return value if value is not None else default
    except (KeyError, IndexError):
        return default


def create_desperation_bar(desperation: int) -> str:
    """Create a visual desperation bar (0-10)"""
    filled = "🔴" * desperation
    empty = "⚫" * (10 - desperation)
    return f"`[{filled}{empty}]` {desperation}/10"


# ===== VIEW CLASSES =====

class CreedSelectionView(discord.ui.View):
    """Interactive button view for selecting Hunter Creed"""

    def __init__(self, user_id: str, character_name: str, timeout: float = 60):
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.character_name = character_name
        self.selected_creed = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Ensure only the original user can interact"""
        return str(interaction.user.id) == self.user_id

    @discord.ui.button(label="Entrepreneurial", style=discord.ButtonStyle.primary, emoji="🔨")
    async def entrepreneurial_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._set_creed(interaction, "Entrepreneurial", "Building, inventing, repairing")

    @discord.ui.button(label="Faithful", style=discord.ButtonStyle.primary, emoji="✝️")
    async def faithful_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._set_creed(interaction, "Faithful", "Direct conflict with the supernatural")

    @discord.ui.button(label="Inquisitive", style=discord.ButtonStyle.primary, emoji="🔍")
    async def inquisitive_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._set_creed(interaction, "Inquisitive", "Gaining information")

    @discord.ui.button(label="Martial", style=discord.ButtonStyle.primary, emoji="⚔️")
    async def martial_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._set_creed(interaction, "Martial", "Physical conflict")

    @discord.ui.button(label="Underground", style=discord.ButtonStyle.primary, emoji="🎭")
    async def underground_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._set_creed(interaction, "Underground", "Stealth and subterfuge")

    async def _set_creed(self, interaction: discord.Interaction, creed: str, description: str):
        """Set the character's creed"""
        try:
            from core.db import get_async_db
            async with get_async_db() as conn:
                await conn.execute(
                    "UPDATE characters SET creed = $1 WHERE user_id = $2 AND name = $3",
                    creed, self.user_id, self.character_name
                )

            # Invalidate cache to ensure /sheet shows updated value
            from core.character_utils import invalidate_character_cache
            invalidate_character_cache(self.user_id, self.character_name)

            embed = discord.Embed(
                title=f"{HeraldEmojis.CREED} Creed Set",
                description=f"**{self.character_name}'s Creed:** {creed}\n\n*{description}*",
                color=0x8B0000
            )
            embed.set_footer(text="Use Desperation dice when your action aligns with your Creed Field")

            # Disable all buttons
            for item in self.children:
                item.disabled = True

            await interaction.response.edit_message(embed=embed, view=self)
            self.selected_creed = creed
            self.stop()

        except Exception as e:
            logger.error(f"Error setting creed: {e}")
            await interaction.response.send_message(
                f"{HeraldEmojis.ERROR} Error setting creed",
                ephemeral=True
            )


class DriveSelectionView(discord.ui.View):
    """Interactive button view for selecting Hunter Drive"""

    DRIVE_REDEMPTIONS = {
        "Curiosity": "Uncover new information about your quarry",
        "Vengeance": "Hurt your quarry",
        "Oath": "Actively uphold or fulfill your oath",
        "Greed": "Acquire resources from enemies",
        "Pride": "Best your quarry in some contest",
        "Envy": "Ally with your quarry",
        "Atonement": "Protect someone from your quarry"
    }

    def __init__(self, user_id: str, character_name: str, timeout: float = 60):
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.character_name = character_name
        self.selected_drive = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Ensure only the original user can interact"""
        return str(interaction.user.id) == self.user_id

    @discord.ui.button(label="Curiosity", style=discord.ButtonStyle.primary, emoji="🔍", row=0)
    async def curiosity_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._set_drive(interaction, "Curiosity")

    @discord.ui.button(label="Vengeance", style=discord.ButtonStyle.primary, emoji="⚔️", row=0)
    async def vengeance_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._set_drive(interaction, "Vengeance")

    @discord.ui.button(label="Oath", style=discord.ButtonStyle.primary, emoji="🤝", row=0)
    async def oath_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._set_drive(interaction, "Oath")

    @discord.ui.button(label="Greed", style=discord.ButtonStyle.primary, emoji="💰", row=1)
    async def greed_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._set_drive(interaction, "Greed")

    @discord.ui.button(label="Pride", style=discord.ButtonStyle.primary, emoji="👑", row=1)
    async def pride_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._set_drive(interaction, "Pride")

    @discord.ui.button(label="Envy", style=discord.ButtonStyle.primary, emoji="💚", row=1)
    async def envy_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._set_drive(interaction, "Envy")

    @discord.ui.button(label="Atonement", style=discord.ButtonStyle.primary, emoji="🕊️", row=2)
    async def atonement_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._set_drive(interaction, "Atonement")

    async def _set_drive(self, interaction: discord.Interaction, drive: str):
        """Set the character's drive and redemption"""
        try:
            redemption = self.DRIVE_REDEMPTIONS[drive]

            from core.db import get_async_db
            async with get_async_db() as conn:
                await conn.execute(
                    "UPDATE characters SET drive = $1, redemption = $2 WHERE user_id = $3 AND name = $4",
                    drive, redemption, self.user_id, self.character_name
                )

            # Invalidate cache to ensure /sheet shows updated value
            from core.character_utils import invalidate_character_cache
            invalidate_character_cache(self.user_id, self.character_name)

            embed = discord.Embed(
                title=f"{HeraldEmojis.DRIVE} Drive Set",
                description=f"**{self.character_name}'s Drive:** {drive}",
                color=0x8B0000
            )

            embed.add_field(
                name=f"{HeraldEmojis.REDEMPTION} Redemption",
                value=redemption,
                inline=False
            )

            embed.set_footer(text="Achieve your Redemption to recover from Despair")

            # Disable all buttons
            for item in self.children:
                item.disabled = True

            await interaction.response.edit_message(embed=embed, view=self)
            self.selected_drive = drive
            self.stop()

        except Exception as e:
            logger.error(f"Error setting drive: {e}")
            await interaction.response.send_message(
                f"{HeraldEmojis.ERROR} Error setting drive",
                ephemeral=True
            )


class EdgeSelectionView(discord.ui.View):
    """Interactive button view for selecting Hunter Edges"""

    # All 17 edges organized by category
    EDGES = {
        # Assets (5)
        "Arsenal": "Access to weapons and military equipment",
        "Fleet": "Access to vehicles and transportation",
        "Ordnance": "Access to explosives and munitions",
        "Library": "Access to information and research",
        "Experimental Medicine": "Access to medical experiments and healing",

        # Aptitudes (5)
        "Improvised Gear": "Create short-lived useful tools",
        "Global Access": "Digital larceny and hacking",
        "Drone Jockey": "Control drones for surveillance/combat",
        "Beast Whisperer": "Loyal animal companions",
        "Turncoat": "Double agent abilities",

        # Endowments (7)
        "Sense the Unnatural": "Detect supernatural presence",
        "Repel the Unnatural": "Repel supernatural creatures",
        "Thwart the Unnatural": "Resist supernatural abilities",
        "Artifact": "Rare supernatural relic",
        "Cleanse the Unnatural": "Remove supernatural influence",
        "Great Destiny": "Empowered by higher purpose",
        "Unnatural Changes": "Use body in supernatural ways"
    }

    def __init__(self, user_id: str, character_name: str, timeout: float = 60):
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.character_name = character_name
        self.selected_edge = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Ensure only the original user can interact"""
        return str(interaction.user.id) == self.user_id

    # Assets Row 1 (5 edges)
    @discord.ui.button(label="Arsenal", style=discord.ButtonStyle.secondary, row=0)
    async def arsenal_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._add_edge(interaction, "Arsenal")

    @discord.ui.button(label="Fleet", style=discord.ButtonStyle.secondary, row=0)
    async def fleet_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._add_edge(interaction, "Fleet")

    @discord.ui.button(label="Ordnance", style=discord.ButtonStyle.secondary, row=0)
    async def ordnance_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._add_edge(interaction, "Ordnance")

    @discord.ui.button(label="Library", style=discord.ButtonStyle.secondary, row=0)
    async def library_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._add_edge(interaction, "Library")

    @discord.ui.button(label="Experimental Medicine", style=discord.ButtonStyle.secondary, row=0)
    async def experimental_medicine_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._add_edge(interaction, "Experimental Medicine")

    # Aptitudes Row 2 (5 edges)
    @discord.ui.button(label="Improvised Gear", style=discord.ButtonStyle.secondary, row=1)
    async def improvised_gear_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._add_edge(interaction, "Improvised Gear")

    @discord.ui.button(label="Global Access", style=discord.ButtonStyle.secondary, row=1)
    async def global_access_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._add_edge(interaction, "Global Access")

    @discord.ui.button(label="Drone Jockey", style=discord.ButtonStyle.secondary, row=1)
    async def drone_jockey_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._add_edge(interaction, "Drone Jockey")

    @discord.ui.button(label="Beast Whisperer", style=discord.ButtonStyle.secondary, row=1)
    async def beast_whisperer_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._add_edge(interaction, "Beast Whisperer")

    @discord.ui.button(label="Turncoat", style=discord.ButtonStyle.secondary, row=1)
    async def turncoat_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._add_edge(interaction, "Turncoat")

    # Endowments Row 3-4 (7 edges)
    @discord.ui.button(label="Sense the Unnatural", style=discord.ButtonStyle.secondary, row=2)
    async def sense_unnatural_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._add_edge(interaction, "Sense the Unnatural")

    @discord.ui.button(label="Repel the Unnatural", style=discord.ButtonStyle.secondary, row=2)
    async def repel_unnatural_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._add_edge(interaction, "Repel the Unnatural")

    @discord.ui.button(label="Thwart the Unnatural", style=discord.ButtonStyle.secondary, row=2)
    async def thwart_unnatural_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._add_edge(interaction, "Thwart the Unnatural")

    @discord.ui.button(label="Artifact", style=discord.ButtonStyle.secondary, row=2)
    async def artifact_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._add_edge(interaction, "Artifact")

    @discord.ui.button(label="Cleanse the Unnatural", style=discord.ButtonStyle.secondary, row=3)
    async def cleanse_unnatural_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._add_edge(interaction, "Cleanse the Unnatural")

    @discord.ui.button(label="Great Destiny", style=discord.ButtonStyle.secondary, row=3)
    async def great_destiny_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._add_edge(interaction, "Great Destiny")

    @discord.ui.button(label="Unnatural Changes", style=discord.ButtonStyle.secondary, row=3)
    async def unnatural_changes_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._add_edge(interaction, "Unnatural Changes")

    async def _add_edge(self, interaction: discord.Interaction, edge_name: str):
        """Add an edge to the character"""
        try:
            description = self.EDGES[edge_name]

            from core.db import get_async_db
            async with get_async_db() as conn:
                # Check if edge already exists
                existing = await conn.fetchrow(
                    "SELECT edge_name FROM edges WHERE user_id = $1 AND character_name = $2 AND edge_name = $3",
                    self.user_id, self.character_name, edge_name
                )

                if existing:
                    await interaction.response.send_message(
                        f"{HeraldEmojis.ERROR} **{self.character_name}** already has the **{edge_name}** edge!",
                        ephemeral=True
                    )
                    return

                # Add the edge
                await conn.execute(
                    "INSERT INTO edges (user_id, character_name, edge_name, description) VALUES ($1, $2, $3, $4)",
                    self.user_id, self.character_name, edge_name, description
                )

            # Invalidate cache to ensure /sheet shows updated value
            from core.character_utils import invalidate_character_cache
            invalidate_character_cache(self.user_id, self.character_name)

            embed = discord.Embed(
                title=f"{HeraldEmojis.EDGE} Edge Added",
                description=f"**{self.character_name}** gained the **{edge_name}** edge",
                color=0xFFA500  # Orange
            )

            embed.add_field(
                name="Description",
                value=description,
                inline=False
            )

            embed.set_footer(text="View all edges with /edge action:View")

            # Disable all buttons
            for item in self.children:
                item.disabled = True

            await interaction.response.edit_message(embed=embed, view=self)
            self.selected_edge = edge_name
            self.stop()

        except Exception as e:
            logger.error(f"Error adding edge: {e}")
            await interaction.response.send_message(
                f"{HeraldEmojis.ERROR} Error adding edge",
                ephemeral=True
            )


class CharacterGameplay(commands.Cog):
    """Character Gameplay - H5E mechanics and combat systems"""
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger('Herald.Character.Gameplay')

    @app_commands.command(name="damage", description="Apply health or willpower damage to your character")
    @app_commands.describe(
        track="Damage track (health or willpower)",
        amount="Amount of damage to apply",
        damage_type="Type of damage (superficial or aggravated)"
    )
    @app_commands.choices(
        track=[
            app_commands.Choice(name="Health", value="health"),
            app_commands.Choice(name="Willpower", value="willpower")
        ],
        damage_type=[
            app_commands.Choice(name="Superficial", value="superficial"),
            app_commands.Choice(name="Aggravated", value="aggravated")
        ]
    )
    async def apply_damage(
        self,
        interaction: discord.Interaction,
        track: str,
        amount: int,
        damage_type: str = "superficial"
    ):
        """Apply damage to a character's health or willpower"""
        user_id = str(interaction.user.id)

        if amount < 1:
            await interaction.response.send_message(
                f"{HeraldEmojis.ERROR} Damage amount must be positive",
                ephemeral=True
            )
            return

        try:
            # Get active character
            active_char_name = await get_active_character(user_id)
            if not active_char_name:
                await interaction.response.send_message(
                    f"{HeraldEmojis.ERROR} No active character set. Use `/character` to set your active character.",
                    ephemeral=True
                )
                return

            char = await find_character(user_id, active_char_name)
            if not char:
                await interaction.response.send_message(
                    f"{HeraldEmojis.ERROR} Could not find your active character.",
                    ephemeral=True
                )
                return

            # Determine fields to update
            if track == "health":
                max_track = char['health']
                sup_field = 'health_sup'
                agg_field = 'health_agg'
                current_sup = char['health_sup']
                current_agg = char['health_agg']
                track_emoji = HeraldEmojis.HEALTH_FULL
            else:  # willpower
                max_track = char['willpower']
                sup_field = 'willpower_sup'
                agg_field = 'willpower_agg'
                current_sup = char['willpower_sup']
                current_agg = char['willpower_agg']
                track_emoji = HeraldEmojis.WILLPOWER_FULL

            # Calculate new damage totals
            if damage_type == "superficial":
                new_sup = min(current_sup + amount, max_track - current_agg)
                new_agg = current_agg
            else:  # aggravated
                # Aggravated damage converts superficial to aggravated
                new_agg = min(current_agg + amount, max_track)
                new_sup = max(0, current_sup - amount)  # Reduced by converted damage

            # Update database using actual character name with async
            async with get_async_db() as conn:
                await conn.execute(
                    f"UPDATE characters SET {sup_field} = $1, {agg_field} = $2 WHERE user_id = $3 AND name = $4",
                    new_sup, new_agg, user_id, char['name']
                )

            # Invalidate cache to ensure /sheet shows updated value
            from core.character_utils import invalidate_character_cache
            invalidate_character_cache(user_id, char['name'])

            # Create response with proper display functions
            remaining = max_track - new_sup - new_agg
            if track == "health":
                damage_bar_display = create_health_bar(max_track, new_sup, new_agg, 8)
            else:
                damage_bar_display = create_willpower_bar(max_track, new_sup, new_agg, 10)

            embed = discord.Embed(
                title=f"{HeraldEmojis.CRITICAL} Damage Applied",
                description=f"**{char['name']}** takes {amount} {damage_type} {track} damage",
                color=0x8B0000
            )
            
            embed.add_field(
                name=f"{track_emoji} {track.title()}",
                value=f"{damage_bar_display}\n`{remaining}/{max_track} remaining`",
                inline=False
            )

            if remaining == 0:
                if track == "health":
                    embed.add_field(
                        name=f"{HeraldEmojis.WARNING} Incapacitated!",
                        value="Character is unconscious and dying",
                        inline=False
                    )
                else:
                    embed.add_field(
                        name=f"{HeraldEmojis.WARNING} Willpower Broken!",
                        value="Character is emotionally broken",
                        inline=False
                    )

            await interaction.response.send_message(embed=embed)
            logger.info(f"Applied {amount} {damage_type} {track} damage to {char['name']} for user {user_id}")

        except Exception as e:
            logger.error(f"Error applying damage: {e}")
            await interaction.response.send_message(
                f"{HeraldEmojis.ERROR} Error applying damage: {str(e)}", 
                ephemeral=True
            )

    @app_commands.command(name="heal", description="Heal damage from your character")
    @app_commands.describe(
        track="Track to heal (health or willpower)",
        heal_type="Type of damage to heal",
        amount="Amount to heal (required for superficial/aggravated)"
    )
    @app_commands.choices(
        track=[
            app_commands.Choice(name="Health", value="health"),
            app_commands.Choice(name="Willpower", value="willpower")
        ],
        heal_type=[
            app_commands.Choice(name="All Damage", value="all"),
            app_commands.Choice(name="Superficial", value="superficial"),
            app_commands.Choice(name="Aggravated", value="aggravated")
        ]
    )
    async def heal_damage(
        self,
        interaction: discord.Interaction,
        track: str,
        heal_type: str,
        amount: int = None
    ):
        """Heal damage from a character"""
        user_id = str(interaction.user.id)

        # Validate amount for non-"all" healing
        if heal_type != "all" and (amount is None or amount < 1):
            await interaction.response.send_message(
                f"{HeraldEmojis.ERROR} Please specify a positive amount to heal",
                ephemeral=True
            )
            return

        try:
            # Get active character
            active_char_name = await get_active_character(user_id)
            if not active_char_name:
                await interaction.response.send_message(
                    f"{HeraldEmojis.ERROR} No active character set. Use `/character` to set your active character.",
                    ephemeral=True
                )
                return

            char = await find_character(user_id, active_char_name)
            if not char:
                await interaction.response.send_message(
                    f"{HeraldEmojis.ERROR} Could not find your active character.",
                    ephemeral=True
                )
                return

            # Determine fields
            if track == "health":
                max_track = char['health']
                sup_field = 'health_sup'
                agg_field = 'health_agg'
                current_sup = char['health_sup']
                current_agg = char['health_agg']
                track_emoji = HeraldEmojis.HEALTH_FULL
            else:  # willpower
                max_track = char['willpower']
                sup_field = 'willpower_sup'
                agg_field = 'willpower_agg'  
                current_sup = char['willpower_sup']
                current_agg = char['willpower_agg']
                track_emoji = HeraldEmojis.WILLPOWER_FULL

            # Calculate healing
            if heal_type == "all":
                new_sup = 0
                new_agg = 0
                healed_amount = current_sup + current_agg
            elif heal_type == "superficial":
                new_sup = max(0, current_sup - amount)
                new_agg = current_agg
                healed_amount = current_sup - new_sup
            else:  # aggravated
                new_agg = max(0, current_agg - amount)
                new_sup = current_sup
                healed_amount = current_agg - new_agg

            # Update database using actual character name with async
            async with get_async_db() as conn:
                await conn.execute(
                    f"UPDATE characters SET {sup_field} = $1, {agg_field} = $2 WHERE user_id = $3 AND name = $4",
                    new_sup, new_agg, user_id, char['name']
                )

            # Invalidate cache to ensure /sheet shows updated value
            from core.character_utils import invalidate_character_cache
            invalidate_character_cache(user_id, char['name'])

            # Create response with proper display functions
            remaining = max_track - new_sup - new_agg
            if track == "health":
                damage_bar_display = create_health_bar(max_track, new_sup, new_agg, 8)
            else:
                damage_bar_display = create_willpower_bar(max_track, new_sup, new_agg, 10)

            heal_text = f"all damage" if heal_type == "all" else f"{healed_amount} {heal_type} damage"
            
            embed = discord.Embed(
                title=f"{HeraldEmojis.NEW} Healing Applied",
                description=f"**{char['name']}** heals {heal_text}",
                color=0x228B22
            )
            
            embed.add_field(
                name=f"{track_emoji} {track.title()}",
                value=f"{damage_bar_display}\n`{remaining}/{max_track} remaining`",
                inline=False
            )

            await interaction.response.send_message(embed=embed)
            logger.info(f"Healed {heal_text} from {char['name']}'s {track} for user {user_id}")

        except Exception as e:
            logger.error(f"Error healing damage: {e}")
            await interaction.response.send_message(
                f"{HeraldEmojis.ERROR} Error healing damage: {str(e)}",
                ephemeral=True
            )

    # NOTE: The /edge command has been removed. Edge is now a list of abilities (edges table),
    # not a dice pool modifier. Edge abilities are displayed on the character sheet.
    # To add Edge abilities, use the edges table directly or create an /add_edge command.

    @app_commands.command(name="desperation", description="View or modify your character's Desperation level")
    @app_commands.describe(
        action="What to do with Desperation",
        amount="Amount to add/subtract/set (optional for 'view')"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="View", value="view"),
        app_commands.Choice(name="Set", value="set"),
        app_commands.Choice(name="Add", value="add"),
        app_commands.Choice(name="Subtract", value="subtract")
    ])
    async def desperation(self, interaction: discord.Interaction, action: str, amount: int = None):
        """Manage character Desperation levels (0-10)"""

        user_id = str(interaction.user.id)

        try:
            # Get active character
            active_char_name = await get_active_character(user_id)
            if not active_char_name:
                await interaction.response.send_message(
                    f"{HeraldEmojis.ERROR} No active character set. Use `/character` to set your active character.",
                    ephemeral=True
                )
                return

            char = await find_character(user_id, active_char_name)
            if not char:
                await interaction.response.send_message(
                    f"{HeraldEmojis.ERROR} Could not find your active character.",
                    ephemeral=True
                )
                return
            
            current_desperation = safe_get_character_field(char, 'desperation', 0)
            
            # Handle different actions
            if action == "view":
                # Create desperation bar
                desperation_bar = create_desperation_bar(current_desperation)
                
                embed = discord.Embed(
                    title=f"{HeraldEmojis.DESPERATION} {char['name']}'s Desperation",
                    description=f"**Current Level:** {current_desperation}/10\n{desperation_bar}",
                    color=0x8B0000 if current_desperation >= 7 else 0xFF4500 if current_desperation >= 4 else 0x4169E1
                )
                
                # Add Desperation effects info
                if current_desperation >= 7:
                    embed.add_field(
                        name=f"{HeraldEmojis.WARNING} High Desperation Effects", 
                        value="• Rolling Desperation dice on failed rolls\n• Risk of permanent consequences\n• Increased danger to self and others", 
                        inline=False
                    )
                elif current_desperation >= 4:
                    embed.add_field(
                        name=f"{HeraldEmojis.INFO} Moderate Desperation", 
                        value="Your Hunter is feeling the weight of the hunt. Be careful not to let it consume you.", 
                        inline=False
                    )
                else:
                    embed.add_field(
                        name=f"{HeraldEmojis.SUCCESS} Low Desperation", 
                        value="Your Hunter is maintaining their humanity and purpose.", 
                        inline=False
                    )
                
                await interaction.response.send_message(embed=embed)
                return
            
            # For set/add/subtract, amount is required
            if amount is None:
                await interaction.response.send_message(
                    f"{HeraldEmojis.ERROR} Please specify an amount for {action}", 
                    ephemeral=True
                )
                return
            
            # Calculate new desperation value
            if action == "set":
                new_desperation = max(0, min(amount, 10))
            elif action == "add":
                new_desperation = max(0, min(current_desperation + amount, 10))
            else:  # subtract
                new_desperation = max(0, current_desperation - amount)
            
            # Update database with async
            async with get_async_db() as conn:
                await conn.execute(
                    "UPDATE characters SET desperation = $1 WHERE user_id = $2 AND name = $3",
                    new_desperation, user_id, char['name']
                )

            # Invalidate cache to ensure /sheet shows updated value
            from core.character_utils import invalidate_character_cache
            invalidate_character_cache(user_id, char['name'])

            # Create response
            desperation_bar = create_desperation_bar(new_desperation)

            embed = discord.Embed(
                title=f"{HeraldEmojis.DESPERATION} Desperation Updated",
                description=f"{HeraldMessages.PATTERN_LOGGED}: Risk increases with reward\n\n{desperation_bar}",
                color=0x8B0000 if new_desperation >= 7 else 0xFF4500 if new_desperation >= 4 else 0x4169E1
            )

            # Add contextual warnings
            if new_desperation >= 7 and current_desperation < 7:
                embed.add_field(
                    name=f"{HeraldMessages.PATTERN_WARNING}",
                    value="Your Hunter has reached a critical level of Desperation. Failed rolls now trigger Desperation dice!",
                    inline=False
                )
            elif new_desperation == 10:
                embed.add_field(
                    name=f"{HeraldMessages.PATTERN_WARNING}: Critical threshold",
                    value="Your Hunter is at the breaking point. One more failed roll could mean disaster!",
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Error in desperation command: {e}")
            await interaction.response.send_message(
                f"{HeraldEmojis.ERROR} An error occurred while managing Desperation", 
                ephemeral=True
            )

    @app_commands.command(name="creed", description="View or set your character's Hunter Creed")
    @app_commands.describe(
        action="View current creed or set a new one"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="View", value="view"),
        app_commands.Choice(name="Set", value="set")
    ])
    async def creed(self, interaction: discord.Interaction, action: str = "view"):
        """Manage character Creed (Hunter type/philosophy)"""

        user_id = str(interaction.user.id)

        try:
            # Get active character
            active_char_name = await get_active_character(user_id)
            if not active_char_name:
                await interaction.response.send_message(
                    f"{HeraldEmojis.ERROR} No active character set. Use `/character` to set your active character.",
                    ephemeral=True
                )
                return

            char = await find_character(user_id, active_char_name)
            if not char:
                await interaction.response.send_message(
                    f"{HeraldEmojis.ERROR} Could not find your active character.",
                    ephemeral=True
                )
                return

            if action == "view":
                # Show current creed
                current_creed = char['creed']

                embed = discord.Embed(
                    title=f"{HeraldEmojis.CREED} {char['name']}'s Creed",
                    color=0x8B0000
                )

                if current_creed:
                    embed.description = f"**Current Creed:** {current_creed}"

                    # Add creed field descriptions
                    creed_fields = {
                        "Entrepreneurial": "Building, inventing, repairing",
                        "Faithful": "Direct conflict with the supernatural",
                        "Inquisitive": "Gaining information",
                        "Martial": "Physical conflict",
                        "Underground": "Stealth and subterfuge"
                    }

                    if current_creed in creed_fields:
                        embed.add_field(
                            name="Creed Field",
                            value=creed_fields[current_creed],
                            inline=False
                        )
                else:
                    embed.description = "*No Creed set yet*"
                    embed.add_field(
                        name="Hunter: The Reckoning 5E Creeds",
                        value="• **Entrepreneurial** - Building, inventing, repairing\n• **Faithful** - Direct conflict with the supernatural\n• **Inquisitive** - Gaining information\n• **Martial** - Physical conflict\n• **Underground** - Stealth and subterfuge",
                        inline=False
                    )

                embed.set_footer(text="Use /creed action:Set to change your creed")
                await interaction.response.send_message(embed=embed)

            else:  # action == "set"
                # Show interactive button selection
                embed = discord.Embed(
                    title=f"{HeraldEmojis.CREED} Select Your Creed",
                    description=f"Choose the Creed for **{char['name']}**\n\nYour Creed represents your Hunter's philosophy and approach to the hunt.",
                    color=0x8B0000
                )

                embed.add_field(
                    name="🔨 Entrepreneurial",
                    value="Building, inventing, repairing",
                    inline=True
                )
                embed.add_field(
                    name="✝️ Faithful",
                    value="Direct conflict with the supernatural",
                    inline=True
                )
                embed.add_field(
                    name="🔍 Inquisitive",
                    value="Gaining information",
                    inline=True
                )
                embed.add_field(
                    name="⚔️ Martial",
                    value="Physical conflict",
                    inline=True
                )
                embed.add_field(
                    name="🎭 Underground",
                    value="Stealth and subterfuge",
                    inline=True
                )

                view = CreedSelectionView(user_id, char['name'])
                await interaction.response.send_message(embed=embed, view=view)

        except Exception as e:
            self.logger.error(f"Error in creed command: {e}")
            await interaction.response.send_message(
                f"{HeraldEmojis.ERROR} Error managing creed",
                ephemeral=True
            )

    @app_commands.command(name="edge", description="Manage your character's Hunter Edges")
    @app_commands.describe(
        action="What to do with edges",
        edge_name="Edge name (for remove action)"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="View All", value="view"),
        app_commands.Choice(name="Add", value="add"),
        app_commands.Choice(name="Remove", value="remove")
    ])
    async def edge(self, interaction: discord.Interaction, action: str, edge_name: str = None):
        """Manage character Edges (Hunter supernatural advantages)"""

        user_id = str(interaction.user.id)

        try:
            # Get active character
            active_char_name = await get_active_character(user_id)
            if not active_char_name:
                await interaction.response.send_message(
                    f"{HeraldEmojis.ERROR} No active character set. Use `/character` to set your active character.",
                    ephemeral=True
                )
                return

            char = await find_character(user_id, active_char_name)
            if not char:
                await interaction.response.send_message(
                    f"{HeraldEmojis.ERROR} Could not find your active character.",
                    ephemeral=True
                )
                return

            if action == "view":
                # Show all current edges
                from core.character_utils import get_character_edges
                edges = await get_character_edges(user_id, char['name'])

                embed = discord.Embed(
                    title=f"{HeraldEmojis.EDGE} {char['name']}'s Edges",
                    color=0xFFA500  # Orange
                )

                if edges:
                    # Group by category
                    assets = []
                    aptitudes = []
                    endowments = []

                    asset_names = ["Arsenal", "Fleet", "Ordnance", "Library", "Experimental Medicine"]
                    aptitude_names = ["Improvised Gear", "Global Access", "Drone Jockey", "Beast Whisperer", "Turncoat"]

                    for edge in edges:
                        edge_name = edge.get('edge_name', 'Unknown')
                        edge_desc = edge.get('description', '')

                        if edge_name in asset_names:
                            assets.append(f"• **{edge_name}**")
                        elif edge_name in aptitude_names:
                            aptitudes.append(f"• **{edge_name}**")
                        else:
                            endowments.append(f"• **{edge_name}**")

                    if assets:
                        embed.add_field(
                            name="📦 Assets",
                            value='\n'.join(assets),
                            inline=False
                        )
                    if aptitudes:
                        embed.add_field(
                            name="🧠 Aptitudes",
                            value='\n'.join(aptitudes),
                            inline=False
                        )
                    if endowments:
                        embed.add_field(
                            name="✨ Endowments",
                            value='\n'.join(endowments),
                            inline=False
                        )
                else:
                    embed.description = "*No Edges yet*"
                    embed.add_field(
                        name="What are Edges?",
                        value="Edges are supernatural advantages that put Hunters above ordinary people. Use `/edge action:Add` to gain an Edge!",
                        inline=False
                    )

                embed.set_footer(text="Use /edge action:Add to gain new edges • /edge action:Remove to remove an edge")
                await interaction.response.send_message(embed=embed)

            elif action == "add":
                # Show interactive button selection
                embed = discord.Embed(
                    title=f"{HeraldEmojis.EDGE} Select an Edge",
                    description=f"Choose an Edge for **{char['name']}**\n\nEdges are supernatural advantages divided into Assets, Aptitudes, and Endowments.",
                    color=0xFFA500  # Orange
                )

                embed.add_field(
                    name="📦 Assets",
                    value="Access to resources, tools, or contacts that ordinary citizens don't have",
                    inline=False
                )
                embed.add_field(
                    name="🧠 Aptitudes",
                    value="Supernatural abilities that defy normal human limits",
                    inline=False
                )
                embed.add_field(
                    name="✨ Endowments",
                    value="Supernatural objects or abilities beyond what is natural",
                    inline=False
                )

                view = EdgeSelectionView(user_id, char['name'])
                await interaction.response.send_message(embed=embed, view=view)

            elif action == "remove":
                # Remove edge
                if not edge_name:
                    await interaction.response.send_message(
                        f"{HeraldEmojis.ERROR} Please specify the edge name to remove",
                        ephemeral=True
                    )
                    return

                async with get_async_db() as conn:
                    result = await conn.execute(
                        "DELETE FROM edges WHERE user_id = $1 AND character_name = $2 AND edge_name = $3",
                        user_id, char['name'], edge_name
                    )

                    # Invalidate cache to ensure /sheet shows updated value
                    from core.character_utils import invalidate_character_cache
                    invalidate_character_cache(user_id, char['name'])

                    # Check if anything was deleted
                    if result == "DELETE 0":
                        await interaction.response.send_message(
                            f"{HeraldEmojis.ERROR} Edge **{edge_name}** not found",
                            ephemeral=True
                        )
                        return

                    embed = discord.Embed(
                        title=f"🗑️ Edge Removed",
                        description=f"**{char['name']}** lost the **{edge_name}** edge",
                        color=0xFF4500
                    )

                    await interaction.response.send_message(embed=embed)
                    logger.info(f"Removed edge '{edge_name}' from {char['name']} (user {user_id})")

        except Exception as e:
            self.logger.error(f"Error in edge command: {e}")
            await interaction.response.send_message(
                f"{HeraldEmojis.ERROR} Error managing edges",
                ephemeral=True
            )

    @app_commands.command(name="perks", description="Manage your character's Edge Perks")
    @app_commands.describe(
        action="What to do with perks",
        edge_name="Edge to view perks for (for add action)",
        perk_name="Perk name (for add/remove actions)"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="View All", value="view"),
        app_commands.Choice(name="Add", value="add"),
        app_commands.Choice(name="Remove", value="remove")
    ])
    async def perks(self, interaction: discord.Interaction, action: str, edge_name: str = None, perk_name: str = None):
        """Manage character Perks (Hunter advantages from Edges)"""

        user_id = str(interaction.user.id)

        try:
            # Get active character
            active_char_name = await get_active_character(user_id)
            if not active_char_name:
                await interaction.response.send_message(
                    f"{HeraldEmojis.ERROR} No active character set. Use `/character` to set your active character.",
                    ephemeral=True
                )
                return

            char = await find_character(user_id, active_char_name)
            if not char:
                await interaction.response.send_message(
                    f"{HeraldEmojis.ERROR} Could not find your active character.",
                    ephemeral=True
                )
                return

            # Get character's edges
            from core.character_utils import get_character_edges, get_character_perks
            edges = await get_character_edges(user_id, char['name'])

            if not edges and action != "view":
                await interaction.response.send_message(
                    f"{HeraldEmojis.ERROR} **{char['name']}** has no Edges yet! Use `/edge action:Add` to gain an Edge before adding Perks.",
                    ephemeral=True
                )
                return

            if action == "view":
                # Show all current perks grouped by edge
                perks = await get_character_perks(user_id, char['name'])

                embed = discord.Embed(
                    title=f"🎭 {char['name']}'s Perks",
                    color=0xFFA500  # Orange
                )

                if perks:
                    # Group perks by edge
                    from collections import defaultdict
                    perks_by_edge = defaultdict(list)

                    for perk in perks:
                        edge = perk.get('edge_name', 'Unknown')
                        perk_nm = perk.get('perk_name', 'Unknown')
                        perks_by_edge[edge].append(perk_nm)

                    # Display perks grouped by edge
                    for edge, perk_list in sorted(perks_by_edge.items()):
                        perk_display = '\n'.join([f"• {p}" for p in perk_list])
                        embed.add_field(
                            name=f"⚡ {edge}",
                            value=perk_display,
                            inline=False
                        )
                else:
                    embed.description = "*No Perks yet*"

                    if edges:
                        edge_list = ", ".join([e['edge_name'] for e in edges])
                        embed.add_field(
                            name="Your Edges",
                            value=f"You have the following Edges: **{edge_list}**\n\nUse `/perks action:Add` to gain Perks for your Edges!",
                            inline=False
                        )
                    else:
                        embed.add_field(
                            name="What are Perks?",
                            value="Perks are special abilities tied to your Edges. First gain an Edge with `/edge action:Add`, then gain Perks for that Edge!",
                            inline=False
                        )

                embed.set_footer(text="Use /perks action:Add to gain new perks • /perks action:Remove to remove a perk")
                await interaction.response.send_message(embed=embed)

            elif action == "add":
                # Show available perks for character's edges
                if not edge_name:
                    # Show edges to choose from
                    embed = discord.Embed(
                        title=f"🎭 Select an Edge",
                        description=f"Choose which Edge you want to add a Perk for:\n\n**Your Edges:**",
                        color=0xFFA500
                    )

                    edge_list = []
                    for edge in edges:
                        edge_list.append(f"⚡ **{edge['edge_name']}**")

                    embed.add_field(
                        name="\u200b",
                        value="\n".join(edge_list),
                        inline=False
                    )

                    embed.set_footer(text="Use /perks action:Add edge_name:\"Edge Name\" perk_name:\"Perk Name\" to add a perk")
                    await interaction.response.send_message(embed=embed)
                    return

                # Verify the character has this edge
                edge_names = [e['edge_name'] for e in edges]
                if edge_name not in edge_names:
                    await interaction.response.send_message(
                        f"{HeraldEmojis.ERROR} **{char['name']}** does not have the **{edge_name}** Edge!",
                        ephemeral=True
                    )
                    return

                if not perk_name:
                    # Show available perks for this edge
                    from data.perks import get_perks_for_edge
                    available_perks = get_perks_for_edge(edge_name)

                    if not available_perks:
                        await interaction.response.send_message(
                            f"{HeraldEmojis.ERROR} No perks found for **{edge_name}**",
                            ephemeral=True
                        )
                        return

                    embed = discord.Embed(
                        title=f"🎭 Available Perks for {edge_name}",
                        description=f"Choose a Perk to add:",
                        color=0xFFA500
                    )

                    # Get character's current perks for this edge
                    current_perks = await get_character_perks(user_id, char['name'])
                    current_perk_names = [p['perk_name'] for p in current_perks if p['edge_name'] == edge_name]

                    perk_list = []
                    for perk_nm, perk_desc in available_perks.items():
                        if perk_nm in current_perk_names:
                            perk_list.append(f"✅ **{perk_nm}** (already have)")
                        else:
                            perk_list.append(f"• **{perk_nm}**")

                    # Discord has a 1024 character limit per field, so we might need to split
                    perk_display = "\n".join(perk_list)
                    if len(perk_display) > 1024:
                        # Split into multiple fields
                        chunks = []
                        current_chunk = []
                        current_length = 0

                        for perk_line in perk_list:
                            if current_length + len(perk_line) + 1 > 1024:
                                chunks.append("\n".join(current_chunk))
                                current_chunk = [perk_line]
                                current_length = len(perk_line)
                            else:
                                current_chunk.append(perk_line)
                                current_length += len(perk_line) + 1

                        if current_chunk:
                            chunks.append("\n".join(current_chunk))

                        for i, chunk in enumerate(chunks):
                            embed.add_field(
                                name=f"Perks (Part {i+1})" if i > 0 else "Perks",
                                value=chunk,
                                inline=False
                            )
                    else:
                        embed.add_field(
                            name="Perks",
                            value=perk_display,
                            inline=False
                        )

                    embed.set_footer(text=f"Use /perks action:Add edge_name:\"{edge_name}\" perk_name:\"Perk Name\" to add a perk")
                    await interaction.response.send_message(embed=embed)
                    return

                # Add the perk
                from data.perks import get_perk_description
                perk_description = get_perk_description(edge_name, perk_name)

                if not perk_description:
                    await interaction.response.send_message(
                        f"{HeraldEmojis.ERROR} **{perk_name}** is not a valid perk for **{edge_name}**",
                        ephemeral=True
                    )
                    return

                async with get_async_db() as conn:
                    # Check if perk already exists
                    existing = await conn.fetchrow(
                        "SELECT perk_name FROM perks WHERE user_id = $1 AND character_name = $2 AND perk_name = $3",
                        user_id, char['name'], perk_name
                    )

                    if existing:
                        await interaction.response.send_message(
                            f"{HeraldEmojis.ERROR} **{char['name']}** already has the **{perk_name}** perk!",
                            ephemeral=True
                        )
                        return

                    # Add the perk
                    await conn.execute(
                        "INSERT INTO perks (user_id, character_name, edge_name, perk_name, description) VALUES ($1, $2, $3, $4, $5)",
                        user_id, char['name'], edge_name, perk_name, perk_description
                    )

                # Invalidate cache to ensure /sheet shows updated value
                from core.character_utils import invalidate_character_cache
                invalidate_character_cache(user_id, char['name'])

                embed = discord.Embed(
                    title=f"🎭 Perk Added",
                    description=f"**{char['name']}** gained the **{perk_name}** perk",
                    color=0xFFA500
                )

                embed.add_field(
                    name=f"⚡ {edge_name}",
                    value=f"**{perk_name}**\n*{perk_description}*",
                    inline=False
                )

                embed.set_footer(text="View all perks with /perks action:View")

                await interaction.response.send_message(embed=embed)
                logger.info(f"Added perk '{perk_name}' ({edge_name}) to {char['name']} (user {user_id})")

            elif action == "remove":
                # Remove perk
                if not perk_name:
                    await interaction.response.send_message(
                        f"{HeraldEmojis.ERROR} Please specify the perk name to remove",
                        ephemeral=True
                    )
                    return

                async with get_async_db() as conn:
                    result = await conn.execute(
                        "DELETE FROM perks WHERE user_id = $1 AND character_name = $2 AND perk_name = $3",
                        user_id, char['name'], perk_name
                    )

                    # Invalidate cache to ensure /sheet shows updated value
                    from core.character_utils import invalidate_character_cache
                    invalidate_character_cache(user_id, char['name'])

                    # Check if anything was deleted
                    if result == "DELETE 0":
                        await interaction.response.send_message(
                            f"{HeraldEmojis.ERROR} Perk **{perk_name}** not found",
                            ephemeral=True
                        )
                        return

                    embed = discord.Embed(
                        title=f"🗑️ Perk Removed",
                        description=f"**{char['name']}** lost the **{perk_name}** perk",
                        color=0xFF4500
                    )

                    await interaction.response.send_message(embed=embed)
                    logger.info(f"Removed perk '{perk_name}' from {char['name']} (user {user_id})")

        except Exception as e:
            self.logger.error(f"Error in perks command: {e}")
            await interaction.response.send_message(
                f"{HeraldEmojis.ERROR} Error managing perks",
                ephemeral=True
            )

    @app_commands.command(name="ambition", description="View or set your character's Ambition")
    @app_commands.describe(
        ambition="Long-term goal (leave empty to view current ambition)"
    )
    async def ambition(self, interaction: discord.Interaction, ambition: str = None):
        """Manage character Ambition (long-term goal that recovers aggravated willpower damage)"""

        user_id = str(interaction.user.id)

        if ambition and len(ambition) > 200:
            await interaction.response.send_message(
                f"{HeraldEmojis.ERROR} Ambition must be 200 characters or less", 
                ephemeral=True
            )
            return

        try:
            # Get active character
            active_char_name = await get_active_character(user_id)
            if not active_char_name:
                await interaction.response.send_message(
                    f"{HeraldEmojis.ERROR} No active character set. Use `/character` to set your active character.",
                    ephemeral=True
                )
                return

            char = await find_character(user_id, active_char_name)
            if not char:
                await interaction.response.send_message(
                    f"{HeraldEmojis.ERROR} Could not find your active character.",
                    ephemeral=True
                )
                return

            current_ambition = char['ambition']
            
            # If no ambition provided, show current ambition
            if ambition is None:
                embed = discord.Embed(
                    title=f"{HeraldEmojis.AMBITION} {char['name']}'s Ambition",
                    color=0x4169E1
                )
                
                if current_ambition:
                    embed.description = f"**Current Ambition:** {current_ambition}"
                    embed.add_field(
                        name=f"{HeraldEmojis.INFO} About Ambitions", 
                        value="Ambitions are long-term goals that drive your character forward. When you make **significant progress** toward your Ambition during a story, you **immediately recover one point of Aggravated Willpower damage**.", 
                        inline=False
                    )
                else:
                    embed.description = "*No Ambition set yet*"
                    embed.add_field(
                        name="Set Your Ambition",
                        value="Use `/ambition ambition:\"Your long-term goal\"` to set an ambitious goal for your Hunter.\n\n**Examples:**\n• Destroy the vampire nest in the city\n• Find out what happened to my family\n• Prove the supernatural exists to the world",
                        inline=False
                    )
                
                await interaction.response.send_message(embed=embed)
                return
            
            # Set the ambition with async
            async with get_async_db() as conn:
                await conn.execute(
                    "UPDATE characters SET ambition = $1 WHERE user_id = $2 AND name = $3",
                    ambition, user_id, char['name']
                )

            # Invalidate cache to ensure /sheet shows updated value
            from core.character_utils import invalidate_character_cache
            invalidate_character_cache(user_id, char['name'])

            embed = discord.Embed(
                title=f"{HeraldEmojis.AMBITION} Ambition Set",
                color=0x4169E1
            )
            
            embed.description = f"**Ambition Set:** {ambition}"
            embed.add_field(
                name=f"{HeraldEmojis.NEW} Goal Established", 
                value="Your character now has a driving long-term goal! Work towards this during sessions to recover Aggravated Willpower damage.", 
                inline=False
            )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Error in ambition command: {e}")
            await interaction.response.send_message(
                f"{HeraldEmojis.ERROR} An error occurred while managing Ambition", 
                ephemeral=True
            )

    @app_commands.command(name="desire", description="View or set your character's Desire")
    @app_commands.describe(
        desire="Short-term goal (leave empty to view current desire)"
    )
    async def desire(self, interaction: discord.Interaction, desire: str = None):
        """Manage character Desire (short-term goal that recovers superficial willpower damage)"""
        
        user_id = str(interaction.user.id)
        
        if desire and len(desire) > 200:
            await interaction.response.send_message(
                f"{HeraldEmojis.ERROR} Desire must be 200 characters or less", 
                ephemeral=True
            )
            return

        try:
            # Get active character
            active_char_name = await get_active_character(user_id)
            if not active_char_name:
                await interaction.response.send_message(
                    f"{HeraldEmojis.ERROR} No active character set. Use `/character` to set your active character.",
                    ephemeral=True
                )
                return

            char = await find_character(user_id, active_char_name)
            if not char:
                await interaction.response.send_message(
                    f"{HeraldEmojis.ERROR} Could not find your active character.",
                    ephemeral=True
                )
                return

            current_desire = char['desire']
            
            # If no desire provided, show current desire
            if desire is None:
                embed = discord.Embed(
                    title=f"{HeraldEmojis.DESIRE} {char['name']}'s Desire",
                    color=0x4169E1
                )
                
                if current_desire:
                    embed.description = f"**Current Desire:** {current_desire}"
                    embed.add_field(
                        name=f"{HeraldEmojis.INFO} About Desires", 
                        value="Desires are short-term goals or momentary wants. When you accomplish your Desire during a session, you **immediately recover one point of spent or damaged Superficial Willpower**. You can change your Desire each session.", 
                        inline=False
                    )
                else:
                    embed.description = "*No Desire set yet*"
                    embed.add_field(
                        name="Set Your Desire",
                        value="Use `/desire desire:\"Your short-term goal\"` to set a desire for this session.\n\n**Examples:**\n• Find evidence of the creature's lair\n• Protect an innocent from harm\n• Get revenge on a specific enemy",
                        inline=False
                    )
                
                await interaction.response.send_message(embed=embed)
                return
            
            # Set the desire with async
            async with get_async_db() as conn:
                await conn.execute(
                    "UPDATE characters SET desire = $1 WHERE user_id = $2 AND name = $3",
                    desire, user_id, char['name']
                )

            # Invalidate cache to ensure /sheet shows updated value
            from core.character_utils import invalidate_character_cache
            invalidate_character_cache(user_id, char['name'])

            embed = discord.Embed(
                title=f"{HeraldEmojis.DESIRE} Desire Set",
                color=0x4169E1
            )
            
            embed.description = f"**Desire Set:** {desire}"
            embed.add_field(
                name=f"{HeraldEmojis.NEW} Goal Established", 
                value="Your character now has a short-term goal! Accomplish this during the session to recover Superficial Willpower damage.", 
                inline=False
            )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Error in desire command: {e}")
            await interaction.response.send_message(
                f"{HeraldEmojis.ERROR} An error occurred while managing Desire", 
                ephemeral=True
            )

    @app_commands.command(name="drive", description="View or set your character's Drive and Redemption")
    @app_commands.describe(
        action="View current drive or set a new one"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="View", value="view"),
        app_commands.Choice(name="Set", value="set")
    ])
    async def drive(self, interaction: discord.Interaction, action: str = "view"):
        """Manage character Drive (reason for hunting) and Redemption (healing from Despair)"""

        user_id = str(interaction.user.id)

        try:
            # Get active character
            active_char_name = await get_active_character(user_id)
            if not active_char_name:
                await interaction.response.send_message(
                    f"{HeraldEmojis.ERROR} No active character set. Use `/character` to set your active character.",
                    ephemeral=True
                )
                return

            char = await find_character(user_id, active_char_name)
            if not char:
                await interaction.response.send_message(
                    f"{HeraldEmojis.ERROR} Could not find your active character.",
                    ephemeral=True
                )
                return

            if action == "view":
                # Show current drive and redemption
                current_drive = char['drive']
                current_redemption = char['redemption']

                embed = discord.Embed(
                    title=f"{HeraldEmojis.DRIVE} {char['name']}'s Drive",
                    color=0x8B0000
                )

                if current_drive:
                    embed.description = f"**Current Drive:** {current_drive}"
                    if current_redemption:
                        embed.add_field(
                            name=f"{HeraldEmojis.REDEMPTION} Redemption",
                            value=current_redemption,
                            inline=False
                        )
                else:
                    embed.description = "*No Drive set yet*"
                    embed.add_field(
                        name="Hunter: The Reckoning 5E Drives",
                        value="• **Curiosity** - Uncover new information\n• **Vengeance** - Hurt your quarry\n• **Oath** - Uphold or fulfill your oath\n• **Greed** - Acquire resources from enemies\n• **Pride** - Best your quarry in contest\n• **Envy** - Ally with your quarry\n• **Atonement** - Protect someone from your quarry",
                        inline=False
                    )

                embed.set_footer(text="Use /drive action:Set to change your drive")
                await interaction.response.send_message(embed=embed)

            else:  # action == "set"
                # Show interactive button selection
                embed = discord.Embed(
                    title=f"{HeraldEmojis.DRIVE} Select Your Drive",
                    description=f"Choose the Drive for **{char['name']}**\n\nYour Drive is why you hunt. Your Redemption is what you must do to escape Despair.",
                    color=0x8B0000
                )

                embed.add_field(
                    name="🔍 Curiosity",
                    value="*Redemption:* Uncover new information about your quarry",
                    inline=False
                )
                embed.add_field(
                    name="⚔️ Vengeance",
                    value="*Redemption:* Hurt your quarry",
                    inline=False
                )
                embed.add_field(
                    name="🤝 Oath",
                    value="*Redemption:* Actively uphold or fulfill your oath",
                    inline=False
                )
                embed.add_field(
                    name="💰 Greed",
                    value="*Redemption:* Acquire resources from enemies",
                    inline=False
                )
                embed.add_field(
                    name="👑 Pride",
                    value="*Redemption:* Best your quarry in some contest",
                    inline=False
                )
                embed.add_field(
                    name="💚 Envy",
                    value="*Redemption:* Ally with your quarry",
                    inline=False
                )
                embed.add_field(
                    name="🕊️ Atonement",
                    value="*Redemption:* Protect someone from your quarry",
                    inline=False
                )

                view = DriveSelectionView(user_id, char['name'])
                await interaction.response.send_message(embed=embed, view=view)

        except Exception as e:
            self.logger.error(f"Error in drive command: {e}")
            await interaction.response.send_message(
                f"{HeraldEmojis.ERROR} Error setting drive",
                ephemeral=True
            )

    @app_commands.command(name="despair", description="Mark your character as entering Despair state")
    async def enter_despair(self, interaction: discord.Interaction):
        """Enter Despair state - Drive becomes unusable until redeemed"""
        user_id = str(interaction.user.id)

        try:
            # Get active character
            active_char_name = await get_active_character(user_id)
            if not active_char_name:
                await interaction.response.send_message(
                    f"{HeraldEmojis.ERROR} No active character set. Use `/character` to set your active character.",
                    ephemeral=True
                )
                return

            char = await find_character(user_id, active_char_name)
            if not char:
                await interaction.response.send_message(
                    f"{HeraldEmojis.ERROR} Could not find your active character.",
                    ephemeral=True
                )
                return

            # Check if already in Despair
            if char.get('in_despair', False):
                await interaction.response.send_message(
                    f"{HeraldEmojis.ERROR} **{char['name']}** is already in Despair!",
                    ephemeral=True
                )
                return

            # Mark character as in Despair
            async with get_async_db() as conn:
                await conn.execute(
                    "UPDATE characters SET in_despair = $1 WHERE user_id = $2 AND name = $3",
                    True, user_id, char['name']
                )

            # Invalidate cache to ensure /sheet shows updated value
            from core.character_utils import invalidate_character_cache
            invalidate_character_cache(user_id, char['name'])

            # Create response
            embed = discord.Embed(
                title=f"💀 {char['name']} Enters Despair",
                description=f"**Drive has failed.** {char['name']}'s motivations ring hollow.",
                color=0x8B0000
            )

            if char.get('drive'):
                embed.add_field(
                    name=f"{HeraldEmojis.DRIVE} Broken Drive",
                    value=char['drive'],
                    inline=False
                )

            if char.get('redemption'):
                embed.add_field(
                    name=f"{HeraldEmojis.REDEMPTION} Path to Redemption",
                    value=char['redemption'],
                    inline=False
                )
            else:
                embed.add_field(
                    name=f"{HeraldEmojis.WARNING} No Redemption Set",
                    value="Set your Drive using `/drive action:Set` - Redemption will be assigned automatically based on your chosen Drive",
                    inline=False
                )

            embed.add_field(
                name="Effects",
                value="• Cannot use Desperation dice\n• Drive is unusable\n• Must complete Redemption to recover",
                inline=False
            )

            await interaction.response.send_message(embed=embed)
            logger.info(f"{char['name']} entered Despair (user {user_id})")

        except Exception as e:
            logger.error(f"Error entering despair: {e}")
            await interaction.response.send_message(
                f"{HeraldEmojis.ERROR} Error entering Despair",
                ephemeral=True
            )

    @app_commands.command(name="redemption", description="Mark your character as redeemed from Despair")
    async def exit_despair(self, interaction: discord.Interaction):
        """Exit Despair state - Redemption completed"""
        user_id = str(interaction.user.id)

        try:
            # Get active character
            active_char_name = await get_active_character(user_id)
            if not active_char_name:
                await interaction.response.send_message(
                    f"{HeraldEmojis.ERROR} No active character set. Use `/character` to set your active character.",
                    ephemeral=True
                )
                return

            char = await find_character(user_id, active_char_name)
            if not char:
                await interaction.response.send_message(
                    f"{HeraldEmojis.ERROR} Could not find your active character.",
                    ephemeral=True
                )
                return

            # Check if in Despair
            if not char.get('in_despair', False):
                await interaction.response.send_message(
                    f"{HeraldEmojis.ERROR} **{char['name']}** is not in Despair!",
                    ephemeral=True
                )
                return

            # Mark character as redeemed
            async with get_async_db() as conn:
                await conn.execute(
                    "UPDATE characters SET in_despair = $1 WHERE user_id = $2 AND name = $3",
                    False, user_id, char['name']
                )

            # Invalidate cache to ensure /sheet shows updated value
            from core.character_utils import invalidate_character_cache
            invalidate_character_cache(user_id, char['name'])

            # Create response
            embed = discord.Embed(
                title=f"🕊️ {char['name']} Redeemed",
                description=f"**Drive restored.** {char['name']}'s purpose burns bright once more.",
                color=0x228B22
            )

            if char.get('redemption'):
                embed.add_field(
                    name=f"{HeraldEmojis.REDEMPTION} Redemption Completed",
                    value=char['redemption'],
                    inline=False
                )

            if char.get('drive'):
                embed.add_field(
                    name=f"{HeraldEmojis.DRIVE} Restored Drive",
                    value=char['drive'],
                    inline=False
                )

            embed.add_field(
                name="Effects",
                value="• Can use Desperation dice again\n• Drive is active\n• Ready to hunt",
                inline=False
            )

            await interaction.response.send_message(embed=embed)
            logger.info(f"{char['name']} redeemed from Despair (user {user_id})")

        except Exception as e:
            logger.error(f"Error exiting despair: {e}")
            await interaction.response.send_message(
                f"{HeraldEmojis.ERROR} Error exiting Despair",
                ephemeral=True
            )

    # ===== HELPER METHODS FOR ROLL INTEGRATION =====

    async def get_character_attribute(self, user_id: str, character_name: str, attribute: str) -> Optional[int]:
        """Get a specific attribute value for a character (for roll integration)"""
        try:
            async with get_async_db() as conn:
                result = await conn.fetchrow(
                    "SELECT * FROM characters WHERE user_id = $1 AND name = $2", 
                    user_id, character_name
                )
                
                return result[attribute.lower()] if result else None
        except Exception as e:
            logger.error(f"Error getting attribute {attribute}: {e}")
            return None

    async def get_character_skill(self, user_id: str, character_name: str, skill_name: str) -> Optional[int]:
        """Get a specific skill value for a character (for roll integration)"""
        try:
            async with get_async_db() as conn:
                result = await conn.fetchrow(
                    "SELECT dots FROM skills WHERE user_id = $1 AND character_name = $2 AND skill_name = $3", 
                    user_id, character_name, skill_name
                )
                
                return result['dots'] if result else None
        except Exception as e:
            logger.error(f"Error getting skill {skill_name}: {e}")
            return None

async def setup(bot: commands.Bot):
    """Setup function for the Character Gameplay cog"""
    cog = CharacterGameplay(bot)
    await bot.add_cog(cog)
    logger.info(f"Character Gameplay cog loaded with {len(cog.get_app_commands())} commands")
