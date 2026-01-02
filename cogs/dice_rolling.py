"""
Dice Rolling Cog for Herald Bot - Async Version
Handles H5E dice mechanics: basic rolls, character rolls, edge dice, desperation
"""

import discord
from discord import app_commands
from discord.ext import commands
from typing import List, Optional
import logging
import random

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

# Dice result thumbnails
THUMBNAIL_URLS = {
    "success": "https://media.discordapp.net/attachments/1416859395962310716/1452436428180164850/Dice_Success.png?ex=694a7715&is=69492595&hm=0e7d686c30822ea36d26eff966680e64b1a0e4c95da6d64b09da1f38bfa06101&=&format=webp&quality=lossless",
    "failure": "https://media.discordapp.net/attachments/1416859395962310716/1452436427265806611/Dice_Failure.png?ex=6949ce55&is=69487cd5&hm=fa691cde54fcaf134758e7dc7e1ef4162953dc2671c327996e1e3912161c49ad&=&format=webp&quality=lossless",
    "critical": "https://media.discordapp.net/attachments/1416859395962310716/1452436426892378223/Dice_Critical.png?ex=6949ce55&is=69487cd5&hm=3b7b7d30205494d0875766cdcd7c036f8c57efb6fe836b8dece0add206c5dbd4&=&format=webp&quality=lossless",
    "overreach": "https://media.discordapp.net/attachments/1416859395962310716/1452436427685101750/Dice_Overreach.png?ex=6949ce55&is=69487cd5&hm=1c2991f783cf45a84fbcabf14b554d45c231e9f8c236fe268e09b726d38c876f&=&format=webp&quality=lossless"
}

# H5E Attributes for choices
H5E_ATTRIBUTES = [
    "Strength", "Dexterity", "Stamina",
    "Charisma", "Manipulation", "Composure",
    "Intelligence", "Wits", "Resolve"
]


