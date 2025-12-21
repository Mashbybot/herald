"""
Dice Rolling Cog for Herald Bot - Async Version
Handles H5E dice mechanics: basic rolls, character rolls, edge dice, desperation
"""

import discord
from discord import app_commands
from discord.ext import commands
from typing import List, Optional
import logging

from core.dice import roll_pool, simple_roll, roll_rouse_check, DiceResult
from core.dice_utils import (
    get_die_emoji, format_dice_display, get_result_color, 
    create_success_description, format_margin_display, sort_dice_for_display
)
from core.character_utils import (
    find_character, character_autocomplete, get_character_attribute, get_character_skill,
    get_active_character, ALL_SKILLS
)
from core.ui_utils import HeraldEmojis, HeraldMessages, HeraldColors
from core.db import get_async_db
from config.settings import GUILD_ID

logger = logging.getLogger('Herald.Dice')

# H5E Attributes for choices
H5E_ATTRIBUTES = [
    "Strength", "Dexterity", "Stamina",
    "Charisma", "Manipulation", "Composure", 
    "Intelligence", "Wits", "Resolve"
]


def format_dice_result(result: DiceResult, pool_description: str = None, 
                      character_name: str = None, difficulty: int = 0, danger: int = 0) -> discord.Embed:
    """Format dice result in clean Inconnu-style layout"""
    
    # === STEP 1: Calculate core values ===
    margin = result.total_successes - difficulty
    
    # === STEP 2: Get formatted components ===
    success_text = create_success_description(result.total_successes, result.crits, result.messy_critical)
    color = get_result_color(result.total_successes, result.crits, result.messy_critical)
    margin_text = format_margin_display(margin)
    
    # === STEP 3: Create embed with clean title ===
    if character_name:
        embed = discord.Embed(title=character_name, color=color)
    else:
        embed = discord.Embed(title="Dice Roll", color=color)
    
    # === STEP 4: Main result (large, prominent) ===
    embed.add_field(name="", value=f"# **{success_text}**", inline=False)
    
    # === STEP 5: Pool calculation (small subtitle) ===
    if pool_description:
        pool_calc = pool_description.split(" = ")[0] if " = " in pool_description else pool_description
        embed.add_field(name="", value=f"-# {pool_calc}", inline=False)
    
    # === STEP 6: Danger warning (if present) ===
    if danger > 0:
        embed.add_field(
            name="",
            value=f"⚠️ **Danger {danger}** active (adds +{danger} to difficulty)",
            inline=False
        )
    
    # === STEP 7: Dice display ===
    dice_display = create_inconnu_dice_display(result)
    if dice_display:
        embed.add_field(name="", value=dice_display, inline=False)
    
    # === STEP 8: Margin if difficulty was set ===
    if difficulty > 0:
        embed.add_field(name="", value=margin_text, inline=False)

    # === STEP 9: Critical warnings with Herald's voice ===
    if result.messy_critical:
        embed.add_field(
            name="",
            value=f"💀 **Messy Critical!** Desperation dice contributed to success.\n{HeraldMessages.PATTERN_WARNING}: Desperation leaves traces",
            inline=False
        )
    elif result.crits > 0:
        # Regular critical pair
        embed.add_field(
            name="",
            value=f"{HeraldMessages.PATTERN_RECOGNIZED}: Exceptional execution",
            inline=False
        )

    # === STEP 10: Overreach/Despair warnings ===
    if result.has_overreach:
        # Check if this is a win or loss situation
        is_win = result.total_successes >= difficulty if difficulty > 0 else result.total_successes > 0

        if is_win:
            # Win condition - player chooses Overreach or Despair
            embed.add_field(
                name="",
                value=f"⚠️ **DESPERATION TRIGGERED** - Rolled {result.desperation_ones} one(s) on Desperation dice!\n\n"
                      f"**Choose:**\n"
                      f"🎯 Accept success + **Overreach** (Danger +{result.desperation_ones})\n"
                      f"💀 Reject success + Enter **Despair**\n\n"
                      f"Use `/overreach` or `/despair` to decide",
                inline=False
            )
        else:
            # Loss condition - automatic Despair
            embed.add_field(
                name="",
                value=f"💀 **AUTOMATIC DESPAIR** - Failed roll + {result.desperation_ones} one(s) on Desperation dice\n\n"
                      f"Drive becomes useless until redeemed.\n"
                      f"Use `/despair` to mark character state.",
                inline=False
            )

    return embed


