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
    ensure_h5e_columns, ALL_SKILLS, H5E_SKILLS, HeraldMessages, resolve_character
)
from core.ui_utils import (
    HeraldEmojis, HeraldMessages, HeraldColors, create_health_bar, create_willpower_bar,
    create_edge_bar, create_desperation_bar
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


class CharacterGameplay(commands.Cog):
    """Character Gameplay - H5E mechanics and combat systems"""
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger('Herald.Character.Gameplay')

    @app_commands.command(name="damage", description="Apply health or willpower damage to your character")
    @app_commands.describe(
        character="Character name (optional - uses active character if not specified)",
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
    @app_commands.autocomplete(character=character_autocomplete)
    async def apply_damage(
        self,
        interaction: discord.Interaction,
        track: str,
        amount: int,
        damage_type: str = "superficial",
        character: str = None
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
            # Resolve character (uses active if not specified)
            char = await resolve_character(user_id, character)

            if not char:
                await interaction.response.send_message(
                    f"{HeraldEmojis.ERROR} No character specified and no active character set. Use `/character` to set your active character.",
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
        character="Character name (optional - uses active character if not specified)",
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
    @app_commands.autocomplete(character=character_autocomplete)
    async def heal_damage(
        self,
        interaction: discord.Interaction,
        track: str,
        heal_type: str,
        amount: int = None,
        character: str = None
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
            char = await resolve_character(user_id, character)

            if not char:
                await interaction.response.send_message(
                    f"{HeraldEmojis.ERROR} No character specified and no active character set. Use `/character` to set your active character.",
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
        amount="Amount to add/subtract/set (optional for 'view')",
        character="Character name (optional - uses active character if not specified)"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="View", value="view"),
        app_commands.Choice(name="Set", value="set"),
        app_commands.Choice(name="Add", value="add"),
        app_commands.Choice(name="Subtract", value="subtract")
    ])
    @app_commands.autocomplete(character=character_autocomplete)
    async def desperation(self, interaction: discord.Interaction, action: str, amount: int = None, character: str = None):
        """Manage character Desperation levels (0-10)"""

        user_id = str(interaction.user.id)

        try:
            char = await resolve_character(user_id, character)

            if not char:
                await interaction.response.send_message(
                    f"{HeraldEmojis.ERROR} No character specified and no active character set. Use `/character` to set your active character.",
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
            
            # Create response
            desperation_bar = create_desperation_bar(new_desperation)
            
            embed = discord.Embed(
                title=f"{HeraldEmojis.DESPERATION} Desperation Updated",
                description=f"😰 Desperation activated: {current_desperation} → {new_desperation}\n{HeraldMessages.PATTERN_LOGGED}: Risk increases with reward\n{desperation_bar}",
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
        creed="Hunter Creed (leave empty to view current)",
        character="Character name (optional - uses active character if not specified)"
    )
    @app_commands.choices(creed=[
        app_commands.Choice(name="Entrepreneurial - Building, inventing, repairing", value="Entrepreneurial"),
        app_commands.Choice(name="Faithful - Direct conflict with the supernatural", value="Faithful"),
        app_commands.Choice(name="Inquisitive - Gaining information", value="Inquisitive"),
        app_commands.Choice(name="Martial - Physical conflict", value="Martial"),
        app_commands.Choice(name="Underground - Stealth and subterfuge", value="Underground")
    ])
    @app_commands.autocomplete(character=character_autocomplete)
    async def creed(self, interaction: discord.Interaction, creed: str = None, character: str = None):
        """Manage character Creed (Hunter type/philosophy)"""

        user_id = str(interaction.user.id)

        try:
            char = await resolve_character(user_id, character)

            if not char:
                await interaction.response.send_message(
                    f"{HeraldEmojis.ERROR} No character specified and no active character set. Use `/character` to set your active character.",
                    ephemeral=True
                )
                return

            # If no creed provided, show current
            if creed is None:
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

                await interaction.response.send_message(embed=embed)
                return

            # Set the creed with async
            async with get_async_db() as conn:
                await conn.execute(
                    "UPDATE characters SET creed = $1 WHERE user_id = $2 AND name = $3",
                    creed, user_id, char['name']
                )

            embed = discord.Embed(
                title=f"{HeraldEmojis.CREED} Creed Set",
                description=f"**{char['name']}'s Creed:** {creed}",
                color=0x8B0000
            )

            embed.set_footer(text="Use Desperation dice when your action aligns with your Creed Field")

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            self.logger.error(f"Error setting creed: {e}")
            await interaction.response.send_message(
                f"{HeraldEmojis.ERROR} Error setting creed",
                ephemeral=True
            )

    @app_commands.command(name="ambition", description="View or set your character's Ambition")
    @app_commands.describe(
        ambition="Long-term goal (leave empty to view current ambition)",
        character="Character name (optional - uses active character if not specified)"
    )
    @app_commands.autocomplete(character=character_autocomplete)
    async def ambition(self, interaction: discord.Interaction, ambition: str = None, character: str = None):
        """Manage character Ambition (long-term goal that recovers aggravated willpower damage)"""

        user_id = str(interaction.user.id)

        if ambition and len(ambition) > 200:
            await interaction.response.send_message(
                f"{HeraldEmojis.ERROR} Ambition must be 200 characters or less", 
                ephemeral=True
            )
            return

        try:
            char = await resolve_character(user_id, character)

            if not char:
                await interaction.response.send_message(
                    f"{HeraldEmojis.ERROR} No character specified and no active character set. Use `/character` to set your active character.",
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
                        value="Use `/ambition character:Name ambition:\"Your long-term goal\"` to set an ambitious goal for your Hunter.\n\n**Examples:**\n• Destroy the vampire nest in the city\n• Find out what happened to my family\n• Prove the supernatural exists to the world", 
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
        desire="Short-term goal (leave empty to view current desire)",
        character="Character name (optional - uses active character if not specified)"
    )
    @app_commands.autocomplete(character=character_autocomplete)
    async def desire(self, interaction: discord.Interaction, desire: str = None, character: str = None):
        """Manage character Desire (short-term goal that recovers superficial willpower damage)"""
        
        user_id = str(interaction.user.id)
        
        if desire and len(desire) > 200:
            await interaction.response.send_message(
                f"{HeraldEmojis.ERROR} Desire must be 200 characters or less", 
                ephemeral=True
            )
            return

        try:
            char = await resolve_character(user_id, character)

            if not char:
                await interaction.response.send_message(
                    f"{HeraldEmojis.ERROR} No character specified and no active character set. Use `/character` to set your active character.",
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
                        value="Use `/desire character:Name desire:\"Your short-term goal\"` to set a desire for this session.\n\n**Examples:**\n• Find evidence of the creature's lair\n• Protect an innocent from harm\n• Get revenge on a specific enemy", 
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
        drive="Your Drive (why you hunt) - leave empty to view current",
        character="Character name (optional - uses active character if not specified)"
    )
    @app_commands.choices(drive=[
        app_commands.Choice(name="Curiosity - Uncover new information about your quarry", value="Curiosity"),
        app_commands.Choice(name="Vengeance - Hurt your quarry", value="Vengeance"),
        app_commands.Choice(name="Oath - Actively uphold or fulfill your oath", value="Oath"),
        app_commands.Choice(name="Greed - Acquire resources from enemies", value="Greed"),
        app_commands.Choice(name="Pride - Best your quarry in some contest", value="Pride"),
        app_commands.Choice(name="Envy - Ally with your quarry", value="Envy"),
        app_commands.Choice(name="Atonement - Protect someone from your quarry", value="Atonement")
    ])
    @app_commands.autocomplete(character=character_autocomplete)
    async def drive(self, interaction: discord.Interaction, drive: str = None, character: str = None):
        """Manage character Drive (reason for hunting) and Redemption (healing from Despair)"""

        user_id = str(interaction.user.id)

        # Drive-Redemption mappings from H5E
        drive_redemptions = {
            "Curiosity": "Uncover new information about your quarry",
            "Vengeance": "Hurt your quarry",
            "Oath": "Actively uphold or fulfill your oath",
            "Greed": "Acquire resources from enemies",
            "Pride": "Best your quarry in some contest",
            "Envy": "Ally with your quarry",
            "Atonement": "Protect someone from your quarry"
        }

        try:
            char = await resolve_character(user_id, character)

            if not char:
                await interaction.response.send_message(
                    f"{HeraldEmojis.ERROR} No character specified and no active character set. Use `/character` to set your active character.",
                    ephemeral=True
                )
                return

            current_drive = char['drive']
            current_redemption = char['redemption']

            # If no drive provided, show current drive and redemption
            if drive is None:
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

                await interaction.response.send_message(embed=embed)
                return

            # Set both drive and its associated redemption
            redemption = drive_redemptions.get(drive, drive)

            async with get_async_db() as conn:
                await conn.execute(
                    "UPDATE characters SET drive = $1, redemption = $2 WHERE user_id = $3 AND name = $4",
                    drive, redemption, user_id, char['name']
                )

            embed = discord.Embed(
                title=f"{HeraldEmojis.DRIVE} Drive Set",
                description=f"**{char['name']}'s Drive:** {drive}",
                color=0x8B0000
            )

            embed.add_field(
                name=f"{HeraldEmojis.REDEMPTION} Redemption",
                value=redemption,
                inline=False
            )

            embed.set_footer(text="Achieve your Redemption to recover from Despair")

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            self.logger.error(f"Error setting drive: {e}")
            await interaction.response.send_message(
                f"{HeraldEmojis.ERROR} Error setting drive",
                ephemeral=True
            )

    @app_commands.command(name="enter_despair", description="Mark your character as entering Despair state")
    @app_commands.describe(
        character="Character name (optional - uses active character if not specified)"
    )
    @app_commands.autocomplete(character=character_autocomplete)
    async def enter_despair(self, interaction: discord.Interaction, character: str = None):
        """Enter Despair state - Drive becomes unusable until redeemed"""
        user_id = str(interaction.user.id)

        try:
            char = await resolve_character(user_id, character)

            if not char:
                await interaction.response.send_message(
                    f"{HeraldEmojis.ERROR} No character specified and no active character set. Use `/character` to set your active character.",
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
                    "UPDATE characters SET in_despair = TRUE WHERE user_id = $1 AND name = $2",
                    user_id, char['name']
                )

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
                    value="Use `/drive character:Name redemption:\"method\"` to set how this character can redeem their Drive",
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

    @app_commands.command(name="exit_despair", description="Mark your character as redeemed from Despair")
    @app_commands.describe(
        character="Character name (optional - uses active character if not specified)"
    )
    @app_commands.autocomplete(character=character_autocomplete)
    async def exit_despair(self, interaction: discord.Interaction, character: str = None):
        """Exit Despair state - Redemption completed"""
        user_id = str(interaction.user.id)

        try:
            char = await resolve_character(user_id, character)

            if not char:
                await interaction.response.send_message(
                    f"{HeraldEmojis.ERROR} No character specified and no active character set. Use `/character` to set your active character.",
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
                    "UPDATE characters SET in_despair = FALSE WHERE user_id = $1 AND name = $2",
                    user_id, char['name']
                )

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

    # ===== AUTOCOMPLETE FUNCTIONS =====
    
    @apply_damage.autocomplete('character')
    @heal_damage.autocomplete('character')
    @desperation.autocomplete('character')
    @creed.autocomplete('character')
    @ambition.autocomplete('character')
    @desire.autocomplete('character')
    @drive.autocomplete('character')
    @enter_despair.autocomplete('character')
    @exit_despair.autocomplete('character')
    async def gameplay_character_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> List[app_commands.Choice[str]]:
        """Autocomplete character names for gameplay commands"""
        return await character_autocomplete(interaction, current)


async def setup(bot: commands.Bot):
    """Setup function for the Character Gameplay cog"""
    cog = CharacterGameplay(bot)
    await bot.add_cog(cog)
    logger.info(f"Character Gameplay cog loaded with {len(cog.get_app_commands())} commands")
