"""
Dice Rolling Cog for Herald Bot - Fixed with Inconnu-style formatting
Handles H5E dice mechanics: basic rolls, character rolls, edge dice, desperation
"""
import asyncio
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
    find_character, character_autocomplete, get_character_attribute, get_character_skill, ALL_SKILLS
)
from core.ui_utils import HeraldEmojis, HeraldMessages  # ← Moved to correct module
from core.db import get_db_connection
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
        embed.add_field(name="", value=f"⚠️ **Danger:** {danger}", inline=False)
    
    # === STEP 7: Margin display ===
    embed.add_field(name="", value=margin_text, inline=False)
    
    # === STEP 8: Visual dice display ===
    dice_display = create_inconnu_dice_display(result)
    if dice_display:
        embed.add_field(name="", value=dice_display, inline=False)
    
    # === STEP 9: Three-column layout (numbers only) ===
    total_dice = len(result.dice) + len(result.edge_dice)
    embed.add_field(name="**Dice**", value=str(total_dice), inline=True)
    
    # Desperation column
    if result.desperation_dice:
        desperation_value = str(len(result.desperation_dice))
        if result.messy_critical:
            desperation_value += " ⚠️"
    else:
        desperation_value = "0"
    embed.add_field(name="**Desperation**", value=desperation_value, inline=True)
    
    # Difficulty column
    embed.add_field(name="**Difficulty**", value=str(difficulty) if difficulty > 0 else "0", inline=True)
    
    # === STEP 10: Messy critical warning ===
    if result.messy_critical:
        embed.add_field(
            name="",
            value="⚠️ **Messy Critical!** Desperation dice contributed to success.",
            inline=False
        )
    
    return embed


