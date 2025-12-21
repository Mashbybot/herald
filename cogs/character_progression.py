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
        dots="Skill rating (0-5)",
        character_name="Character name (optional - uses active character if not specified)"
    )
    @app_commands.choices(skill=[
        app_commands.Choice(name=skill, value=skill)
        for skill in ALL_SKILLS[:25]  # Discord limit
    ])
    @app_commands.autocomplete(character_name=character_autocomplete)
    async def skill_set(
        self,
        interaction: discord.Interaction,
        skill: str,
        dots: int,
        character_name: str = None
    ):
        """Set skill dots for a character"""
        user_id = str(interaction.user.id)
        dots = max(0, min(dots, 5))  # Clamp to valid range

        try:
            char = await resolve_character(user_id, character_name)

            if not char:
                await interaction.response.send_message(
                    f"❌ No character specified and no active character set. Use `/character` to set your active character.",
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

    @app_commands.command(name="skill_template", description="Apply a pre-made skill distribution template")
    @app_commands.describe(
        template="Skill distribution template to apply"    )
    @app_commands.choices(template=[
        app_commands.Choice(name="Balanced (Jack of All Trades)", value="balanced"),
        app_commands.Choice(name="Specialized (Expert Focus)", value="specialized"),
        app_commands.Choice(name="Generalist (Broad Knowledge)", value="generalist")
    ])
    async def skill_template(self, interaction: discord.Interaction, template: str):
        """Apply a skill distribution template"""
        user_id = str(interaction.user.id)
        
        # Template definitions
        TEMPLATES = {
            "balanced": {
                "name": "Balanced",
                "description": "9 skills at 3 dots, 9 at 2 dots, 9 at 1 dot",
                "distribution": {"3": 9, "2": 9, "1": 9, "0": 0}
            },
            "specialized": {
                "name": "Specialized",
                "description": "3 skills at 4 dots, 6 at 3 dots, 6 at 2 dots, 12 at 1 dot",
                "distribution": {"4": 3, "3": 6, "2": 6, "1": 12, "0": 0}
            },
            "generalist": {
                "name": "Generalist",
                "description": "18 skills at 2 dots, 9 at 1 dot",
                "distribution": {"2": 18, "1": 9, "0": 0}
            }
        }
        
        template_info = TEMPLATES.get(template)
        if not template_info:
            await interaction.response.send_message("❌ Invalid template", ephemeral=True)
            return

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

            # Create confirmation view
            embed = discord.Embed(
                title=f"📋 Apply {template_info['name']} Template?",
                description=f"This will reset all skills for **{char['name']}** and apply the following distribution:",
                color=0xFF4500
            )
            
            embed.add_field(
                name="📊 Skill Distribution",
                value=template_info['description'],
                inline=False
            )
            
            embed.add_field(
                name="⚠️ Warning",
                value="This will **overwrite** all current skill dots. This action cannot be undone!",
                inline=False
            )
            
            view = SkillTemplateView(user_id, char['name'], template, template_info)
            await interaction.response.send_message(embed=embed, view=view)
            
        except Exception as e:
            logger.error(f"Error in skill_template command: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while preparing the template", 
                ephemeral=True
            )

    @app_commands.command(name="skill_bulk", description="Set multiple skills at once")
    @app_commands.describe(
        skill_list="Comma-separated skill:dots pairs (e.g., 'Athletics:3,Stealth:2,Investigation:4')"    )
    async def skill_bulk(self, interaction: discord.Interaction, skill_list: str):
        """Bulk set multiple skills"""
        user_id = str(interaction.user.id)
        
        try:
            # Parse skill updates
            skill_updates = []
            for pair in skill_list.split(','):
                pair = pair.strip()
                if ':' not in pair:
                    continue
                skill_name, dots_str = pair.split(':', 1)
                skill_name = skill_name.strip()
                try:
                    dots = int(dots_str.strip())
                    dots = max(0, min(dots, 5))
                    skill_updates.append((skill_name, dots))
                except ValueError:
                    continue
            
            if not skill_updates:
                await interaction.response.send_message(
                    "❌ Invalid format. Use: 'Skill1:dots,Skill2:dots' (e.g., 'Athletics:3,Stealth:2')",
                    ephemeral=True
                )
                return

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

            async with get_async_db() as conn:
                # Validate all skills exist and update them
                updated_skills = []
                errors = []
                
                for skill_name, dots in skill_updates:
                    # Check if skill exists
                    skill_check = await conn.fetchrow("""
                        SELECT skill_name 
                        FROM skills 
                        WHERE user_id = $1 AND character_name = $2 AND skill_name = $3
                    """, user_id, char['name'], skill_name)
                    
                    if not skill_check:
                        errors.append(f"**{skill_name}** not found")
                        continue
                    
                    # Update skill
                    await conn.execute("""
                        UPDATE skills 
                        SET dots = $1
                        WHERE user_id = $2 AND character_name = $3 AND skill_name = $4
                    """, dots, user_id, char['name'], skill_name)
                    
                    updated_skills.append((skill_name, dots))
            
            # Create response
            embed = discord.Embed(
                title="✅ Skills Updated",
                description=f"Updated {len(updated_skills)} skills for **{char['name']}**",
                color=0x228B22
            )
            
            if updated_skills:
                skills_text = '\n'.join([
                    f"**{skill}**: {'●' * dots}{'○' * (5 - dots)} ({dots}/5)"
                    for skill, dots in updated_skills
                ])
                
                # Split into chunks if too long
                if len(skills_text) > 1024:
                    chunks = [skills_text[i:i+1024] for i in range(0, len(skills_text), 1024)]
                    for i, chunk in enumerate(chunks):
                        field_name = "Updated Skills" if i == 0 else f"Updated Skills (cont. {i+1})"
                        embed.add_field(name=field_name, value=chunk, inline=False)
                else:
                    embed.add_field(name="Updated Skills", value=skills_text, inline=False)
            
            if errors:
                embed.add_field(
                    name="⚠️ Errors",
                    value='\n'.join(errors),
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed)
            logger.info(f"Bulk updated {len(updated_skills)} skills for {char['name']} (user {user_id})")
            
        except Exception as e:
            logger.error(f"Error in skill_bulk command: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while updating skills", 
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

    @app_commands.command(name="specialty_bulk", description="Add multiple specialties at once")
    @app_commands.describe(
        specialty_list="Comma-separated skill:specialty pairs (e.g., 'Athletics:Running,Firearms:Pistols')"    )
    async def specialty_bulk(self, interaction: discord.Interaction, specialty_list: str):
        """Bulk add multiple specialties"""
        user_id = str(interaction.user.id)

        try:
            # Parse specialty updates
            specialty_updates = []
            for pair in specialty_list.split(','):
                pair = pair.strip()
                if ':' not in pair:
                    continue
                skill_name, specialty_name = pair.split(':', 1)
                skill_name = skill_name.strip()
                specialty_name = specialty_name.strip()
                if skill_name and specialty_name:
                    specialty_updates.append((skill_name, specialty_name))

            if not specialty_updates:
                await interaction.response.send_message(
                    "❌ Invalid format. Use: 'Skill1:Specialty1,Skill2:Specialty2' (e.g., 'Athletics:Running,Firearms:Pistols')",
                    ephemeral=True
                )
                return

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
            
            async with get_async_db() as conn:
                # Validate all skills have dots and check limits
                errors = []
                added_specialties = []
                
                for skill_name, specialty_name in specialty_updates:
                    # Check skill dots
                    skill_data = await conn.fetchrow("""
                        SELECT dots 
                        FROM skills 
                        WHERE user_id = $1 AND character_name = $2 AND skill_name = $3
                    """, user_id, char['name'], skill_name)
                    
                    if not skill_data or skill_data['dots'] == 0:
                        errors.append(f"**{skill_name}** has 0 dots")
                        continue
                    
                    skill_dots = skill_data['dots']
                    
                    # Check current specialty count
                    current_count = await conn.fetchval("""
                        SELECT COUNT(*) 
                        FROM specialties 
                        WHERE user_id = $1 AND character_name = $2 AND skill_name = $3
                    """, user_id, char['name'], skill_name)
                    
                    max_specialties = max(1, skill_dots)
                    
                    if current_count >= max_specialties:
                        errors.append(f"**{skill_name}** already has maximum specialties ({max_specialties})")
                        continue
                    
                    # Check for duplicate
                    exists = await conn.fetchval("""
                        SELECT id 
                        FROM specialties 
                        WHERE user_id = $1 AND character_name = $2 AND skill_name = $3 AND specialty_name = $4
                    """, user_id, char['name'], skill_name, specialty_name)
                    
                    if exists:
                        errors.append(f"**{skill_name}**: {specialty_name} already exists")
                        continue
                    
                    # Add specialty
                    try:
                        await conn.execute("""
                            INSERT INTO specialties (user_id, character_name, skill_name, specialty_name)
                            VALUES ($1, $2, $3, $4)
                        """, user_id, char['name'], skill_name, specialty_name)
                        added_specialties.append((skill_name, specialty_name))
                    except Exception as e:
                        errors.append(f"**{skill_name}**: {specialty_name} - {str(e)[:50]}")
            
            # Create response
            embed = discord.Embed(
                title="🎯 Bulk Specialty Addition",
                description=f"Processed {len(added_specialties)} specialties for **{char['name']}**",
                color=0x228B22 if added_specialties else 0xFF4500
            )
            
            if added_specialties:
                # Group by skill
                from collections import defaultdict
                skills_dict = defaultdict(list)
                for skill_name, specialty_name in added_specialties:
                    skills_dict[skill_name].append(specialty_name)
                
                specs_text = []
                for skill_name, spec_list in sorted(skills_dict.items()):
                    specs_text.append(f"**{skill_name}**")
                    for spec in spec_list:
                        specs_text.append(f"  • {spec}")
                
                # Split into chunks if needed
                specs_str = '\n'.join(specs_text)
                if len(specs_str) > 1024:
                    chunks = [specs_text[i:i+20] for i in range(0, len(specs_text), 20)]
                    for i, chunk in enumerate(chunks):
                        field_name = "Added Specialties" if i == 0 else f"Added Specialties (cont. {i+1})"
                        embed.add_field(name=field_name, value="\n".join(chunk), inline=False)
                else:
                    embed.add_field(name="Added Specialties", value=specs_str, inline=False)
            
            if errors:
                errors_str = '\n'.join(errors[:10])  # Limit to 10 errors
                embed.add_field(name="⚠️ Errors", value=errors_str, inline=False)
                if len(errors) > 10:
                    embed.add_field(name="", value=f"...and {len(errors) - 10} more errors", inline=False)
            
            embed.set_footer(text=f"Added {len(added_specialties)} specialties")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            logger.info(f"Bulk added {len(added_specialties)} specialties for {char['name']} (user {user_id})")
            
        except Exception as e:
            logger.error(f"Error in specialty_bulk command: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while adding specialties",
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
        app_commands.Choice(name="Subtract", value="subtract"),
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
                    action_text = f"Gained {amount} XP"
                elif action == "subtract":
                    new_total = max(current_spent, current_total - amount)
                    action_text = f"Lost {amount} XP"
                else:  # set
                    new_total = max(current_spent, amount)
                    action_text = f"Set total to {amount} XP"
                
                new_spent = current_spent
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

    @app_commands.command(name="spend_xp", description="Spend XP to improve attributes or skills")
    @app_commands.describe(
        improvement_type="What to improve",
        target="Attribute or skill name",
        new_rating="New rating (current rating + 1)"    )
    @app_commands.choices(
        improvement_type=[
            app_commands.Choice(name="Attribute", value="attribute"),
            app_commands.Choice(name="Skill", value="skill")
        ]
    )
    async def spend_xp(
        self,
        interaction: discord.Interaction,
        improvement_type: str,
        target: str,
        new_rating: int
    ):
        """Spend XP to improve character abilities"""
        user_id = str(interaction.user.id)

        if new_rating < 1 or new_rating > 5:
            await interaction.response.send_message(
                "❌ Ratings must be between 1 and 5",
                ephemeral=True
            )
            return

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
            
            async with get_async_db() as conn:
                # Get current XP
                xp_data = await conn.fetchrow(
                    "SELECT experience_total, experience_spent FROM characters WHERE user_id = $1 AND name = $2", 
                    user_id, char['name']
                )
                
                if not xp_data:
                    await interaction.response.send_message(
                        "❌ XP data not found. Use `/xp` command first.", 
                        ephemeral=True
                    )
                    return
                
                current_total = xp_data['experience_total'] or 0
                current_spent = xp_data['experience_spent'] or 0
                available_xp = current_total - current_spent
                
                if improvement_type == "attribute":
                    # Check if attribute exists and get current value
                    target_lower = target.lower()
                    if target_lower not in ['strength', 'dexterity', 'stamina', 'charisma', 'manipulation', 'composure', 'intelligence', 'wits', 'resolve']:
                        await interaction.response.send_message(
                            f"❌ **{target}** is not a valid attribute", 
                            ephemeral=True
                        )
                        return
                    
                    char_data = await conn.fetchrow(
                        f"SELECT {target_lower}, resolve, composure FROM characters WHERE user_id = $1 AND name = $2", 
                        user_id, char['name']
                    )
                    current_rating = char_data[target_lower]
                    
                    if new_rating != current_rating + 1:
                        await interaction.response.send_message(
                            f"❌ Can only increase {target} from {current_rating} to {current_rating + 1}", 
                            ephemeral=True
                        )
                        return
                    
                    # Calculate cost (new rating × 4)
                    xp_cost = new_rating * 4
                    
                    if available_xp < xp_cost:
                        await interaction.response.send_message(
                            f"❌ Need {xp_cost} XP to raise {target} to {new_rating}. You have {available_xp} XP available.", 
                            ephemeral=True
                        )
                        return
                    
                    # Apply improvement
                    await conn.execute(f"""
                        UPDATE characters 
                        SET {target_lower} = $1, experience_spent = experience_spent + $2
                        WHERE user_id = $3 AND name = $4
                    """, new_rating, xp_cost, user_id, char['name'])
                    
                    # Update derived stats if needed
                    if target_lower == 'stamina':
                        new_health = new_rating + 3
                        await conn.execute(
                            "UPDATE characters SET health = $1 WHERE user_id = $2 AND name = $3", 
                            new_health, user_id, char['name']
                        )
                    elif target_lower in ['resolve', 'composure']:
                        # Recalculate willpower
                        updated_char = await conn.fetchrow(
                            "SELECT resolve, composure FROM characters WHERE user_id = $1 AND name = $2", 
                            user_id, char['name']
                        )
                        new_willpower = updated_char['resolve'] + updated_char['composure']
                        await conn.execute(
                            "UPDATE characters SET willpower = $1 WHERE user_id = $2 AND name = $3", 
                            new_willpower, user_id, char['name']
                        )
                    
                    improvement_text = f"{target} {current_rating} → {new_rating}"
                    
                else:  # skill
                    # Check if skill exists and get current value
                    skill_data = await conn.fetchrow(
                        "SELECT dots FROM skills WHERE user_id = $1 AND character_name = $2 AND skill_name = $3", 
                        user_id, char['name'], target
                    )
                    
                    if not skill_data:
                        await interaction.response.send_message(
                            f"❌ Skill **{target}** not found", 
                            ephemeral=True
                        )
                        return
                    
                    current_rating = skill_data['dots']
                    
                    if new_rating != current_rating + 1:
                        await interaction.response.send_message(
                            f"❌ Can only increase {target} from {current_rating} to {current_rating + 1}", 
                            ephemeral=True
                        )
                        return
                    
                    # Calculate cost (new rating × 2)
                    xp_cost = new_rating * 2
                    
                    if available_xp < xp_cost:
                        await interaction.response.send_message(
                            f"❌ Need {xp_cost} XP to raise {target} to {new_rating}. You have {available_xp} XP available.", 
                            ephemeral=True
                        )
                        return
                    
                    # Apply improvement
                    await conn.execute("""
                        UPDATE skills 
                        SET dots = $1
                        WHERE user_id = $2 AND character_name = $3 AND skill_name = $4
                    """, new_rating, user_id, char['name'], target)
                    
                    await conn.execute("""
                        UPDATE characters 
                        SET experience_spent = experience_spent + $1
                        WHERE user_id = $2 AND name = $3
                    """, xp_cost, user_id, char['name'])
                    
                    improvement_text = f"{target} {current_rating} → {new_rating}"
                
                # Log the expenditure
                await conn.execute("""
                    INSERT INTO xp_log (user_id, character_name, action, amount, reason)
                    VALUES ($1, $2, $3, $4, $5)
                """, user_id, char['name'], f"Spent {xp_cost} XP", xp_cost, improvement_text)
                
                # Create response
                new_available = available_xp - xp_cost
                
                embed = discord.Embed(
                    title=f"🎉 {char['name']} Improved!",
                    description=improvement_text,
                    color=0x228B22
                )
                
                embed.add_field(
                    name="💰 XP Cost",
                    value=f"Spent {xp_cost} XP\n{new_available} XP remaining",
                    inline=False
                )
                
                if improvement_type == "attribute":
                    embed.add_field(
                        name="📈 Character Development",
                        value=f"Your {target} has increased! This may affect derived stats and dice pools.",
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="🎯 Skill Advancement", 
                        value=f"You're becoming more proficient in {target}!",
                        inline=False
                    )
                
                await interaction.response.send_message(embed=embed)
                logger.info(f"XP spent: {char['name']} improved {improvement_text} for {xp_cost} XP (user {user_id})")
                
        except Exception as e:
            logger.error(f"Error in spend_xp command: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while spending XP",
                ephemeral=True
            )

    @app_commands.command(name="xp_log", description="View your character's experience point history")
    @app_commands.describe(
        limit="Number of recent entries to show (default: 10)"    )
    async def xp_log(self, interaction: discord.Interaction, limit: int = 10):
        """View character's XP transaction log"""
        user_id = str(interaction.user.id)

        if limit < 1 or limit > 50:
            await interaction.response.send_message(
                "❌ Limit must be between 1 and 50",
                ephemeral=True
            )
            return

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
            
            async with get_async_db() as conn:
                # Get XP log entries
                log_entries = await conn.fetch("""
                    SELECT action, amount, reason, created_at 
                    FROM xp_log 
                    WHERE user_id = $1 AND character_name = $2 
                    ORDER BY created_at DESC 
                    LIMIT $3
                """, user_id, char['name'], limit)
            
            if not log_entries:
                await interaction.response.send_message(
                    f"**{char['name']}** has no XP history yet.", 
                    ephemeral=True
                )
                return
            
            # Create response
            embed = discord.Embed(
                title=f"📜 {char['name']}'s XP Log",
                description=f"Showing last {len(log_entries)} transactions",
                color=0xFFD700
            )
            
            log_text = []
            for entry in log_entries:
                reason_text = f" - {entry['reason']}" if entry['reason'] else ""
                log_text.append(f"• **{entry['action']}**: {entry['amount']:+d} XP{reason_text}")
            
            # Split into chunks if needed
            log_str = '\n'.join(log_text)
            if len(log_str) > 1024:
                chunks = [log_text[i:i+15] for i in range(0, len(log_text), 15)]
                for i, chunk in enumerate(chunks):
                    field_name = "Transaction History" if i == 0 else f"History (cont. {i+1})"
                    embed.add_field(name=field_name, value="\n".join(chunk), inline=False)
            else:
                embed.add_field(name="Transaction History", value=log_str, inline=False)
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in xp_log command: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while retrieving XP log",
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

    # ===== AUTOCOMPLETE FUNCTIONS =====

    @skill_set.autocomplete('character_name')
    async def progression_character_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> List[app_commands.Choice[str]]:
        """Autocomplete character names for skill_set command"""
        return await character_autocomplete(interaction, current)

    @spend_xp.autocomplete('target')
    async def spend_xp_target_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> List[app_commands.Choice[str]]:
        """Autocomplete attribute and skill names for spending XP"""
        improvement_type = getattr(interaction.namespace, 'improvement_type', None)
        
        targets = []
        
        if improvement_type == "attribute" or improvement_type is None:
            attributes = ["Strength", "Dexterity", "Stamina", "Charisma", "Manipulation", "Composure", "Intelligence", "Wits", "Resolve"]
            targets.extend(attributes)
        
        if improvement_type == "skill" or improvement_type is None:
            targets.extend(ALL_SKILLS)
        
        filtered = [
            target for target in targets 
            if current.lower() in target.lower()
        ]
        
        return [
            app_commands.Choice(name=target, value=target)
            for target in filtered[:25]
        ]


async def setup(bot: commands.Bot):
    """Setup function for the Character Progression cog"""
    cog = CharacterProgression(bot)
    await bot.add_cog(cog)
    logger.info(f"Character Progression cog loaded with {len(cog.get_app_commands())} commands")