class WillpowerRerollView(discord.ui.View):
    """View for Willpower re-roll buttons (Inconnu-style)"""

    def __init__(self, user_id: str, result: DiceResult, character_name: str = None,
                 difficulty: int = 0, danger: int = 0, pool_description: str = None):
        super().__init__(timeout=300)  # 5 minute timeout
        self.user_id = user_id
        self.result = result
        self.character_name = character_name
        self.difficulty = difficulty
        self.danger = danger
        self.pool_description = pool_description
        self.used = False

        # Conditionally show buttons based on roll state
        # Avoid Messy only shows if there's a messy critical
        if not result.messy_critical:
            self.remove_item(self.avoid_messy_button)

        # Risky Avoid only shows if there are tens
        tens_count = sum(1 for d in result.dice if d == 10)
        if tens_count == 0:
            self.remove_item(self.risky_avoid_button)

    async def _check_willpower(self, interaction: discord.Interaction) -> bool:
        """Check if character has available willpower"""
        if not self.character_name:
            await interaction.response.send_message(
                f"{HeraldEmojis.ERROR} No active character for willpower re-roll!",
                ephemeral=True
            )
            return False

        char = await find_character(self.user_id, self.character_name)
        if not char:
            await interaction.response.send_message(
                f"{HeraldEmojis.ERROR} Character not found!",
                ephemeral=True
            )
            return False

        # Correct database field names
        willpower_max = char.get('willpower', 0)
        willpower_superficial = char.get('willpower_sup', 0)
        willpower_aggravated = char.get('willpower_agg', 0)

        # Calculate available willpower
        available = willpower_max - willpower_superficial - willpower_aggravated

        if available < 1:
            await interaction.response.send_message(
                f"{HeraldEmojis.ERROR} Not enough Willpower! Need 1 undamaged Willpower to re-roll.",
                ephemeral=True
            )
            return False

        return True

    async def _spend_willpower(self):
        """Spend 1 willpower (add superficial damage)"""
        async with get_async_db() as conn:
            await conn.execute("""
                UPDATE characters
                SET willpower_sup = willpower_sup + 1
                WHERE user_id = $1 AND name = $2
            """, self.user_id, self.character_name)

        # Invalidate cache
        from core.character_utils import invalidate_character_cache
        invalidate_character_cache(self.user_id, self.character_name)

    async def _update_result(self, interaction: discord.Interaction, new_dice: List[int]):
        """Update the roll with new dice values and refresh display"""
        # Create new DiceResult with re-rolled dice
        new_result = DiceResult(new_dice, self.result.desperation_dice)

        # Spend willpower
        await self._spend_willpower()

        # Generate new embed
        new_embed = format_dice_result(
            new_result,
            self.pool_description,
            self.character_name,
            self.difficulty,
            self.danger
        )

        # Add re-roll indicator
        new_embed.set_footer(text="⚡ Willpower Re-roll Used (-1 Superficial Willpower)")

        # Disable all buttons
        for item in self.children:
            item.disabled = True

        self.used = True
        await interaction.response.edit_message(embed=new_embed, view=self)

    @discord.ui.button(label="Re-Roll Failures", style=discord.ButtonStyle.primary, emoji="🔄")
    async def reroll_failures_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Re-roll up to 3 failed regular dice (2-5)"""
        if interaction.user.id != int(self.user_id):
            await interaction.response.send_message("This isn't your roll!", ephemeral=True)
            return

        if not await self._check_willpower(interaction):
            return

        # Find failures (2-5) in regular dice only
        failures = [i for i, d in enumerate(self.result.dice) if 2 <= d <= 5]

        if not failures:
            await interaction.response.send_message(
                f"{HeraldEmojis.WARNING} No failures to re-roll!",
                ephemeral=True
            )
            return

        # Re-roll up to 3 failures
        to_reroll = failures[:3]
        new_dice = self.result.dice.copy()

        for idx in to_reroll:
            new_dice[idx] = random.randint(1, 10)

        await self._update_result(interaction, new_dice)

    @discord.ui.button(label="Max Crits", style=discord.ButtonStyle.primary, emoji="⭐")
    async def max_crits_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Re-roll up to 3 failing dice; if fewer than 3 failures, also re-roll successes"""
        if interaction.user.id != int(self.user_id):
            await interaction.response.send_message("This isn't your roll!", ephemeral=True)
            return

        if not await self._check_willpower(interaction):
            return

        # Find failures (2-5) and successes (6-9) in regular dice
        failures = [i for i, d in enumerate(self.result.dice) if 2 <= d <= 5]
        successes = [i for i, d in enumerate(self.result.dice) if 6 <= d <= 9]

        # Priority: failures first, then successes
        to_reroll = failures[:3]
        if len(to_reroll) < 3:
            # Add successes to reach 3
            remaining = 3 - len(to_reroll)
            to_reroll.extend(successes[:remaining])

        if not to_reroll:
            await interaction.response.send_message(
                f"{HeraldEmojis.WARNING} No dice to re-roll for crits!",
                ephemeral=True
            )
            return

        new_dice = self.result.dice.copy()
        for idx in to_reroll:
            new_dice[idx] = random.randint(1, 10)

        await self._update_result(interaction, new_dice)

    @discord.ui.button(label="Avoid Messy", style=discord.ButtonStyle.danger, emoji="💀")
    async def avoid_messy_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Re-roll tens to attempt to avoid Messy Critical"""
        if interaction.user.id != int(self.user_id):
            await interaction.response.send_message("This isn't your roll!", ephemeral=True)
            return

        if not await self._check_willpower(interaction):
            return

        # Find tens in regular dice
        tens = [i for i, d in enumerate(self.result.dice) if d == 10]

        if not tens:
            await interaction.response.send_message(
                f"{HeraldEmojis.WARNING} No tens to re-roll!",
                ephemeral=True
            )
            return

        new_dice = self.result.dice.copy()
        for idx in tens:
            new_dice[idx] = random.randint(1, 10)

        await self._update_result(interaction, new_dice)

    @discord.ui.button(label="Risky Avoid", style=discord.ButtonStyle.danger, emoji="⚠️")
    async def risky_avoid_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Re-roll tens; if <3 tens, also re-roll failures"""
        if interaction.user.id != int(self.user_id):
            await interaction.response.send_message("This isn't your roll!", ephemeral=True)
            return

        if not await self._check_willpower(interaction):
            return

        # Find tens and failures in regular dice
        tens = [i for i, d in enumerate(self.result.dice) if d == 10]
        failures = [i for i, d in enumerate(self.result.dice) if 2 <= d <= 5]

        # Re-roll all tens first
        to_reroll = tens.copy()

        # If fewer than 3 tens, add failures
        if len(to_reroll) < 3:
            remaining = 3 - len(to_reroll)
            to_reroll.extend(failures[:remaining])

        if not to_reroll:
            await interaction.response.send_message(
                f"{HeraldEmojis.WARNING} No dice to re-roll!",
                ephemeral=True
            )
            return

        new_dice = self.result.dice.copy()
        for idx in to_reroll:
            new_dice[idx] = random.randint(1, 10)

        await self._update_result(interaction, new_dice)