def create_inconnu_dice_display(result: DiceResult) -> str:
    """Create visual dice emoji display in Inconnu style with sorted dice"""
    
    # Regular dice (combine base + edge, sort successes first)
    regular_dice = result.dice + result.edge_dice
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
        attribute="Attribute rating (0-5)",
        skill="Skill rating (0-5)", 
        difficulty="Target number of successes needed",
        edge="Number of edge dice to add",
        desperation="Add desperation die to the roll",
        modifier="Additional dice pool modifier"
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
        attribute: int = 0,
        skill: int = 0,
        difficulty: int = 0,
        edge: int = 0,
        desperation: bool = False,
        modifier: int = 0
    ):
        """Roll dice with H5E mechanics"""
        
        # Validate inputs
        if attribute < 0 or attribute > 5:
            await interaction.response.send_message(f"{HeraldEmojis.ERROR} Attribute must be 0-5", ephemeral=True)
            return
        
        if skill < 0 or skill > 5:
            await interaction.response.send_message(f"{HeraldEmojis.ERROR} Skill must be 0-5", ephemeral=True)
            return
        
        if edge < 0 or edge > 10:
            await interaction.response.send_message(f"{HeraldEmojis.ERROR} Edge must be 0-10", ephemeral=True)
            return
        
        try:
            # Calculate effective pool (no danger for manual rolls)
            base_pool = attribute + skill + modifier
            effective_pool = max(1, base_pool)
            
            # Roll the dice
            result = roll_pool(attribute, skill, desperation, edge, 0)
            
            # Create description
            pool_parts = []
            if attribute > 0:
                pool_parts.append(f"Attribute {attribute}")
            if skill > 0:
                pool_parts.append(f"Skill {skill}")
            if modifier != 0:
                pool_parts.append(f"Modifier {modifier:+d}")
            if edge > 0:
                pool_parts.append(f"Edge {edge}")
            if desperation:
                pool_parts.append("Desperation")
            
            description = " + ".join(pool_parts) if pool_parts else "Manual Roll"
            description += f" = {effective_pool} dice"
            
            if difficulty > 0:
                description += f" vs Difficulty {difficulty}"
            
            # Format and send result (no danger for manual rolls)
            embed = format_dice_result(result, description, difficulty=difficulty, danger=0)
            await interaction.response.send_message(embed=embed)
            
            logger.info(f"Manual roll: {description} -> {result.total_successes} successes")
            
        except Exception as e:
            logger.error(f"Error in roll command: {e}")
            await interaction.response.send_message(
                f"{HeraldEmojis.ERROR} Error rolling dice: {str(e)}", 
                ephemeral=True
            )

    @app_commands.command(name="roll_char", description="Roll dice using character stats")
    @app_commands.describe(
        character="Character name",
        attribute="Attribute to use",
        skill="Skill to use",
        difficulty="Target number of successes needed",
        edge="Override character's edge rating",
        desperation="Force desperation roll",
        modifier="Additional dice pool modifier"
    )
    @app_commands.choices(
        attribute=[app_commands.Choice(name=attr, value=attr.lower()) for attr in H5E_ATTRIBUTES],
        skill=[app_commands.Choice(name=skill, value=skill) for skill in ALL_SKILLS[:25]],  # Discord limit
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
    async def roll_character(
        self,
        interaction: discord.Interaction,
        character: str,
        attribute: str,
        skill: str = None,
        difficulty: int = 0,
        edge: int = None,
        desperation: bool = None,
        modifier: int = 0
    ):
        """Roll dice using character attributes and skills"""
        user_id = str(interaction.user.id)
        
        try:
            # Find character
            char = await find_character(user_id, character)
            if not char:
                error_msg = await HeraldMessages.character_not_found(user_id, character)
                await interaction.response.send_message(error_msg, ephemeral=True)
                return
            
            # Get attribute value
            attr_value = 0
            if attribute:
                attr_value = char.get(attribute, 0)
                if attr_value is None:
                    attr_value = 0
            
            # Get skill value
            skill_value = 0
            if skill:
                skill_value = await get_character_skill(user_id, char['name'], skill)
                if skill_value is None:
                    skill_value = 0
            
            # Use character's edge if not overridden
            if edge is None:
                edge = char.get('edge', 0) or 0
            
            # Use character's danger rating automatically
            char_danger = char.get('danger', 0) or 0
            total_difficulty = difficulty + char_danger
            
            # Use character's desperation if not specified
            if desperation is None:
                char_desperation = char.get('desperation', 0) or 0
                desperation = char_desperation >= 7  # High desperation triggers desperation dice
            
            # Validate edge override
            if edge < 0 or edge > 10:
                await interaction.response.send_message(f"{HeraldEmojis.ERROR} Edge must be 0-10", ephemeral=True)
                return
            
            # Roll the dice
            result = roll_pool(attr_value, skill_value, desperation, edge, 0)
            
            # Create description
            pool_parts = []
            if attr_value > 0:
                pool_parts.append(f"{attribute.title()} {attr_value}")
            if skill_value > 0:
                pool_parts.append(f"{skill} {skill_value}")
            if modifier != 0:
                pool_parts.append(f"Modifier {modifier:+d}")
            if edge > 0:
                pool_parts.append(f"Edge {edge}")
            if desperation:
                pool_parts.append("Desperation")
            
            effective_pool = max(1, attr_value + skill_value + modifier)
            description = " + ".join(pool_parts) + f" = {effective_pool} dice"
            
            if total_difficulty > 0:
                description += f" vs Difficulty {total_difficulty}"
                if char_danger > 0:
                    description += f" ({difficulty} + {char_danger} Danger)"
            
            # Format and send result with character danger
            embed = format_dice_result(result, description, char['name'], total_difficulty, char_danger)
            await interaction.response.send_message(embed=embed)
            
            logger.info(f"Character roll for {char['name']}: {description} -> {result.total_successes} successes")
            
        except Exception as e:
            logger.error(f"Error in roll_char command: {e}")
            await interaction.response.send_message(
                f"{HeraldEmojis.ERROR} Error rolling for character: {str(e)}", 
                ephemeral=True
            )

    @app_commands.command(name="simple", description="Roll a simple dice pool")
    @app_commands.describe(
        pool="Number of dice to roll",
        description="Description of what you're rolling for"
    )
    async def simple_dice(
        self,
        interaction: discord.Interaction,
        pool: int,
        description: str = None
    ):
        """Roll a simple dice pool without H5E mechanics"""
        
        if pool < 1 or pool > 50:
            await interaction.response.send_message(
                f"{HeraldEmojis.ERROR} Pool size must be between 1 and 50", 
                ephemeral=True
            )
            return
        
        try:
            # Roll simple pool
            result_dict = simple_roll(pool)
            
            # Convert to DiceResult format for consistency
            from core.dice import DiceResult
            dice_result = DiceResult(result_dict['dice'])
            
            # Use same formatter but simpler description
            pool_desc = f"Simple {pool}-die pool"
            if description:
                pool_desc += f": {description}"
            
            embed = format_dice_result(dice_result, pool_desc, difficulty=0, danger=0)
            await interaction.response.send_message(embed=embed)
            logger.info(f"Simple roll: {pool} dice -> {dice_result.total_successes} successes")
            
        except Exception as e:
            logger.error(f"Error in simple command: {e}")
            await interaction.response.send_message(
                f"{HeraldEmojis.ERROR} Error rolling dice: {str(e)}", 
                ephemeral=True
            )

    @app_commands.command(name="rouse", description="Roll a rouse check for desperation")
    @app_commands.describe(
        character="Character to check desperation for (optional)"
    )
    async def rouse_check(self, interaction: discord.Interaction, character: str = None):
        """Roll a rouse check for desperation escalation"""
        user_id = str(interaction.user.id)
        
        try:
            # Get character info if provided
            char_name = None
            current_desperation = 0
            
            if character:
                char = await find_character(user_id, character)
                if not char:
                    error_msg = await HeraldMessages.character_not_found(user_id, character)
                    await interaction.response.send_message(error_msg, ephemeral=True)
                    return
                
                char_name = char['name']
                current_desperation = char.get('desperation', 0) or 0
            
            # Roll rouse check
            result = roll_rouse_check()
            
            # Create embed
            embed = discord.Embed(
                title=f"{HeraldEmojis.DESPERATION} Rouse Check",
                color=0x228B22 if result['success'] else 0x8B0000
            )
            
            if char_name:
                embed.description = f"**{char_name}** tests against rising desperation"
            
            # Show die result
            die_text = f"**{result['die']}**" if result['die'] >= 6 else str(result['die'])
            embed.add_field(
                name=f"{HeraldEmojis.DICE} Die Rolled",
                value=die_text,
                inline=False
            )
            
            # Show result
            if result['success']:
                embed.add_field(
                    name=f"{HeraldEmojis.SUCCESS} Success",
                    value="No desperation gained",
                    inline=False
                )
            else:
                embed.add_field(
                    name=f"{HeraldEmojis.WARNING} Failure", 
                    value="Gain 1 Desperation",
                    inline=False
                )
                
                if char_name:
                    new_desperation = min(10, current_desperation + 1)
                    embed.add_field(
                        name=f"{HeraldEmojis.DESPERATION} Desperation",
                        value=f"{char_name}: {current_desperation} → {new_desperation}",
                        inline=False
                    )
                    
                    if new_desperation >= 7:
                        embed.add_field(
                            name=f"{HeraldEmojis.WARNING} High Desperation!",
                            value="Character now rolls desperation dice on failed rolls",
                            inline=False
                        )
            
            embed.add_field(
                name="ℹ️ Rouse Check Rules",
                value="**1-5:** Success (no desperation)\n**6-10:** Failure (+1 desperation)",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed)
            logger.info(f"Rouse check: d10={result['die']}, success={result['success']}")
            
        except Exception as e:
            logger.error(f"Error in rouse command: {e}")
            await interaction.response.send_message(
                f"{HeraldEmojis.ERROR} Error rolling rouse check: {str(e)}", 
                ephemeral=True
            )

    @app_commands.command(name="danger", description="View or set your character's Danger rating")
    @app_commands.describe(
        character="Character name",
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
        character: str,
        action: str,
        amount: int = None
    ):
        """Manage character-specific Danger ratings"""
        user_id = str(interaction.user.id)
        conn = None
        
        try:
            # Find character using fuzzy matching
            char = await find_character(user_id, character)
            if not char:
                error_msg = await HeraldMessages.character_not_found(user_id, character)
                await interaction.response.send_message(error_msg, ephemeral=True)
                return
            
            # Ensure danger column exists
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Check if danger column exists, add if not
            cur.execute("PRAGMA table_info(characters)")
            columns = [row[1] for row in cur.fetchall()]
            
            if 'danger' not in columns:
                logger.info("Adding danger column to characters table")
                cur.execute("ALTER TABLE characters ADD COLUMN danger INTEGER DEFAULT 0 CHECK(danger >= 0 AND danger <= 5)")
                conn.commit()
            
            # Get current danger
            cur.execute("SELECT danger FROM characters WHERE user_id = ? AND name = ?", (user_id, char['name']))
            result = cur.fetchone()
            current_danger = result['danger'] if result and result['danger'] is not None else 0
            
            if action == "view":
                # Display current danger
                embed = discord.Embed(
                    title=f"⚠️ {char['name']}'s Danger Rating",
                    color=0xFF4500 if current_danger >= 4 else 0xFFD700 if current_danger >= 2 else 0x4169E1
                )
                
                # Create danger bar
                danger_filled = "🔴" * current_danger
                danger_empty = "⚫" * (5 - current_danger)
                danger_bar = f"{danger_filled}{danger_empty}"
                
                embed.add_field(
                    name="Current Rating",
                    value=f"**{current_danger}/5**\n{danger_bar}",
                    inline=False
                )
                
                embed.add_field(
                    name="Danger Effects",
                    value=(
                        "• **0:** No supernatural threat\n"
                        "• **1:** Minor paranormal activity\n"
                        "• **2:** Moderate supernatural danger\n"
                        "• **3:** High paranormal threat\n"
                        "• **4:** Extreme supernatural peril\n"
                        "• **5:** Reality-warping horror"
                    ),
                    inline=False
                )
                
                embed.add_field(
                    name="Usage",
                    value=f"This danger rating will be automatically added to all of {char['name']}'s rolls.",
                    inline=False
                )
                
                await interaction.response.send_message(embed=embed)
                
            else:
                # Actions that modify danger require amount
                if action != "reset" and amount is None:
                    await interaction.response.send_message(
                        f"{HeraldEmojis.WARNING} Amount required for **{action}** action", 
                        ephemeral=True
                    )
                    return
                
                # Calculate new danger
                if action == "set":
                    new_danger = amount
                elif action == "add":
                    new_danger = current_danger + amount
                elif action == "subtract":
                    new_danger = current_danger - amount
                elif action == "reset":
                    new_danger = 0
                
                # Validate range (0-5)
                new_danger = max(0, min(5, new_danger))
                
                # Update database
                cur.execute("""
                    UPDATE characters 
                    SET danger = ? 
                    WHERE user_id = ? AND name = ?
                """, (new_danger, user_id, char['name']))
                conn.commit()
                
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
        finally:
            if conn:
                conn.close()

    # Autocomplete functions
    @roll_character.autocomplete('character')
    @rouse_check.autocomplete('character')
    @danger_command.autocomplete('character')
    async def dice_character_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> List[app_commands.Choice[str]]:
        """Autocomplete character names for dice commands"""
        return await character_autocomplete(interaction, current)

    @roll_character.autocomplete('skill')
    async def dice_skill_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> List[app_commands.Choice[str]]:
        """Autocomplete skill names with enhanced error handling"""
        try:
            # Filter skills based on current input
            if not current:
                # If no input, return first 25 skills
                return [
                    app_commands.Choice(name=skill, value=skill)
                    for skill in ALL_SKILLS[:25]
                ]
                
            # Filter based on current input
            filtered = [
                skill for skill in ALL_SKILLS 
                if current.lower() in skill.lower()
            ]
                
            # Return up to 25 matches
            return [
                app_commands.Choice(name=skill, value=skill)
                for skill in filtered[:25]
            ]
                
        except Exception as e:
            # Log the error but don't let it break the autocomplete
            logger.error(f"Error in skill autocomplete: {e}")
                
            # Return a basic fallback list
            basic_skills = ["Athletics", "Firearms", "Stealth", "Investigation", "Persuasion"]
            return [
                app_commands.Choice(name=skill, value=skill)
                for skill in basic_skills
            ]


async def setup(bot: commands.Bot):
    """Setup function for the Dice Rolling cog"""
    cog = DiceRolling(bot)
    await bot.add_cog(cog)
    
    # Only register guild commands if GUILD_ID is set (development mode)
    if GUILD_ID:
        for command in cog.get_app_commands():
            bot.tree.add_command(command, guild=discord.Object(id=GUILD_ID))
        logger.info(f"Dice Rolling cog loaded with {len(cog.get_app_commands())} guild commands")
    else:
        logger.info(f"Dice Rolling cog loaded with {len(cog.get_app_commands())} global commands")
