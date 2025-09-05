"""
Character Gameplay Cog for Herald Bot
Handles game mechanics: damage, healing, Edge, Desperation, Creed, H5E character mechanics
"""

import discord
from discord import app_commands
from discord.ext import commands
from typing import List, Optional
import logging

from core.db import get_db_connection
from core.character_utils import (
    find_character, character_autocomplete, get_character_and_skills,
    ensure_h5e_columns, ALL_SKILLS, H5E_SKILLS, HeraldMessages
)
from core.ui_utils import (
    HeraldEmojis, create_health_bar, create_willpower_bar,
    create_edge_bar, create_desperation_bar
)
from config.settings import GUILD_ID

logger = logging.getLogger('Herald.Character.Gameplay')


def safe_get_character_field(character, field, default=None):
    """Safely get a field from sqlite3.Row with default value"""
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
        character="Character name",
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
        character: str,
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
            # Use fuzzy character matching
            char = await find_character(user_id, character)
            
            if not char:
                error_msg = await HeraldMessages.character_not_found(user_id, character)
                await interaction.response.send_message(error_msg, ephemeral=True)
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

            # Update database using actual character name
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(f"UPDATE characters SET {sup_field} = ?, {agg_field} = ? WHERE user_id = ? AND name = ?",
                       (new_sup, new_agg, user_id, char['name']))
            conn.commit()
            conn.close()

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
                        value="Character cannot spend willpower",
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

    @app_commands.command(name="heal", description="Heal health or willpower damage from your character")
    @app_commands.describe(
        character="Character name",
        track="Track to heal (health or willpower)",
        amount="Amount to heal",
        heal_type="Type of healing (superficial or aggravated)"
    )
    @app_commands.choices(
        track=[
            app_commands.Choice(name="Health", value="health"),
            app_commands.Choice(name="Willpower", value="willpower")
        ],
        heal_type=[
            app_commands.Choice(name="Superficial", value="superficial"),
            app_commands.Choice(name="Aggravated", value="aggravated"),
            app_commands.Choice(name="All", value="all")
        ]
    )
    async def heal_damage(
        self,
        interaction: discord.Interaction,
        character: str,
        track: str,
        amount: int,
        heal_type: str = "superficial"
    ):
        """Heal damage from a character"""
        user_id = str(interaction.user.id)
        
        if amount < 1:
            await interaction.response.send_message(
                f"{HeraldEmojis.ERROR} Heal amount must be positive", 
                ephemeral=True
            )
            return

        try:
            # Use fuzzy character matching
            char = await find_character(user_id, character)
            
            if not char:
                error_msg = await HeraldMessages.character_not_found(user_id, character)
                await interaction.response.send_message(error_msg, ephemeral=True)
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

            # Update database using actual character name
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(f"UPDATE characters SET {sup_field} = ?, {agg_field} = ? WHERE user_id = ? AND name = ?",
                       (new_sup, new_agg, user_id, char['name']))
            conn.commit()
            conn.close()

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

    @app_commands.command(name="edge", description="View or modify your character's Edge rating")
    @app_commands.describe(
        character="Character name",
        action="What to do with Edge",
        amount="Amount to add/subtract/set (optional for 'view')"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="View", value="view"),
        app_commands.Choice(name="Set", value="set"),
        app_commands.Choice(name="Add", value="add"),
        app_commands.Choice(name="Subtract", value="subtract")
    ])
    async def edge(self, interaction: discord.Interaction, character: str, action: str, amount: int = None):
        """Manage character Edge ratings (0-5)"""
        
        user_id = str(interaction.user.id)
        
        try:
            char = await find_character(user_id, character)
            if not char:
                error_msg = await HeraldMessages.character_not_found(user_id, character)
                await interaction.response.send_message(error_msg, ephemeral=True)
                return
            
            current_edge = safe_get_character_field(char, 'edge', 0)
            
            # Handle different actions
            if action == "view":
                # Create edge display
                edge_dots = HeraldEmojis.EDGE * current_edge + HeraldEmojis.EDGE_EMPTY * (5 - current_edge)
                
                embed = discord.Embed(
                    title=f"{HeraldEmojis.EDGE} {char['name']}'s Edge",
                    description=f"**Current Rating:** {current_edge}/5\n{edge_dots}",
                    color=0xFFD700 if current_edge >= 3 else 0x4169E1
                )
                
                # Add Edge benefits info
                if current_edge > 0:
                    embed.add_field(
                        name=f"{HeraldEmojis.INFO} Edge Benefits", 
                        value=f"• Add {current_edge} dice to Danger rolls\n• Enhanced supernatural resistance\n• Improved Hunter abilities", 
                        inline=False
                    )
                
                await interaction.response.send_message(embed=embed)
                
            else:
                # Actions that modify edge require amount
                if amount is None:
                    await interaction.response.send_message(
                        f"{HeraldEmojis.WARNING} Amount required for **{action}** action", 
                        ephemeral=True
                    )
                    return
                
                # Calculate new edge
                if action == "set":
                    new_edge = amount
                elif action == "add":
                    new_edge = current_edge + amount
                elif action == "subtract":
                    new_edge = current_edge - amount
                
                # Validate range (0-5)
                new_edge = max(0, min(5, new_edge))
                
                # Update database
                conn = get_db_connection()
                conn.execute("""
                    UPDATE characters 
                    SET edge = ? 
                    WHERE user_id = ? AND name = ?
                """, (new_edge, user_id, char['name']))
                conn.commit()
                conn.close()
                
                # Create response
                change = new_edge - current_edge
                change_text = f"+{change}" if change > 0 else str(change) if change < 0 else "±0"
                
                edge_dots = HeraldEmojis.EDGE * new_edge + HeraldEmojis.EDGE_EMPTY * (5 - new_edge)
                
                embed = discord.Embed(
                    title=f"{HeraldEmojis.EDGE} {char['name']}'s Edge Updated",
                    description=f"**{current_edge} → {new_edge}** ({change_text})\n{edge_dots}",
                    color=0xFFD700 if new_edge >= 3 else 0x4169E1
                )
                
                # Add note for significant changes
                if new_edge > current_edge:
                    embed.add_field(
                        name=f"{HeraldEmojis.NEW} Edge Increased!", 
                        value=f"Your character now adds {new_edge} dice to Danger rolls!", 
                        inline=False
                    )
                
                await interaction.response.send_message(embed=embed)
                
        except Exception as e:
            self.logger.error(f"Error in edge command: {e}")
            await interaction.response.send_message(
                f"{HeraldEmojis.ERROR} An error occurred while managing Edge", 
                ephemeral=True
            )

    @app_commands.command(name="desperation", description="View or modify your character's Desperation level")
    @app_commands.describe(
        character="Character name",
        action="What to do with Desperation",
        amount="Amount to add/subtract/set (optional for 'view')"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="View", value="view"),
        app_commands.Choice(name="Set", value="set"),
        app_commands.Choice(name="Add", value="add"),
        app_commands.Choice(name="Subtract", value="subtract")
    ])
    async def desperation(self, interaction: discord.Interaction, character: str, action: str, amount: int = None):
        """Manage character Desperation levels (0-10)"""
        
        user_id = str(interaction.user.id)
        
        try:
            # Use fuzzy character matching
            char = await find_character(user_id, character)
            
            if not char:
                error_msg = await HeraldMessages.character_not_found(user_id, character)
                await interaction.response.send_message(error_msg, ephemeral=True)
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
                        value="• Rolling Desperation dice on failed rolls\n• Increased supernatural vulnerability", 
                        inline=False
                    )
                
                await interaction.response.send_message(embed=embed)
                
            else:
                # Actions that modify desperation require amount
                if amount is None:
                    await interaction.response.send_message(
                        f"{HeraldEmojis.WARNING} Amount required for **{action}** action", 
                        ephemeral=True
                    )
                    return
                
                # Calculate new desperation
                if action == "set":
                    new_desperation = amount
                elif action == "add":
                    new_desperation = current_desperation + amount
                elif action == "subtract":
                    new_desperation = current_desperation - amount
                
                # Validate range (0-10)
                new_desperation = max(0, min(10, new_desperation))
                
                # Update database using actual character name
                conn = get_db_connection()
                conn.execute("""
                    UPDATE characters 
                    SET desperation = ? 
                    WHERE user_id = ? AND name = ?
                """, (new_desperation, user_id, char['name']))
                conn.commit()
                conn.close()
                
                # Create response
                change = new_desperation - current_desperation
                change_text = f"+{change}" if change > 0 else str(change) if change < 0 else "±0"
                
                desperation_bar = create_desperation_bar(new_desperation)
                
                embed = discord.Embed(
                    title=f"{HeraldEmojis.DESPERATION} {char['name']}'s Desperation Updated",
                    description=f"**{current_desperation} → {new_desperation}** ({change_text})\n{desperation_bar}",
                    color=0x8B0000 if new_desperation >= 7 else 0xFF4500 if new_desperation >= 4 else 0x4169E1
                )
                
                # Add warning for high desperation
                if new_desperation >= 7 and current_desperation < 7:
                    embed.add_field(
                        name=f"{HeraldEmojis.WARNING} High Desperation!", 
                        value="Your character is now rolling Desperation dice on failed rolls!", 
                        inline=False
                    )
                
                await interaction.response.send_message(embed=embed)
                
        except Exception as e:
            self.logger.error(f"Error in desperation command: {e}")
            await interaction.response.send_message(
                f"{HeraldEmojis.ERROR} An error occurred while managing Desperation", 
                ephemeral=True
            )

    @app_commands.command(name="creed", description="View or set your character's Creed")
    @app_commands.describe(
        character="Character name",
        creed="Creed name (leave empty to view current creed)"
    )
    async def creed(self, interaction: discord.Interaction, character: str, creed: str = None):
        """Manage character Creed"""
        
        user_id = str(interaction.user.id)
        
        try:
            # Use fuzzy character matching
            char = await find_character(user_id, character)
            
            if not char:
                error_msg = await HeraldMessages.character_not_found(user_id, character)
                await interaction.response.send_message(error_msg, ephemeral=True)
                return
            
            current_creed = char['creed']
            
            # If no creed provided, show current creed
            if creed is None:
                embed = discord.Embed(
                    title=f"{HeraldEmojis.CREED} {char['name']}'s Creed",
                    color=0x8B4513
                )
                
                if current_creed:
                    embed.description = f"**Current Creed:** {current_creed}"
                    embed.add_field(
                        name=f"{HeraldEmojis.INFO} About Creeds", 
                        value="Creeds define your Hunter's philosophy and approach to the supernatural. They provide moral guidance and special abilities.", 
                        inline=False
                    )
                else:
                    embed.description = "**No Creed set**"
                    embed.add_field(
                        name="Set a Creed", 
                        value="Use `/creed character:Name creed:\"Creed Name\"` to set your character's Creed.\n\nCommon Creeds: Innocent, Martyr, Redeemer, Visionary, Wayward", 
                        inline=False
                    )
                
                await interaction.response.send_message(embed=embed)
                
            else:
                # Set new creed
                # Clean up creed name (capitalize properly)
                creed = creed.strip().title()
                
                # Update database using actual character name
                conn = get_db_connection()
                conn.execute("""
                    UPDATE characters 
                    SET creed = ? 
                    WHERE user_id = ? AND name = ?
                """, (creed, user_id, char['name']))
                conn.commit()
                conn.close()
                
                # Create response
                embed = discord.Embed(
                    title=f"{HeraldEmojis.CREED} {char['name']}'s Creed Updated",
                    color=0x8B4513
                )
                
                if current_creed:
                    embed.description = f"**{current_creed}** → **{creed}**"
                    embed.add_field(
                        name=f"{HeraldEmojis.NEW} Creed Changed", 
                        value=f"Your character has embraced the **{creed}** Creed!", 
                        inline=False
                    )
                else:
                    embed.description = f"**Creed Set:** {creed}"
                    embed.add_field(
                        name=f"{HeraldEmojis.NEW} New Hunter", 
                        value=f"Your character has joined the **{creed}** Creed and begins their hunt!", 
                        inline=False
                    )
                
                await interaction.response.send_message(embed=embed)
                
        except Exception as e:
            self.logger.error(f"Error in creed command: {e}")
            await interaction.response.send_message(
                f"{HeraldEmojis.ERROR} An error occurred while managing Creed", 
                ephemeral=True
            )

    @app_commands.command(name="ambition", description="View or set your character's Ambition")
    @app_commands.describe(
        character="Character name",
        ambition="Long-term goal (leave empty to view current ambition)"
    )
    async def ambition(self, interaction: discord.Interaction, character: str, ambition: str = None):
        """Manage character Ambition (long-term goal that recovers aggravated willpower damage)"""
        
        user_id = str(interaction.user.id)
        
        try:
            # Use fuzzy character matching
            char = await find_character(user_id, character)
            
            if not char:
                error_msg = await HeraldMessages.character_not_found(user_id, character)
                await interaction.response.send_message(error_msg, ephemeral=True)
                return
            
            current_ambition = char['ambition']
            
            # If no ambition provided, show current ambition
            if ambition is None:
                embed = discord.Embed(
                    title=f"{HeraldEmojis.AMBITION} {char['name']}'s Ambition",
                    color=0xFFD700
                )
                
                if current_ambition:
                    embed.description = f"**Current Ambition:** {current_ambition}"
                    embed.add_field(
                        name=f"{HeraldEmojis.INFO} About Ambitions", 
                        value="Ambitions are long-term goals. When you actively work towards your Ambition during a session, you recover **one point of Aggravated Willpower damage** at the end of the session.", 
                        inline=False
                    )
                else:
                    embed.description = "**No Ambition set**"
                    embed.add_field(
                        name="Set an Ambition", 
                        value="Use `/ambition character:Name ambition:\"Your long-term goal\"` to set your character's Ambition.\n\nExamples: \"Destroy the vampire coven that killed my family\", \"Become the city's most feared supernatural hunter\", \"Find a cure for my cursed condition\"", 
                        inline=False
                    )
                
                await interaction.response.send_message(embed=embed)
                
            else:
                # Set new ambition
                if len(ambition) > 200:
                    await interaction.response.send_message(
                        f"{HeraldEmojis.ERROR} Ambition must be 200 characters or less", 
                        ephemeral=True
                    )
                    return
                
                # Update database using actual character name
                conn = get_db_connection()
                conn.execute("""
                    UPDATE characters 
                    SET ambition = ? 
                    WHERE user_id = ? AND name = ?
                """, (ambition, user_id, char['name']))
                conn.commit()
                conn.close()
                
                # Create response
                embed = discord.Embed(
                    title=f"{HeraldEmojis.AMBITION} {char['name']}'s Ambition Updated",
                    color=0xFFD700
                )
                
                if current_ambition:
                    embed.description = f"**Previous:** {current_ambition}\n**New:** {ambition}"
                    embed.add_field(
                        name=f"{HeraldEmojis.NEW} Ambition Changed", 
                        value="Your character's long-term goal has been updated!", 
                        inline=False
                    )
                else:
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
        character="Character name",
        desire="Short-term goal (leave empty to view current desire)"
    )
    async def desire(self, interaction: discord.Interaction, character: str, desire: str = None):
        """Manage character Desire (short-term goal that recovers superficial willpower damage)"""
        
        user_id = str(interaction.user.id)
        
        try:
            # Use fuzzy character matching
            char = await find_character(user_id, character)
            
            if not char:
                error_msg = await HeraldMessages.character_not_found(user_id, character)
                await interaction.response.send_message(error_msg, ephemeral=True)
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
                    embed.description = "**No Desire set**"
                    embed.add_field(
                        name="Set a Desire", 
                        value="Use `/desire character:Name desire:\"Your short-term goal\"` to set your character's Desire.\n\nExamples: \"Get information from the bartender\", \"Avoid getting noticed by the police\", \"Find a safe place to rest\"", 
                        inline=False
                    )
                
                await interaction.response.send_message(embed=embed)
                
            else:
                # Set new desire
                if len(desire) > 200:
                    await interaction.response.send_message(
                        f"{HeraldEmojis.ERROR} Desire must be 200 characters or less", 
                        ephemeral=True
                    )
                    return
                
                # Update database using actual character name
                conn = get_db_connection()
                conn.execute("""
                    UPDATE characters 
                    SET desire = ? 
                    WHERE user_id = ? AND name = ?
                """, (desire, user_id, char['name']))
                conn.commit()
                conn.close()
                
                # Create response
                embed = discord.Embed(
                    title=f"{HeraldEmojis.DESIRE} {char['name']}'s Desire Updated",
                    color=0x4169E1
                )
                
                if current_desire:
                    embed.description = f"**Previous:** {current_desire}\n**New:** {desire}"
                    embed.add_field(
                        name=f"{HeraldEmojis.NEW} Desire Changed", 
                        value="Your character's immediate goal has been updated!", 
                        inline=False
                    )
                else:
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
        character="Character name",
        drive="Why you hunt the supernatural (leave empty to view current)",
        redemption="How your Drive can be redeemed/healed from Despair"
    )
    async def drive(self, interaction: discord.Interaction, character: str, drive: str = None, redemption: str = None):
        """Manage character Drive (reason for hunting) and Redemption (healing from Despair)"""
        
        user_id = str(interaction.user.id)
        
        try:
            # Use fuzzy character matching
            char = await find_character(user_id, character)
            
            if not char:
                error_msg = await HeraldMessages.character_not_found(user_id, character)
                await interaction.response.send_message(error_msg, ephemeral=True)
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
                        embed.add_field(
                            name="Set Redemption", 
                            value="Use `/drive character:Name redemption:\"Method to heal from Despair\"` to set your Redemption path.", 
                            inline=False
                        )
                    
                    embed.add_field(
                        name=f"{HeraldEmojis.INFO} About Drive & Redemption", 
                        value="Drive represents your reason for hunting the supernatural. Redemption is the specific method that can heal you from Despair when you reach maximum Desperation.", 
                        inline=False
                    )
                else:
                    embed.description = "**No Drive set**"
                    embed.add_field(
                        name="Set a Drive", 
                        value="Use `/drive character:Name drive:\"Your reason for hunting\"` to set your character's Drive.\n\nExamples: \"Revenge against those who killed my family\", \"Protect the innocent from supernatural threats\", \"Prove that monsters are real\"", 
                        inline=False
                    )
                
                await interaction.response.send_message(embed=embed)
                
            else:
                # Set new drive and/or redemption
                if len(drive) > 200:
                    await interaction.response.send_message(
                        f"{HeraldEmojis.ERROR} Drive must be 200 characters or less", 
                        ephemeral=True
                    )
                    return
                
                if redemption and len(redemption) > 200:
                    await interaction.response.send_message(
                        f"{HeraldEmojis.ERROR} Redemption must be 200 characters or less", 
                        ephemeral=True
                    )
                    return
                
                # Update database using actual character name
                conn = get_db_connection()
                
                if redemption is not None:
                    # Update both drive and redemption
                    conn.execute("""
                        UPDATE characters 
                        SET drive = ?, redemption = ? 
                        WHERE user_id = ? AND name = ?
                    """, (drive, redemption, user_id, char['name']))
                else:
                    # Update only drive
                    conn.execute("""
                        UPDATE characters 
                        SET drive = ? 
                        WHERE user_id = ? AND name = ?
                    """, (drive, user_id, char['name']))
                
                conn.commit()
                conn.close()
                
                # Create response
                embed = discord.Embed(
                    title=f"{HeraldEmojis.DRIVE} {char['name']}'s Drive Updated",
                    color=0x8B0000
                )
                
                if current_drive:
                    embed.description = f"**Previous Drive:** {current_drive}\n**New Drive:** {drive}"
                else:
                    embed.description = f"**Drive Set:** {drive}"
                
                if redemption:
                    embed.add_field(
                        name=f"{HeraldEmojis.REDEMPTION} Redemption Set", 
                        value=redemption, 
                        inline=False
                    )
                
                embed.add_field(
                    name=f"{HeraldEmojis.NEW} Hunter's Purpose", 
                    value="Your character's motivation for hunting the supernatural has been established! This Drive will guide their actions and determine their path to Redemption.", 
                    inline=False
                )
                
                await interaction.response.send_message(embed=embed)
                
        except Exception as e:
            self.logger.error(f"Error in drive command: {e}")
            await interaction.response.send_message(
                f"{HeraldEmojis.ERROR} An error occurred while managing Drive", 
                ephemeral=True
            )

    # Integration methods for roll cog
    async def get_character_attribute(self, user_id: str, character_name: str, attribute: str) -> Optional[int]:
        """Get a specific attribute value for a character (for roll integration)"""
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            cur.execute(f"SELECT {attribute.lower()} FROM characters WHERE user_id = ? AND name = ?", (user_id, character_name))
            result = cur.fetchone()
            conn.close()
            
            return result[attribute.lower()] if result else None
        except Exception as e:
            logger.error(f"Error getting attribute {attribute}: {e}")
            return None

    async def get_character_skill(self, user_id: str, character_name: str, skill_name: str) -> Optional[int]:
        """Get a specific skill value for a character (for roll integration)"""
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            cur.execute("SELECT dots FROM skills WHERE user_id = ? AND character_name = ? AND skill_name = ?", 
                       (user_id, character_name, skill_name))
            result = cur.fetchone()
            conn.close()
            
            return result['dots'] if result else None
        except Exception as e:
            logger.error(f"Error getting skill {skill_name}: {e}")
            return None

    # Autocomplete functions for character names
    @apply_damage.autocomplete('character')
    @heal_damage.autocomplete('character')
    @edge.autocomplete('character')
    @desperation.autocomplete('character')
    @creed.autocomplete('character')
    @ambition.autocomplete('character')
    @desire.autocomplete('character')
    @drive.autocomplete('character')
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
    
    # Only register guild commands if GUILD_ID is set (development mode)
    if GUILD_ID:
        for command in cog.get_app_commands():
            bot.tree.add_command(command, guild=discord.Object(id=GUILD_ID))
        logger.info(f"Character Gameplay cog loaded with {len(cog.get_app_commands())} guild commands")
    else:
        logger.info(f"Character Gameplay cog loaded with {len(cog.get_app_commands())} global commands")