def format_dice_result(result: DiceResult, pool_description: str = None,
                      character_name: str = None, difficulty: int = 0, danger: int = 0) -> discord.Embed:
    """Format dice result in clean Inconnu-style layout"""

    # === STEP 1: Calculate core values ===
    margin = result.total_successes - difficulty

    # === STEP 1.5: Check for automatic despair ===
    # Automatic despair = failed roll + desperation 1s
    is_automatic_despair = False
    if result.has_overreach:
        is_win = result.total_successes >= difficulty if difficulty > 0 else result.total_successes > 0
        is_automatic_despair = not is_win

    # === STEP 2: Get formatted components ===
    if is_automatic_despair:
        success_text = "AUTOMATIC DESPAIR"
        color = 0x8B0000  # Dark red for despair
    else:
        # Check if roll failed (negative margin means didn't meet difficulty)
        if difficulty > 0 and margin < 0:
            success_text = "FAILURE"
            color = HeraldEmojis.COLOR_TOTAL_FAILURE
        else:
            success_text = create_success_description(result.total_successes, result.crits, result.messy_critical)
            color = get_result_color(result.total_successes, result.crits, result.messy_critical)
    margin_text = format_margin_display(margin)

    # === STEP 2.5: Determine thumbnail based on result type ===
    thumbnail_url = None
    if is_automatic_despair:
        # Automatic despair uses overreach thumbnail
        thumbnail_url = THUMBNAIL_URLS.get("overreach")
    elif difficulty > 0 and margin < 0:
        # Failed to meet difficulty
        thumbnail_url = THUMBNAIL_URLS.get("failure")
    elif result.has_overreach or result.messy_critical:
        # Overreach choice or messy critical
        thumbnail_url = THUMBNAIL_URLS.get("overreach")
    elif result.crits > 0:
        # Critical win (at least one pair of 10s)
        thumbnail_url = THUMBNAIL_URLS.get("critical")
    elif result.total_successes > 0:
        # Regular success
        thumbnail_url = THUMBNAIL_URLS.get("success")
    else:
        # Total failure
        thumbnail_url = THUMBNAIL_URLS.get("failure")

    # === STEP 3: Create embed with clean title and thumbnail ===
    if character_name:
        embed = discord.Embed(title=character_name, color=color)
    else:
        embed = discord.Embed(title="Dice Roll", color=color)

    # Set thumbnail if URL is available
    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)
    
    # === STEP 4: Main result (large, prominent) ===
    embed.add_field(name="", value=f"**{success_text}**", inline=False)

    # === STEP 4.5: Comment (if provided) ===
    # Extract comment from pool_description if it contains a newline
    if pool_description and "\n" in pool_description:
        comment_text = pool_description.split("\n")[0]
        embed.add_field(name="", value=f"*{comment_text}*", inline=False)

    # === STEP 5: Margin ===
    if difficulty > 0:
        embed.add_field(name="Margin", value=str(margin), inline=False)

    # === STEP 6: Dice display ===
    dice_display = create_inconnu_dice_display(result)
    if dice_display:
        embed.add_field(name="", value=dice_display, inline=False)

    # === STEP 7: Pool | Desperation | Difficulty (Inconnu-style table) ===
    headers = []
    values = []

    # Always show dice count
    headers.append("Dice")
    values.append(str(len(result.dice)))

    # Desperation dice count
    if result.desperation_dice:
        headers.append("Desperation")
        values.append(str(len(result.desperation_dice)))

    # Difficulty
    if difficulty > 0:
        actual_diff = difficulty + danger if danger > 0 else difficulty
        headers.append("Difficulty")
        values.append(str(actual_diff))

    if headers:
        # Create table-like layout with proper spacing
        header_line = "    ".join(f"{h:<12}" for h in headers).rstrip()
        value_line = "    ".join(f"{v:<12}" for v in values).rstrip()
        table_text = f"```\n{header_line}\n{value_line}\n```"
        embed.add_field(name="", value=table_text, inline=False)

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
        difficulty="Difficulty (0=Auto, 1=Simple, 2=Standard, 3=Hard, 4=Extreme, 5=Nearly Impossible, 6=Legendary, 7+=Epic)",
        comment="Description of what you're rolling for"
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

        if difficulty < 0 or difficulty > 20:
            await interaction.response.send_message(
                f"{HeraldEmojis.ERROR} Difficulty must be 0-20",
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

            # Get character danger if applicable
            danger = 0
            if char_name:
                char = await find_character(user_id, char_name)
                if char:
                    danger = char.get('danger', 0) or 0

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
            embed = format_dice_result(result, description, char_name, difficulty=difficulty, danger=danger)

            # Create willpower re-roll view (only if character is present)
            view = None
            if char_name:
                view = WillpowerRerollView(
                    user_id=user_id,
                    result=result,
                    character_name=char_name,
                    difficulty=difficulty,
                    danger=danger,
                    pool_description=description
                )

            await interaction.response.send_message(embed=embed, view=view)

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
