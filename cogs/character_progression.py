"""
Character Progression Cog for Herald Bot
Handles character development: XP, skills, specialties, templates, help
"""

import discord
from discord import app_commands
from discord.ext import commands
from typing import List
import logging

from core.db import get_async_db
from core.character_utils import find_character, character_autocomplete, ALL_SKILLS, resolve_character, get_active_character
from core.ui_utils import HeraldColors, HeraldMessages
from config.settings import GUILD_ID

logger = logging.getLogger('Herald.Character.Progression')


# ===== VIEW CLASSES =====

class SkillTemplateView(discord.ui.View):
    """Confirmation view for applying skill templates"""
    
    def __init__(self, user_id: str, character_name: str, template: str, template_info: dict, timeout: float = 30):
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.character_name = character_name
        self.template = template
        self.template_info = template_info
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Ensure only the original user can interact"""
        return str(interaction.user.id) == self.user_id
    
    @discord.ui.button(label="Apply Template", style=discord.ButtonStyle.danger, emoji="📋")
    async def confirm_apply(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Confirm and apply skill template"""
        try:
            async with get_async_db() as conn:
                # First, reset all skills to 0
                await conn.execute("""
                    UPDATE skills 
                    SET dots = 0 
                    WHERE user_id = $1 AND character_name = $2
                """, self.user_id, self.character_name)
                
                # Apply template distribution
                skills_to_set = []
                skill_index = 0
                
                # Distribute skills according to template
                for dots_str, count in self.template_info['distribution'].items():
                    dots = int(dots_str)
                    if dots > 0:  # Skip 0-dot entries
                        for _ in range(count):
                            if skill_index < len(ALL_SKILLS):
                                skills_to_set.append((ALL_SKILLS[skill_index], dots))
                                skill_index += 1
                
                # Update database with new skill values
                for skill_name, dots in skills_to_set:
                    await conn.execute("""
                        UPDATE skills 
                        SET dots = $1
                        WHERE user_id = $2 AND character_name = $3 AND skill_name = $4
                    """, dots, self.user_id, self.character_name, skill_name)
            
            # Success response
            embed = discord.Embed(
                title="✅ Skill Template Applied",
                description=f"**{self.character_name}** now uses the **{self.template.title()}** template",
                color=0x228B22
            )
            
            embed.add_field(
                name="📊 Skill Distribution",
                value=self.template_info['description'],
                inline=False
            )
            
            embed.add_field(
                name="🎯 Next Steps",
                value="Use `/skill_set` to customize specific skills or use `/sheet` to view your character.",
                inline=False
            )
            
            # Disable all buttons
            for item in self.children:
                item.disabled = True
            
            await interaction.response.edit_message(embed=embed, view=self)
            logger.info(f"Applied {self.template} template to '{self.character_name}' for user {self.user_id}")
            
        except Exception as e:
            logger.error(f"Error applying skill template: {e}")
            await interaction.response.send_message(
                f"❌ Error applying template: {str(e)}", ephemeral=True
            )
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel_apply(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel template application"""
        embed = discord.Embed(
            title="❌ Template Cancelled",
            description=f"**{self.character_name}**'s skills were not changed",
            color=0x4169E1
        )
        
        # Disable all buttons
        for item in self.children:
            item.disabled = True
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def on_timeout(self):
        """Handle timeout"""
        for item in self.children:
            item.disabled = True


# ===== MAIN COG CLASS =====

class CharacterProgression(commands.Cog):
    """Character Progression - Skills, XP, specialties, and help"""
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger('Herald.Character.Progression')

    # ===== SKILL COMMANDS =====

    @app_commands.command(name="skill_set", description="Set dots for a skill on your character")
    @app_commands.describe(
        skill="Skill to update",
        dots="Skill rating (0-5)"
    )
    @app_commands.choices(skill=[
        app_commands.Choice(name=skill, value=skill)
        for skill in ALL_SKILLS[:25]  # Discord limit
    ])
    async def skill_set(
        self,
        interaction: discord.Interaction,
        skill: str,
        dots: int
    ):
        """Set skill dots for a character"""
        user_id = str(interaction.user.id)
        dots = max(0, min(dots, 5))  # Clamp to valid range

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
                    f"{HeraldEmojis.ERROR} Active character '{active_char_name}' not found.",
                    ephemeral=True
                )
                return

            async with get_async_db() as conn:
                # Update skill
                await conn.execute("""
                    UPDATE skills
                    SET dots = $1
                    WHERE user_id = $2 AND character_name = $3 AND skill_name = $4
                """, dots, user_id, char['name'], skill)

            # Response
            embed = discord.Embed(
                title="✅ Skill Updated",
                description=f"**{char['name']}** • {skill}: {'●' * dots}{'○' * (5 - dots)} ({dots}/5)",
                color=0x228B22
            )
            
            await interaction.response.send_message(embed=embed)
            logger.info(f"Set {skill} to {dots} dots for {char['name']} (user {user_id})")

        except Exception as e:
            logger.error(f"Error in skill_set command: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while updating the skill", 
                ephemeral=True
            )

    # ===== SPECIALTY COMMANDS =====

    @app_commands.command(name="specialty", description="Manage skill specialties")
    @app_commands.describe(
        action="What to do with specialty",
        skill="Skill name (for add/remove actions)",
        specialty="Specialty name (for add/remove actions)"    )
    @app_commands.choices(action=[
        app_commands.Choice(name="View All", value="view"),
        app_commands.Choice(name="Add", value="add"),
        app_commands.Choice(name="Remove", value="remove")
    ])
    async def specialty(
        self,
        interaction: discord.Interaction,
        action: str,
        skill: str = None,
        specialty: str = None
    ):
        """Manage character skill specialties"""
        user_id = str(interaction.user.id)

        try:
            # Get active character
            active_char_name = await get_active_character(user_id)
            if not active_char_name:
                await interaction.response.send_message(
                    f"❌ No active character set. Use `/character` to set your active character.",
                    ephemeral=True
                )
                return

            char = await find_character(user_id, active_char_name)
            if not char:
                await interaction.response.send_message(
                    f"❌ Could not find your active character.",
                    ephemeral=True
                )
                return
            
            if action == "view":
                # View all specialties
                async with get_async_db() as conn:
                    specialties = await conn.fetch("""
                        SELECT skill_name, specialty_name 
                        FROM specialties 
                        WHERE user_id = $1 AND character_name = $2
                        ORDER BY skill_name, specialty_name
                    """, user_id, char['name'])
                
                if not specialties:
                    await interaction.response.send_message(
                        f"**{char['name']}** has no specialties yet. Use `/specialty character:Name action:add skill:SkillName specialty:\"Specialty Name\"` to add one!",
                        ephemeral=True
                    )
                    return
                
                embed = discord.Embed(
                    title=f"🎯 {char['name']}'s Specialties",
                    color=0x4169E1
                )
                
                # Group by skill
                from collections import defaultdict
                skills_dict = defaultdict(list)
                for spec in specialties:
                    skills_dict[spec['skill_name']].append(spec['specialty_name'])
                
                for skill_name, spec_list in sorted(skills_dict.items()):
                    embed.add_field(
                        name=f"**{skill_name}**",
                        value='\n'.join([f"• {spec}" for spec in spec_list]),
                        inline=False
                    )
                
                await interaction.response.send_message(embed=embed)
                return
            
            # Add or remove require skill and specialty
            if not skill or not specialty:
                await interaction.response.send_message(
                    f"❌ Please specify both skill and specialty for {action} action",
                    ephemeral=True
                )
                return
            
            async with get_async_db() as conn:
                if action == "add":
                    # Check if skill has dots
                    skill_check = await conn.fetchrow("""
                        SELECT dots 
                        FROM skills 
                        WHERE user_id = $1 AND character_name = $2 AND skill_name = $3
                    """, user_id, char['name'], skill)
                    
                    if not skill_check or skill_check['dots'] == 0:
                        await interaction.response.send_message(
                            f"❌ **{skill}** must have at least 1 dot to add a specialty",
                            ephemeral=True
                        )
                        return
                    
                    skill_dots = skill_check['dots']
                    
                    # Check specialty limit (max = skill dots, minimum 1)
                    max_specialties = max(1, skill_dots)
                    
                    current_count = await conn.fetchval("""
                        SELECT COUNT(*) 
                        FROM specialties 
                        WHERE user_id = $1 AND character_name = $2 AND skill_name = $3
                    """, user_id, char['name'], skill)
                    
                    if current_count >= max_specialties:
                        await interaction.response.send_message(
                            f"❌ **{skill}** already has the maximum number of specialties ({max_specialties})",
                            ephemeral=True
                        )
                        return
                    
                    # Add specialty
                    try:
                        await conn.execute("""
                            INSERT INTO specialties (user_id, character_name, skill_name, specialty_name)
                            VALUES ($1, $2, $3, $4)
                        """, user_id, char['name'], skill, specialty)
                        
                        embed = discord.Embed(
                            title="✅ Specialty Added",
                            description=f"**{char['name']}** gained a specialty",
                            color=0x228B22
                        )
                        
                        embed.add_field(
                            name=f"🎯 {skill}",
                            value=f"• {specialty}",
                            inline=False
                        )
                        
                        await interaction.response.send_message(embed=embed)
                        logger.info(f"Added specialty '{specialty}' to {skill} for {char['name']} (user {user_id})")
                        
                    except Exception as e:
                        if "UNIQUE constraint" in str(e) or "duplicate" in str(e).lower():
                            await interaction.response.send_message(
                                f"❌ **{char['name']}** already has the **{specialty}** specialty for **{skill}**",
                                ephemeral=True
                            )
                        else:
                            raise
                
                elif action == "remove":
                    # Remove specialty
                    result = await conn.execute("""
                        DELETE FROM specialties 
                        WHERE user_id = $1 AND character_name = $2 AND skill_name = $3 AND specialty_name = $4
                    """, user_id, char['name'], skill, specialty)
                    
                    # Check if anything was deleted (PostgreSQL specific)
                    if result == "DELETE 0":
                        await interaction.response.send_message(
                            f"❌ Specialty **{specialty}** not found for **{skill}**",
                            ephemeral=True
                        )
                        return
                    
                    embed = discord.Embed(
                        title="🗑️ Specialty Removed",
                        description=f"**{char['name']}** lost a specialty",
                        color=0xFF4500
                    )
                    
                    embed.add_field(
                        name=f"🎯 {skill}",
                        value=f"Removed: {specialty}",
                        inline=False
                    )
                    
                    await interaction.response.send_message(embed=embed)
                    logger.info(f"Removed specialty '{specialty}' from {skill} for {char['name']} (user {user_id})")
            
        except Exception as e:
            logger.error(f"Error in specialty command: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while managing specialties",
                ephemeral=True
            )

    # ===== EXPERIENCE POINT COMMANDS =====

    @app_commands.command(name="xp", description="View or manage your character's experience points")
    @app_commands.describe(
        action="What to do with experience points",
        amount="Amount of XP to add/subtract/set (optional for 'view')",
        reason="Reason for XP change (optional)"    )
    @app_commands.choices(action=[
        app_commands.Choice(name="View", value="view"),
        app_commands.Choice(name="Add", value="add"),
        app_commands.Choice(name="Spend", value="spend"),
        app_commands.Choice(name="Set", value="set")
    ])
    async def experience_points(
        self,
        interaction: discord.Interaction,
        action: str,
        amount: int = None,
        reason: str = None
    ):
        """Manage character experience points"""
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
                    f"{HeraldEmojis.ERROR} Active character '{active_char_name}' not found.",
                    ephemeral=True
                )
                return
            
            # Get current XP
            async with get_async_db() as conn:
                char_with_xp = await conn.fetchrow(
                    "SELECT * FROM characters WHERE user_id = $1 AND name = $2", 
                    user_id, char['name']
                )
            
            current_total = char_with_xp['experience_total'] or 0
            current_spent = char_with_xp['experience_spent'] or 0
            current_available = current_total - current_spent
            
            if action == "view":
                # Display XP status
                embed = discord.Embed(
                    title=f"⭐ {char['name']}'s Experience Points",
                    color=0xFFD700
                )
                
                embed.add_field(
                    name="📊 Experience Summary",
                    value=(
                        f"**Total Earned:** {current_total} XP\n"
                        f"**Spent:** {current_spent} XP\n"
                        f"**Available:** {current_available} XP"
                    ),
                    inline=False
                )
                
                # Add spending guide
                embed.add_field(
                    name="💡 Spending Guide",
                    value=(
                        "**Attributes:** New rating × 4 XP\n"
                        "**Skills:** New rating × 2 XP\n"
                        "**Specialties:** 3 XP each\n"
                        "**Edges:** Varies by type"
                    ),
                    inline=False
                )
                
                # Show recent XP history if any
                async with get_async_db() as conn:
                    recent_xp = await conn.fetch("""
                        SELECT action, amount, reason, created_at 
                        FROM xp_log 
                        WHERE user_id = $1 AND character_name = $2 
                        ORDER BY created_at DESC 
                        LIMIT 3
                    """, user_id, char['name'])
                
                if recent_xp:
                    history_text = []
                    for entry in recent_xp:
                        reason_text = f" - {entry['reason']}" if entry['reason'] else ""
                        history_text.append(f"• {entry['action']}: {entry['amount']:+d} XP{reason_text}")
                    
                    embed.add_field(
                        name="📜 Recent History",
                        value='\n'.join(history_text),
                        inline=False
                    )
                
                await interaction.response.send_message(embed=embed)
                return
            
            # For add/subtract/set, amount is required
            if amount is None:
                await interaction.response.send_message(
                    f"❌ Please specify an amount for {action} action",
                    ephemeral=True
                )
                return
            
            # Calculate new total based on action
            async with get_async_db() as conn:
                if action == "add":
                    new_total = current_total + amount
                    new_spent = current_spent
                    action_text = f"Gained {amount} XP"
                elif action == "spend":
                    # Spending decreases available XP by increasing spent amount
                    if amount > current_available:
                        await interaction.response.send_message(
                            f"❌ Not enough XP. Available: {current_available}, Trying to spend: {amount}",
                            ephemeral=True
                        )
                        return
                    new_spent = current_spent + amount
                    new_total = current_total
                    action_text = f"Spent {amount} XP"
                else:  # set
                    new_total = max(current_spent, amount)
                    new_spent = current_spent
                    action_text = f"Set total to {amount} XP"

                new_available = new_total - new_spent
                
                # Update database
                await conn.execute("""
                    UPDATE characters 
                    SET experience_total = $1, experience_spent = $2
                    WHERE user_id = $3 AND name = $4
                """, new_total, new_spent, user_id, char['name'])
                
                # Log the change
                await conn.execute("""
                    INSERT INTO xp_log (user_id, character_name, action, amount, reason)
                    VALUES ($1, $2, $3, $4, $5)
                """, user_id, char['name'], action_text, amount, reason)
                
                # Create response
                embed = discord.Embed(
                    title=f"⭐ {char['name']}'s Experience Updated",
                    description=action_text,
                    color=0xFFD700
                )
                
                if reason:
                    embed.add_field(name="📝 Reason", value=reason, inline=False)
                
                embed.add_field(
                    name="📊 New Experience Status",
                    value=(
                        f"**Total Earned:** {new_total} XP\n"
                        f"**Spent:** {new_spent} XP\n"
                        f"**Available:** {new_available} XP"
                    ),
                    inline=False
                )
                
                # Add contextual messages
                if action == "add" and amount >= 5:
                    embed.add_field(
                        name="🎉 Significant Progress!",
                        value="You've earned enough XP to improve an attribute or several skills!",
                        inline=False
                    )
                elif action == "subtract":
                    embed.add_field(
                        name="💸 XP Spent",
                        value="Don't forget to update your character sheet with improvements!",
                        inline=False
                    )
                
                await interaction.response.send_message(embed=embed)
                logger.info(f"XP {action}: {char['name']} - {amount} XP ({reason or 'no reason'}) for user {user_id}")
                
        except Exception as e:
            logger.error(f"Error in XP command: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while managing experience points",
                ephemeral=True
            )

    # ===== HELP COMMAND =====

    @app_commands.command(name="help", description="Get help with Herald bot commands")
    @app_commands.describe(topic="Help topic to view")
    @app_commands.choices(topic=[
        app_commands.Choice(name="Getting Started", value="start"),
        app_commands.Choice(name="Character Creation", value="creation"),
        app_commands.Choice(name="Character Management", value="management"),
        app_commands.Choice(name="Dice Rolling", value="rolling"),
        app_commands.Choice(name="Experience Points", value="xp"),
        app_commands.Choice(name="Hunter Mechanics", value="mechanics"),
        app_commands.Choice(name="Equipment & Notes", value="extras"),
        app_commands.Choice(name="All Commands", value="commands")
    ])
    async def help_command(self, interaction: discord.Interaction, topic: str = "start"):
        """Display help information"""
        
        if topic == "start":
            embed = discord.Embed(
                title="🔸 Herald Protocol",
                description=f"{HeraldMessages.QUERY_RECOGNIZED}: Assistance requested\n\nHerald is your assistant for Hunter: The Reckoning 5th Edition gameplay!",
                color=HeraldColors.ORANGE
            )

            embed.add_field(
                name="🔸 Operations available",
                value=(
                    "1. Create a character: `/create`\n"
                    "2. View character sheet: `/sheet`\n"
                    "3. Roll dice: `/roll` or `/roll_char`\n"
                    "4. Manage character: Use various commands"
                ),
                inline=False
            )

            embed.add_field(
                name="🎯 Help Topics",
                value=(
                    "Use `/help topic:TopicName` for detailed help:\n"
                    "• **Character Creation** - Making characters\n"
                    "• **Character Management** - Editing & organizing\n"
                    "• **Dice Rolling** - H5E dice mechanics\n"
                    "• **Experience Points** - XP tracking & spending\n"
                    "• **Hunter Mechanics** - Edge, Desperation, etc.\n"
                    "• **Equipment & Notes** - Character extras\n"
                    "• **All Commands** - Complete command list"
                ),
                inline=False
            )

            embed.set_footer(text=HeraldMessages.CATCHPHRASE)
            
        elif topic == "commands":
            embed = discord.Embed(
                title="📜 All Commands Reference",
                color=0x4169E1
            )
            
            embed.add_field(
                name="🏗️ Character Creation & Management",
                value=(
                    "`/create` - Create new character\n"
                    "`/delete` - Delete character (with confirmation)\n"
                    "`/rename` - Rename character\n"
                    "`/characters` - List your characters\n"
                    "`/sheet` - View character sheet"
                ),
                inline=False
            )
            
            embed.add_field(
                name="🎯 Character Development",
                value=(
                    "`/skill_set` - Set skill dots\n"
                    "`/skill_template` - Apply H5E skill templates\n"
                    "`/specialty` - Manage skill specialties\n"
                    "`/xp` - Manage experience points\n"
                    "`/spend_xp` - Spend XP for improvements\n"
                    "`/xp_log` - View XP transaction history"
                ),
                inline=False
            )
            
            embed.add_field(
                name="🏹 Hunter Mechanics",
                value=(
                    "`/edge` - Manage Edge rating\n"
                    "`/desperation` - Manage Desperation level\n"
                    "`/creed` - Set/view character Creed\n"
                    "`/damage` - Apply damage\n"
                    "`/heal` - Heal damage"
                ),
                inline=False
            )
        
        else:
            # Other topics use simplified version
            embed = discord.Embed(
                title="🏹 Herald Help",
                description=f"Help for: {topic}",
                color=0x4169E1
            )
            embed.add_field(
                name="More Topics",
                value="Use `/help topic:commands` to see all available commands",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    """Setup function for the Character Progression cog"""
    cog = CharacterProgression(bot)
    await bot.add_cog(cog)
    logger.info(f"Character Progression cog loaded with {len(cog.get_app_commands())} commands")