def create_inconnu_dice_display(result: DiceResult) -> str:
    """Create visual dice emoji display in Inconnu style with sorted dice"""

    # Regular dice (sort successes first)
    regular_dice = result.dice
    sorted_regular = sort_dice_for_display(regular_dice)
    regular_display = format_dice_display(sorted_regular, "regular")
    
    # Desperation dice (sort successes first)
    sorted_desperation = sort_dice_for_display(result.desperation_dice)
    desperation_display = format_dice_display(sorted_desperation, "desperation")
    
    # Format the display - simple row like Inconnu
    if regular_display and desperation_display:
        return f"{regular_display} | {desperation_display}"
    elif regular_display:
        return regular_display
    elif desperation_display:
        return desperation_display
    else:
        return ""


class DiceRolling(commands.Cog):
    """Dice Rolling - H5E dice mechanics and character integration"""
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger('Herald.Dice')

    @app_commands.command(name="roll", description="Roll dice using H5E mechanics")
    @app_commands.describe(
        pool="Total dice pool to roll",
        desperate="Use Desperation dice (adds dots from your Desperation track)",
        difficulty="Target number of successes needed",
        comment="Description of what you're rolling for"
    )
    @app_commands.choices(
        difficulty=[
            app_commands.Choice(name="Difficulty 0 (Automatic)", value=0),
            app_commands.Choice(name="Difficulty 1 (Simple)", value=1),
            app_commands.Choice(name="Difficulty 2 (Standard)", value=2),
            app_commands.Choice(name="Difficulty 3 (Hard)", value=3),
            app_commands.Choice(name="Difficulty 4 (Extreme)", value=4),
            app_commands.Choice(name="Difficulty 5 (Nearly Impossible)", value=5),
            app_commands.Choice(name="Difficulty 6 (Legendary)", value=6)
        ]
    )
    async def roll_dice(
        self,
        interaction: discord.Interaction,
        pool: int,
        desperate: bool = False,
        difficulty: int = 0,
        comment: str = None
    ):
        """Roll dice using H5E mechanics"""
        user_id = str(interaction.user.id)

        # Validate inputs
        if pool < 1 or pool > 20:
            await interaction.response.send_message(
                f"{HeraldEmojis.ERROR} Pool must be 1-20 dice",
                ephemeral=True
            )
            return

        try:
            # Get desperation dice from character's track if desperate=True
            desperation_dice = 0
            char_name = None
            char_desperation = 0

            if desperate:
                # Get active character
                active_char_name = await get_active_character(user_id)
                if active_char_name:
                    char = await find_character(user_id, active_char_name)
                    if char:
                        char_name = char['name']
                        char_desperation = char.get('desperation', 0) or 0

                        # Check if in despair
                        in_despair = char.get('in_despair', False) or False
                        if in_despair:
                            await interaction.response.send_message(
                                f"{HeraldEmojis.ERROR} **{char['name']}** is in Despair!\n"
                                f"💀 Drive is unusable until redeemed.\n"
                                f"🕊️ Redemption: {char.get('redemption', 'Not set')}",
                                ephemeral=True
                            )
                            return

                        if char_desperation > 0:
                            desperation_dice = char_desperation
                        else:
                            await interaction.response.send_message(
                                f"{HeraldEmojis.ERROR} {char['name']} has no Desperation to use!",
                                ephemeral=True
                            )
                            return
                else:
                    await interaction.response.send_message(
                        f"{HeraldEmojis.ERROR} No active character set. Use `/character` to select one before using desperate rolls.",
                        ephemeral=True
                    )
                    return

            # Roll the dice
            result = roll_pool(pool, 0, desperation_dice, 0)

            # Create description
            pool_parts = []
            pool_parts.append(f"Pool {pool}")
            if desperation_dice > 0:
                pool_parts.append(f"Desperation {desperation_dice}")

            description = " + ".join(pool_parts) + f" = {pool + desperation_dice} dice"

            if difficulty > 0:
                description += f" vs Difficulty {difficulty}"

            # Add comment if provided
            if comment:
                description = f"{comment}\n{description}"

            # Format and send result with character name if available
            embed = format_dice_result(result, description, char_name, difficulty=difficulty)
            await interaction.response.send_message(embed=embed)

            log_desc = f"{comment} - " if comment else ""
            logger.info(f"Manual roll: {log_desc}{description} -> {result.total_successes} successes")

        except Exception as e:
            logger.error(f"Error in roll command: {e}")
            await interaction.response.send_message(
                f"{HeraldEmojis.ERROR} Error rolling dice: {str(e)}",
                ephemeral=True
            )

    @app_commands.command(name="danger", description="View or set your character's Danger rating")
    @app_commands.describe(
        action="What to do with Danger rating",
        amount="Amount to add/subtract/set (optional for 'view')"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="View", value="view"),
        app_commands.Choice(name="Set", value="set"),
        app_commands.Choice(name="Add", value="add"),
        app_commands.Choice(name="Subtract", value="subtract"),
        app_commands.Choice(name="Reset", value="reset")
    ])
    async def danger_command(
        self,
        interaction: discord.Interaction,
        action: str,
        amount: int = None
    ):
        """Manage character-specific Danger ratings"""
        user_id = str(interaction.user.id)

        try:
            # Get active character
            active_char_name = await get_active_character(user_id)
            if not active_char_name:
                await interaction.response.send_message(
                    f"{HeraldEmojis.ERROR} No active character set. Use `/character` to select one.",
                    ephemeral=True
                )
                return

            # Find character using the active character name
            char = await find_character(user_id, active_char_name)
            if not char:
                error_msg = await HeraldMessages.character_not_found(user_id, active_char_name)
                await interaction.response.send_message(error_msg, ephemeral=True)
                return
            
            # Get current danger
            current_danger = char.get('danger', 0) or 0
            
            # Handle different actions
            if action == "view":
                danger_filled = "🔴" * current_danger
                danger_empty = "⚫" * (5 - current_danger)
                danger_bar = f"{danger_filled}{danger_empty}"
                
                embed = discord.Embed(
                    title=f"⚠️ {char['name']}'s Danger",
                    description=f"**Current Rating:** {current_danger}/5\n{danger_bar}",
                    color=0xFF4500 if current_danger >= 4 else 0xFFD700 if current_danger >= 2 else 0x4169E1
                )
                
                embed.add_field(
                    name="What is Danger?",
                    value="Danger represents supernatural peril in the scene. It adds to the difficulty of all rolls.",
                    inline=False
                )
                
                if current_danger > 0:
                    embed.add_field(
                        name="Current Effect",
                        value=f"+{current_danger} to all roll difficulties",
                        inline=False
                    )
                
                await interaction.response.send_message(embed=embed)
                return
            
            # For other actions, calculate new danger value
            if action == "reset":
                new_danger = 0
            elif action == "set":
                if amount is None:
                    await interaction.response.send_message(
                        f"{HeraldEmojis.ERROR} Please specify an amount for set action",
                        ephemeral=True
                    )
                    return
                new_danger = max(0, min(amount, 5))
            elif action == "add":
                if amount is None:
                    await interaction.response.send_message(
                        f"{HeraldEmojis.ERROR} Please specify an amount for add action",
                        ephemeral=True
                    )
                    return
                new_danger = max(0, min(current_danger + amount, 5))
            else:  # subtract
                if amount is None:
                    await interaction.response.send_message(
                        f"{HeraldEmojis.ERROR} Please specify an amount for subtract action",
                        ephemeral=True
                    )
                    return
                new_danger = max(0, current_danger - amount)
            
            # Update database with async
            async with get_async_db() as conn:
                await conn.execute("""
                    UPDATE characters
                    SET danger = $1
                    WHERE user_id = $2 AND name = $3
                """, new_danger, user_id, char['name'])

            # Invalidate cache to ensure /sheet shows updated value
            from core.character_utils import invalidate_character_cache
            invalidate_character_cache(user_id, char['name'])

            # Create response
            change = new_danger - current_danger
            change_text = f"+{change}" if change > 0 else str(change) if change < 0 else "±0"
            
            danger_filled = "🔴" * new_danger
            danger_empty = "⚫" * (5 - new_danger)
            danger_bar = f"{danger_filled}{danger_empty}"
            
            embed = discord.Embed(
                title=f"⚠️ {char['name']}'s Danger Updated",
                description=f"**{current_danger} → {new_danger}** ({change_text})",
                color=0xFF4500 if new_danger >= 4 else 0xFFD700 if new_danger >= 2 else 0x4169E1
            )
            
            embed.add_field(
                name="New Rating",
                value=f"**{new_danger}/5**\n{danger_bar}",
                inline=False
            )
            
            if new_danger >= 4 and current_danger < 4:
                embed.add_field(
                    name="⚠️ High Danger!",
                    value="Your character is now in extreme supernatural peril!",
                    inline=False
                )
            elif new_danger == 0 and current_danger > 0:
                embed.add_field(
                    name="✅ Safety Restored",
                    value="Your character is no longer in supernatural danger.",
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed)
            logger.info(f"Updated danger for {char['name']}: {current_danger} → {new_danger} (user {user_id})")
            
        except Exception as e:
            logger.error(f"Error in danger command: {e}")
            await interaction.response.send_message(
                f"{HeraldEmojis.ERROR} An error occurred while managing Danger rating", 
                ephemeral=True
            )

    # ===== AUTOCOMPLETE FUNCTIONS =====
    # (None needed for current dice commands)


async def setup(bot: commands.Bot):
    """Setup function for the Dice Rolling cog"""
    cog = DiceRolling(bot)
    await bot.add_cog(cog)
    logger.info(f"Dice Rolling cog loaded with {len(cog.get_app_commands())} commands")
