import discord
from discord.ext import commands
from discord import app_commands
from core.dice import roll_pool, roll_rouse_check, simple_roll
from core.db import get_db_connection
from typing import Optional, List
import logging

logger = logging.getLogger('Herald.Roll')

# H5E Skills and Attributes for autocomplete
H5E_SKILLS = [
    # Physical
    "Athletics", "Brawl", "Craft", "Driving", "Firearms",
    "Larceny", "Melee", "Stealth", "Survival",
    # Social
    "Animal Ken", "Etiquette", "Insight", "Intimidation", "Leadership",
    "Performance", "Persuasion", "Streetwise", "Subterfuge",
    # Mental
    "Academics", "Awareness", "Finance", "Investigation", "Medicine",
    "Occult", "Politics", "Science", "Technology"
]

H5E_ATTRIBUTES = [
    "Strength", "Dexterity", "Stamina",
    "Charisma", "Manipulation", "Composure", 
    "Intelligence", "Wits", "Resolve"
]

class RollCog(commands.Cog):
    """Hunter: The Reckoning 5th Edition dice rolling commands"""
    
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="roll", description="Roll a Hunter dice pool with full H5E mechanics")
    @app_commands.describe(
        attribute="Attribute rating (0-5)",
        skill="Skill rating (0-5)", 
        desperation="Add desperation die (may cause messy criticals)",
        edge="Number of edge dice (explode on 10s)",
        difficulty="Difficulty modifier (+harder, -easier)",
        modifier="Additional dice modifier"
    )
    async def roll(
        self,
        interaction: discord.Interaction,
        attribute: int,
        skill: int,
        desperation: bool = False,
        edge: int = 0,
        difficulty: int = 0,
        modifier: int = 0
    ):
        """Enhanced roll command with full H5E mechanics"""
        
        # Input validation
        if attribute < 0 or skill < 0:
            await interaction.response.send_message(
                "❌ Attribute and Skill must be 0 or higher!", ephemeral=True
            )
            return
        
        if edge < 0:
            await interaction.response.send_message(
                "❌ Edge dice cannot be negative!", ephemeral=True
            )
            return

        # Adjust pool with modifier
        adjusted_attribute = attribute + modifier
        
        # Roll the dice
        result = roll_pool(adjusted_attribute, skill, desperation, edge, difficulty)
        
        # Build response
        embed = discord.Embed(
            title="🎲 Hunter Dice Roll",
            color=0x8B0000 if result.messy_critical else 0x4169E1
        )
        
        # Pool info
        base_pool = max(1, attribute + skill + modifier - difficulty)
        pool_desc = f"**Pool:** {base_pool} dice"
        if edge > 0:
            pool_desc += f" + {len(result.edge_dice)} edge"
        if desperation:
            pool_desc += f" + {len(result.desperation_dice)} desperation"
        
        embed.add_field(name="Dice Pool", value=pool_desc, inline=False)
        
        # Dice results
        dice_display = self._format_dice_display(result)
        embed.add_field(name="Dice Results", value=dice_display, inline=False)
        
        # Success summary
        success_text = f"**{result.total_successes}** total successes"
        if result.crits > 0:
            success_text += f"\n({result.successes} regular + {result.crits} critical)"
        
        embed.add_field(name="✅ Results", value=success_text, inline=True)
        
        # Special conditions
        if result.messy_critical:
            embed.add_field(
                name="💀 Messy Critical!", 
                value="Desperation dice contributed to criticals - complications ahead!",
                inline=False
            )
        
        # Roll breakdown in footer
        breakdown = f"Att:{attribute} + Skill:{skill}"
        if modifier != 0:
            breakdown += f" + Mod:{modifier:+d}"
        if difficulty != 0:
            breakdown += f" + Diff:{difficulty:+d}"
        if edge > 0:
            breakdown += f" + Edge:{edge}"
        if desperation:
            breakdown += " + Desperation"
            
        embed.set_footer(text=breakdown)
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="roll_char", description="Roll using your character's stats")
    @app_commands.describe(
        character="Your character name",
        attribute="Attribute to use",
        skill="Skill to use", 
        desperation="Add desperation die (may cause messy criticals)",
        edge="Number of edge dice (explode on 10s)",
        difficulty="Difficulty modifier (+harder, -easier)",
        modifier="Additional dice modifier"
    )
    @app_commands.choices(
        attribute=[app_commands.Choice(name=attr.title(), value=attr.lower()) for attr in H5E_ATTRIBUTES],
        skill=[app_commands.Choice(name=skill, value=skill) for skill in H5E_SKILLS[:25]]  # Discord limit
    )
    async def roll_char(
        self,
        interaction: discord.Interaction,
        character: str,
        attribute: str,
        skill: str,
        desperation: bool = False,
        edge: int = 0,
        difficulty: int = 0,
        modifier: int = 0
    ):
        """Roll using character stats with full H5E mechanics"""
        user_id = str(interaction.user.id)
        
        # Input validation
        if edge < 0:
            await interaction.response.send_message(
                "❌ Edge dice cannot be negative!", ephemeral=True
            )
            return
        
        try:
            # Get character stats
            char_cog = self.bot.get_cog("Character")
            if not char_cog:
                await interaction.response.send_message(
                    "❌ Character system not available!", ephemeral=True
                )
                return
            
            # Get attribute and skill values
            attr_value = await char_cog.get_character_attribute(user_id, character, attribute)
            skill_value = await char_cog.get_character_skill(user_id, character, skill)
            
            if attr_value is None:
                await interaction.response.send_message(
                    f"⚠️ Character **{character}** not found or attribute **{attribute}** invalid", 
                    ephemeral=True
                )
                return
            
            if skill_value is None:
                await interaction.response.send_message(
                    f"⚠️ Skill **{skill}** not found for character **{character}**", 
                    ephemeral=True
                )
                return
            
            # Adjust pool with modifier
            adjusted_attribute = attr_value + modifier
            
            # Roll the dice
            result = roll_pool(adjusted_attribute, skill_value, desperation, edge, difficulty)
            
            # Build response
            embed = discord.Embed(
                title=f"🎲 {character}'s Roll",
                description=f"**{attribute.title()} + {skill}**",
                color=0x8B0000 if result.messy_critical else 0x4169E1
            )
            
            # Pool info
            base_pool = max(1, attr_value + skill_value + modifier - difficulty)
            pool_desc = f"**Pool:** {base_pool} dice ({attr_value} + {skill_value}"
            if modifier != 0:
                pool_desc += f" + {modifier:+d}"
            if difficulty != 0:
                pool_desc += f" + {difficulty:+d}"
            pool_desc += ")"
            
            if edge > 0:
                pool_desc += f" + {len(result.edge_dice)} edge"
            if desperation:
                pool_desc += f" + {len(result.desperation_dice)} desperation"
            
            embed.add_field(name="Dice Pool", value=pool_desc, inline=False)
            
            # Dice results
            dice_display = self._format_dice_display(result)
            embed.add_field(name="Dice Results", value=dice_display, inline=False)
            
            # Success summary
            success_text = f"**{result.total_successes}** total successes"
            if result.crits > 0:
                success_text += f"\n({result.successes} regular + {result.crits} critical)"
            
            embed.add_field(name="✅ Results", value=success_text, inline=True)
            
            # Special conditions
            if result.messy_critical:
                embed.add_field(
                    name="💀 Messy Critical!", 
                    value="Desperation dice contributed to criticals - complications ahead!",
                    inline=False
                )
            
            # Roll breakdown in footer
            breakdown = f"{character}: {attribute.title()}({attr_value}) + {skill}({skill_value})"
            if modifier != 0:
                breakdown += f" + Mod:{modifier:+d}"
            if difficulty != 0:
                breakdown += f" + Diff:{difficulty:+d}"
            if edge > 0:
                breakdown += f" + Edge:{edge}"
            if desperation:
                breakdown += " + Desperation"
                
            embed.set_footer(text=breakdown)
            
            await interaction.response.send_message(embed=embed)
            logger.info(f"Character roll: {user_id} rolled {attribute}+{skill} for {character}")

        except Exception as e:
            logger.error(f"Error in character roll: {e}")
            await interaction.response.send_message(
                f"❌ Error rolling for character: {str(e)}", ephemeral=True
            )

    @app_commands.command(name="simple", description="Roll a simple dice pool (no H5E mechanics)")
    @app_commands.describe(
        pool="Number of dice to roll"
    )
    async def simple(self, interaction: discord.Interaction, pool: int):
        """Simple dice pool roll without H5E mechanics"""
        
        if pool < 1:
            await interaction.response.send_message(
                "❌ Pool size must be at least 1!", ephemeral=True
            )
            return
        
        if pool > 50:  # Reasonable limit
            await interaction.response.send_message(
                "❌ Pool size too large (max 50)!", ephemeral=True
            )
            return
        
        result = simple_roll(pool)
        dice_str = " ".join(str(d) for d in result["dice"])
        
        embed = discord.Embed(
            title="🎲 Simple Dice Roll",
            color=0x4169E1
        )
        
        embed.add_field(name="Dice", value=f"`{dice_str}`", inline=False)
        embed.add_field(
            name="Results", 
            value=f"**{result['total_successes']}** successes (Crits: {result['crits']})",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="rouse", description="Roll a rouse check for desperation")
    async def rouse(self, interaction: discord.Interaction):
        """Roll a rouse check for desperation management"""
        
        result = roll_rouse_check()
        
        embed = discord.Embed(
            title="🩸 Rouse Check",
            color=0x8B0000 if not result["success"] else 0x228B22
        )
        
        embed.add_field(name="Die", value=f"`{result['die']}`", inline=True)
        
        if result["success"]:
            embed.add_field(name="Result", value="✅ Success\nNo desperation gained", inline=True)
        else:
            embed.add_field(name="Result", value="❌ Failure\n+1 Desperation", inline=True)
        
        embed.set_footer(text="Success on 1-5, Failure on 6-10")
        
        await interaction.response.send_message(embed=embed)

    # Autocomplete functions
    @roll_char.autocomplete('character')
    async def character_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> List[app_commands.Choice[str]]:
        """Autocomplete user's character names"""
        try:
            user_id = str(interaction.user.id)
            conn = get_db_connection()
            cur = conn.cursor()
            
            cur.execute("SELECT name FROM characters WHERE user_id = ? ORDER BY name", (user_id,))
            characters = cur.fetchall()
            conn.close()
            
            # Filter based on current input
            filtered = [
                char['name'] for char in characters 
                if current.lower() in char['name'].lower()
            ]
            
            return [
                app_commands.Choice(name=char_name, value=char_name)
                for char_name in filtered[:25]  # Discord limit
            ]
        except Exception as e:
            logger.error(f"Error in character autocomplete: {e}")
            return []

    @roll_char.autocomplete('skill')
    async def skill_autocomplete_with_more(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> List[app_commands.Choice[str]]:
        """Autocomplete skills with more options than choices allow"""
        # Filter skills based on current input
        filtered = [
            skill for skill in H5E_SKILLS 
            if current.lower() in skill.lower()
        ]
        
        return [
            app_commands.Choice(name=skill, value=skill)
            for skill in filtered[:25]  # Discord limit
        ]

    def _format_dice_display(self, result) -> str:
        """Format dice results with visual indicators"""
        def format_die(value: int, die_type: str = "normal") -> str:
            if value == 10:
                return f"**`{value}`**"  # Bold 10s (crits)
            elif value >= 6:
                return f"`{value}`"     # Success
            else:
                return f"~~`{value}`~~" # Miss (strikethrough)
        
        display_parts = []
        
        # Base dice
        if result.dice:
            base_dice = " ".join(format_die(d) for d in result.dice)
            display_parts.append(f"**Base:** {base_dice}")
        
        # Edge dice
        if result.edge_dice:
            edge_dice = " ".join(format_die(d) for d in result.edge_dice) 
            display_parts.append(f"**Edge:** {edge_dice}")
        
        # Desperation dice
        if result.desperation_dice:
            desp_dice = " ".join(format_die(d) for d in result.desperation_dice)
            display_parts.append(f"**Desperation:** {desp_dice}")
        
        return "\n".join(display_parts)

async def setup(bot):
    await bot.add_cog(RollCog(bot))
