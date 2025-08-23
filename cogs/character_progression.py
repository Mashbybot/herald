"""
Character Progression Cog for Herald Bot
Handles character development: XP, skills, specialties, templates, help
"""

import discord
from discord import app_commands
from discord.ext import commands
from typing import List
import logging

from core.db import get_db_connection
from core.character_utils import find_character, character_autocomplete, ALL_SKILLS
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
            conn = get_db_connection()
            cur = conn.cursor()
            
            # First, reset all skills to 0
            cur.execute("""
                UPDATE skills 
                SET dots = 0 
                WHERE user_id = ? AND character_name = ?
            """, (self.user_id, self.character_name))
            
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
                cur.execute("""
                    UPDATE skills 
                    SET dots = ? 
                    WHERE user_id = ? AND character_name = ? AND skill_name = ?
                """, (dots, self.user_id, self.character_name, skill_name))
            
            conn.commit()
            conn.close()
            
            embed = discord.Embed(
                title="✅ Skill Template Applied",
                description=f"Applied **{self.template_info['name']}** template to **{self.character_name}**",
                color=0x228B22
            )
            
            # Show what was applied
            applied_text = []
            for dots_str, count in self.template_info['distribution'].items():
                dots = int(dots_str)
                if dots > 0:
                    dots_display = "●" * dots + "○" * (5 - dots)
                    applied_text.append(f"• {count} skills at {dots_display} ({dots} dots)")
            
            embed.add_field(
                name="📊 Skills Set",
                value="\n".join(applied_text),
                inline=False
            )
            
            embed.add_field(
                name="💡 Next Steps",
                value="Skills have been distributed in alphabetical order. Use `/skill_set` to customize specific skills or use `/sheet` to view your character.",
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
        character_name="Character name",
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
        character_name: str,
        skill: str,
        dots: int,
    ):
        """Set skill dots for a character"""
        user_id = str(interaction.user.id)
        dots = max(0, min(dots, 5))  # Clamp to valid range

        try:
            conn = get_db_connection()
            cur = conn.cursor()

            # Verify character exists
            cur.execute("SELECT name FROM characters WHERE user_id = ? AND name = ?", (user_id, character_name))
            if not cur.fetchone():
                await interaction.response.send_message(
                    f"⚠️ Character **{character_name}** not found", ephemeral=True
                )
                conn.close()
                return

            # Update skill
            cur.execute(
                "UPDATE skills SET dots = ? WHERE user_id = ? AND character_name = ? AND skill_name = ?",
                (dots, user_id, character_name, skill)
            )
            
            if cur.rowcount == 0:
                await interaction.response.send_message(
                    f"⚠️ Skill **{skill}** not found on **{character_name}**", ephemeral=True
                )
                conn.close()
                return

            conn.commit()
            conn.close()

            # Success response
            dots_display = "●" * dots + "○" * (5 - dots)
            await interaction.response.send_message(
                f"✅ **{character_name}**'s **{skill}** set to {dots_display} ({dots} dots)",
                ephemeral=True
            )
            logger.info(f"Updated {character_name}'s {skill} to {dots} dots for user {user_id}")

        except Exception as e:
            logger.error(f"Error setting skill: {e}")
            await interaction.response.send_message(
                f"❌ Error updating skill: {str(e)}", ephemeral=True
            )

#==== Start of Part 2 ====

    @app_commands.command(name="skill_template", description="Apply H5E skill distribution templates to your character")
    @app_commands.describe(
        character="Character name",
        template="Skill distribution template from H5E",
        preview="Show what the template does without applying it"
    )
    @app_commands.choices(template=[
        app_commands.Choice(name="Jack of All Trades (1@3, 8@2, 10@1)", value="jack"),
        app_commands.Choice(name="Balanced (3@3, 5@2, 7@1)", value="balanced"),
        app_commands.Choice(name="Specialist (1@4, 3@3, 3@2, 3@1)", value="specialist")
    ])
    async def skill_template(
        self, 
        interaction: discord.Interaction, 
        character: str, 
        template: str, 
        preview: bool = False
    ):
        """Apply H5E skill distribution templates"""
        user_id = str(interaction.user.id)
        
        # Define skill distribution templates
        templates = {
            "jack": {
                "name": "Jack of All Trades",
                "description": "Broad competency across many skills",
                "distribution": {"4": 0, "3": 1, "2": 8, "1": 10, "0": 8},
                "total_skills": 19
            },
            "balanced": {
                "name": "Balanced",
                "description": "Even mix of competencies",
                "distribution": {"4": 0, "3": 3, "2": 5, "1": 7, "0": 12},
                "total_skills": 15
            },
            "specialist": {
                "name": "Specialist", 
                "description": "Highly focused expertise",
                "distribution": {"4": 1, "3": 3, "2": 3, "1": 3, "0": 17},
                "total_skills": 10
            }
        }
        
        if template not in templates:
            await interaction.response.send_message("❌ Invalid template", ephemeral=True)
            return
        
        template_info = templates[template]
        
        try:
            # Use fuzzy character matching
            char = await find_character(user_id, character)
            
            if not char:
                await interaction.response.send_message(f"⚠️ No character named **{character}** found", ephemeral=True)
                return
            
            if preview:
                # Show template preview
                embed = discord.Embed(
                    title=f"📋 {template_info['name']} Template Preview",
                    description=template_info['description'],
                    color=0x4169E1
                )
                
                # Show distribution
                dist_text = []
                for dots, count in template_info['distribution'].items():
                    if count > 0 and dots != "0":
                        dots_display = "●" * int(dots) + "○" * (5 - int(dots))
                        dist_text.append(f"**{count} skills at {dots} dots:** {dots_display}")
                
                embed.add_field(
                    name="📊 Distribution",
                    value="\n".join(dist_text),
                    inline=False
                )
                
                embed.add_field(
                    name="📝 Total Skills",
                    value=f"{template_info['total_skills']} skills with dots (out of {len(ALL_SKILLS)} available)",
                    inline=False
                )
                
                embed.add_field(
                    name="⚠️ Important",
                    value="This will **overwrite all current skill dots**. Use `/skill_template` without `preview:true` to apply.",
                    inline=False
                )
                
                embed.set_footer(text="H5E Character Creation • Page 60-61")
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Apply template with confirmation
            view = SkillTemplateView(user_id, char['name'], template, template_info, timeout=30)
            
            embed = discord.Embed(
                title=f"⚠️ Apply {template_info['name']} Template",
                description=f"Apply the **{template_info['name']}** skill template to **{char['name']}**?",
                color=0xFF4500
            )
            
            # Show what will happen
            dist_text = []
            for dots, count in template_info['distribution'].items():
                if count > 0 and dots != "0":
                    dist_text.append(f"• {count} skills at {dots} dots")
            
            embed.add_field(
                name="📊 This Will Set",
                value="\n".join(dist_text),
                inline=False
            )
            
            embed.add_field(
                name="⚠️ Warning", 
                value="This will **overwrite all current skill dots**. This action cannot be undone.",
                inline=False
            )
            
            embed.set_footer(text="You have 30 seconds to confirm or cancel")
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in skill_template command: {e}")
            await interaction.response.send_message("❌ An error occurred while applying skill template", ephemeral=True)

    @app_commands.command(name="skill_bulk", description="Set multiple skills at once")
    @app_commands.describe(
        character="Character name",
        skill_list="Skills and dots (format: 'Athletics:3,Firearms:2,Stealth:4')"
    )
    async def skill_bulk(self, interaction: discord.Interaction, character: str, skill_list: str):
        """Set multiple skills at once with bulk operation"""
        user_id = str(interaction.user.id)
        
        try:
            # Use fuzzy character matching
            char = await find_character(user_id, character)
            
            if not char:
                await interaction.response.send_message(f"⚠️ No character named **{character}** found", ephemeral=True)
                return
            
            # Parse skill list
            skill_updates = []
            try:
                for pair in skill_list.split(','):
                    skill_name, dots_str = pair.split(':')
                    skill_name = skill_name.strip()
                    dots = int(dots_str.strip())
                    
                    # Validate skill name
                    if skill_name not in ALL_SKILLS:
                        await interaction.response.send_message(f"❌ **{skill_name}** is not a valid skill", ephemeral=True)
                        return
                    
                    # Validate dots
                    if not 0 <= dots <= 5:
                        await interaction.response.send_message(f"❌ Skill dots must be 0-5 (got {dots} for {skill_name})", ephemeral=True)
                        return
                    
                    skill_updates.append((skill_name, dots))
                    
            except ValueError:
                await interaction.response.send_message(
                    "❌ Invalid format. Use: 'Skill1:dots,Skill2:dots' (e.g., 'Athletics:3,Firearms:2')", 
                    ephemeral=True
                )
                return
            
            if not skill_updates:
                await interaction.response.send_message("❌ No valid skill updates found", ephemeral=True)
                return
            
            # Apply updates
            conn = get_db_connection()
            cur = conn.cursor()
            
            for skill_name, dots in skill_updates:
                cur.execute("""
                    UPDATE skills 
                    SET dots = ? 
                    WHERE user_id = ? AND character_name = ? AND skill_name = ?
                """, (dots, user_id, char['name'], skill_name))
            
            conn.commit()
            conn.close()
            
            # Create response
            embed = discord.Embed(
                title=f"✅ Skills Updated for {char['name']}",
                color=0x228B22
            )
            
            update_text = []
            for skill_name, dots in skill_updates:
                dots_display = "●" * dots + "○" * (5 - dots) if dots > 0 else "○○○○○"
                update_text.append(f"**{skill_name}:** {dots_display} ({dots})")
            
            # Split into chunks if too many skills
            if len(update_text) <= 10:
                embed.add_field(name="📊 Updated Skills", value="\n".join(update_text), inline=False)
            else:
                # Split into multiple fields
                for i in range(0, len(update_text), 10):
                    chunk = update_text[i:i+10]
                    field_name = "📊 Updated Skills" if i == 0 else f"📊 Updated Skills (cont.)"
                    embed.add_field(name=field_name, value="\n".join(chunk), inline=False)
            
            embed.set_footer(text=f"Updated {len(skill_updates)} skills")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            logger.info(f"Bulk updated {len(skill_updates)} skills for {char['name']} (user {user_id})")
            
        except Exception as e:
            logger.error(f"Error in skill_bulk command: {e}")
            await interaction.response.send_message("❌ An error occurred while updating skills", ephemeral=True)

#==== Start of Part 3 ====

    # ===== SPECIALTY COMMANDS =====

    @app_commands.command(name="specialty", description="Manage skill specialties for your character")
    @app_commands.describe(
        character="Character name",
        action="What to do with specialties",
        skill="Skill to manage specialties for",
        specialty="Specialty name (required for add/remove)"
    )
    @app_commands.choices(
        action=[
            app_commands.Choice(name="View All", value="view"),
            app_commands.Choice(name="Add", value="add"),
            app_commands.Choice(name="Remove", value="remove"),
            app_commands.Choice(name="List by Skill", value="list_skill")
        ],
        skill=[
            app_commands.Choice(name=skill, value=skill)
            for skill in ALL_SKILLS[:25]  # Discord limit
        ]
    )
    async def specialty(
        self,
        interaction: discord.Interaction,
        character: str,
        action: str,
        skill: str = None,
        specialty: str = None
    ):
        """Manage skill specialties (specific expertise within skills)"""
        user_id = str(interaction.user.id)
        
        try:
            # Use fuzzy character matching
            char = await find_character(user_id, character)
            
            if not char:
                await interaction.response.send_message(f"⚠️ No character named **{character}** found", ephemeral=True)
                return
            
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Create specialties table if it doesn't exist
            cur.execute("""
                CREATE TABLE IF NOT EXISTS specialties (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    character_name TEXT NOT NULL,
                    skill_name TEXT NOT NULL,
                    specialty_name TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, character_name, skill_name, specialty_name),
                    FOREIGN KEY (user_id, character_name) REFERENCES characters(user_id, name) ON DELETE CASCADE
                )
            """)
            
            if action == "view":
                # Show all specialties for character
                cur.execute("""
                    SELECT skill_name, specialty_name 
                    FROM specialties 
                    WHERE user_id = ? AND character_name = ? 
                    ORDER BY skill_name, specialty_name
                """, (user_id, char['name']))
                
                specialties = cur.fetchall()
                
                embed = discord.Embed(
                    title=f"🎯 {char['name']}'s Specialties",
                    color=0x9932CC
                )
                
                if not specialties:
                    embed.description = "*No specialties set*"
                    embed.add_field(
                        name="💡 About Specialties",
                        value=(
                            "Specialties represent specific expertise within a skill. "
                            "When your specialty applies to a roll, you get bonus dice!\n\n"
                            "**H5E Rules:**\n"
                            "• Most skills can have specialties equal to dots in the skill\n"
                            "• Academics, Craft, Performance, Science require specialties if you have dots\n"
                            "• Use `/specialty character:Name action:add skill:Athletics specialty:\"Running\"`"
                        ),
                        inline=False
                    )
                else:
                    # Group by skill
                    skills_dict = {}
                    for spec in specialties:
                        skill_name = spec['skill_name']
                        if skill_name not in skills_dict:
                            skills_dict[skill_name] = []
                        skills_dict[skill_name].append(spec['specialty_name'])
                    
                    specialty_text = []
                    for skill_name in sorted(skills_dict.keys()):
                        specialty_list = ", ".join(skills_dict[skill_name])
                        specialty_text.append(f"**{skill_name}:** {specialty_list}")
                    
                    # Handle long lists
                    full_text = "\n".join(specialty_text)
                    if len(full_text) <= 1024:
                        embed.add_field(name="🎯 Specialties", value=full_text, inline=False)
                    else:
                        # Split into chunks
                        chunks = []
                        current_chunk = []
                        current_length = 0
                        
                        for line in specialty_text:
                            if current_length + len(line) + 1 > 1024:
                                chunks.append("\n".join(current_chunk))
                                current_chunk = [line]
                                current_length = len(line)
                            else:
                                current_chunk.append(line)
                                current_length += len(line) + 1
                        
                        if current_chunk:
                            chunks.append("\n".join(current_chunk))
                        
                        for i, chunk in enumerate(chunks):
                            field_name = "🎯 Specialties" if i == 0 else f"🎯 Specialties (cont. {i+1})"
                            embed.add_field(name=field_name, value=chunk, inline=False)
                    
                    embed.set_footer(text=f"Total specialties: {len(specialties)}")
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
            elif action == "list_skill":
                if not skill:
                    await interaction.response.send_message("❌ Skill name required for listing specialties", ephemeral=True)
                    return
                
                # Show specialties for specific skill
                cur.execute("""
                    SELECT specialty_name 
                    FROM specialties 
                    WHERE user_id = ? AND character_name = ? AND skill_name = ?
                    ORDER BY specialty_name
                """, (user_id, char['name'], skill))
                
                specialties = cur.fetchall()
                
                # Get skill dots
                cur.execute("""
                    SELECT dots 
                    FROM skills 
                    WHERE user_id = ? AND character_name = ? AND skill_name = ?
                """, (user_id, char['name'], skill))
                skill_data = cur.fetchone()
                skill_dots = skill_data['dots'] if skill_data else 0
                
                embed = discord.Embed(
                    title=f"🎯 {char['name']}'s {skill} Specialties",
                    color=0x9932CC
                )
                
                embed.add_field(
                    name="📊 Skill Level",
                    value=f"{'●' * skill_dots}{'○' * (5 - skill_dots)} ({skill_dots} dots)",
                    inline=False
                )
                
                if not specialties:
                    embed.add_field(
                        name="🎯 Specialties",
                        value="*No specialties for this skill*",
                        inline=False
                    )
                    
                    max_specialties = max(1, skill_dots)  # At least 1, up to skill dots
                    embed.add_field(
                        name="💡 Available Slots",
                        value=f"Can have up to {max_specialties} specialties for this skill level",
                        inline=False
                    )
                else:
                    specialty_list = [f"• {spec['specialty_name']}" for spec in specialties]
                    embed.add_field(
                        name="🎯 Current Specialties",
                        value="\n".join(specialty_list),
                        inline=False
                    )
                    
                    max_specialties = max(1, skill_dots)
                    remaining = max_specialties - len(specialties)
                    if remaining > 0:
                        embed.add_field(
                            name="💡 Available Slots",
                            value=f"Can add {remaining} more specialties",
                            inline=False
                        )
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
            elif action == "add":
                if not skill or not specialty:
                    await interaction.response.send_message("❌ Both skill and specialty name required for adding", ephemeral=True)
                    return
                
                if len(specialty) > 50:
                    await interaction.response.send_message("❌ Specialty name too long (max 50 characters)", ephemeral=True)
                    return
                
                # Check if skill exists
                if skill not in ALL_SKILLS:
                    await interaction.response.send_message(f"❌ **{skill}** is not a valid skill", ephemeral=True)
                    return
                
                # Get current skill dots
                cur.execute("""
                    SELECT dots 
                    FROM skills 
                    WHERE user_id = ? AND character_name = ? AND skill_name = ?
                """, (user_id, char['name'], skill))
                skill_data = cur.fetchone()
                
                if not skill_data:
                    await interaction.response.send_message(f"❌ Skill **{skill}** not found for character", ephemeral=True)
                    return
                
                skill_dots = skill_data['dots']
                
                if skill_dots == 0:
                    await interaction.response.send_message(f"❌ Cannot add specialties to **{skill}** with 0 dots", ephemeral=True)
                    return
                
                # Check current specialty count
                cur.execute("""
                    SELECT COUNT(*) as count 
                    FROM specialties 
                    WHERE user_id = ? AND character_name = ? AND skill_name = ?
                """, (user_id, char['name'], skill))
                current_count = cur.fetchone()['count']
                
                max_specialties = max(1, skill_dots)  # Most skills: up to skill dots
                
                if current_count >= max_specialties:
                    await interaction.response.send_message(
                        f"❌ **{skill}** already has maximum specialties ({max_specialties}) for {skill_dots} dots", 
                        ephemeral=True
                    )
                    return
                
                # Check for duplicate
                cur.execute("""
                    SELECT id 
                    FROM specialties 
                    WHERE user_id = ? AND character_name = ? AND skill_name = ? AND specialty_name = ?
                """, (user_id, char['name'], skill, specialty))
                
                if cur.fetchone():
                    await interaction.response.send_message(f"⚠️ Specialty **{specialty}** already exists for {skill}", ephemeral=True)
                    return
                
                # Add specialty
                cur.execute("""
                    INSERT INTO specialties (user_id, character_name, skill_name, specialty_name)
                    VALUES (?, ?, ?, ?)
                """, (user_id, char['name'], skill, specialty))
                
                conn.commit()
                
                embed = discord.Embed(
                    title="✅ Specialty Added",
                    description=f"Added specialty **{specialty}** to {char['name']}'s **{skill}**",
                    color=0x228B22
                )
                
                remaining = max_specialties - (current_count + 1)
                if remaining > 0:
                    embed.add_field(
                        name="💡 Available Slots",
                        value=f"Can add {remaining} more specialties to {skill}",
                        inline=False
                    )
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                logger.info(f"Added specialty '{specialty}' to {skill} for {char['name']} (user {user_id})")
                
            elif action == "remove":
                if not skill or not specialty:
                    await interaction.response.send_message("❌ Both skill and specialty name required for removal", ephemeral=True)
                    return
                
                # Find and remove specialty (exact match)
                cur.execute("""
                    DELETE FROM specialties 
                    WHERE user_id = ? AND character_name = ? AND skill_name = ? AND specialty_name = ?
                """, (user_id, char['name'], skill, specialty))
                
                if cur.rowcount == 0:
                    await interaction.response.send_message(f"⚠️ Specialty **{specialty}** not found for {skill}", ephemeral=True)
                    return
                
                conn.commit()
                
                embed = discord.Embed(
                    title="✅ Specialty Removed",
                    description=f"Removed specialty **{specialty}** from {char['name']}'s **{skill}**",
                    color=0xFF4500
                )
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                logger.info(f"Removed specialty '{specialty}' from {skill} for {char['name']} (user {user_id})")
                
        except Exception as e:
            logger.error(f"Error in specialty command: {e}")
            await interaction.response.send_message("❌ An error occurred while managing specialties", ephemeral=True)
        finally:
            conn.close()

    @app_commands.command(name="specialty_bulk", description="Add multiple specialties at once")
    @app_commands.describe(
        character="Character name",
        specialty_list="Specialties (format: 'Athletics:Running,Firearms:Pistols,Academics:History')"
    )
    async def specialty_bulk(self, interaction: discord.Interaction, character: str, specialty_list: str):
        """Add multiple specialties at once"""
        user_id = str(interaction.user.id)
        
        try:
            # Use fuzzy character matching
            char = await find_character(user_id, character)
            
            if not char:
                await interaction.response.send_message(f"⚠️ No character named **{character}** found", ephemeral=True)
                return
            
            # Parse specialty list
            specialty_updates = []
            try:
                for pair in specialty_list.split(','):
                    skill_name, specialty_name = pair.split(':')
                    skill_name = skill_name.strip()
                    specialty_name = specialty_name.strip()
                    
                    # Validate skill name
                    if skill_name not in ALL_SKILLS:
                        await interaction.response.send_message(f"❌ **{skill_name}** is not a valid skill", ephemeral=True)
                        return
                    
                    # Validate specialty length
                    if len(specialty_name) > 50:
                        await interaction.response.send_message(f"❌ Specialty '{specialty_name}' too long (max 50 characters)", ephemeral=True)
                        return
                    
                    specialty_updates.append((skill_name, specialty_name))
                    
            except ValueError:
                await interaction.response.send_message(
                    "❌ Invalid format. Use: 'Skill1:Specialty1,Skill2:Specialty2' (e.g., 'Athletics:Running,Firearms:Pistols')", 
                    ephemeral=True
                )
                return
            
            if not specialty_updates:
                await interaction.response.send_message("❌ No valid specialty updates found", ephemeral=True)
                return
            
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Create specialties table if it doesn't exist
            cur.execute("""
                CREATE TABLE IF NOT EXISTS specialties (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    character_name TEXT NOT NULL,
                    skill_name TEXT NOT NULL,
                    specialty_name TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, character_name, skill_name, specialty_name),
                    FOREIGN KEY (user_id, character_name) REFERENCES characters(user_id, name) ON DELETE CASCADE
                )
            """)
            
            # Validate all skills have dots and check limits
            errors = []
            added_specialties = []
            
            for skill_name, specialty_name in specialty_updates:
                # Check skill dots
                cur.execute("""
                    SELECT dots 
                    FROM skills 
                    WHERE user_id = ? AND character_name = ? AND skill_name = ?
                """, (user_id, char['name'], skill_name))
                skill_data = cur.fetchone()
                
                if not skill_data or skill_data['dots'] == 0:
                    errors.append(f"**{skill_name}** has 0 dots")
                    continue
                
                skill_dots = skill_data['dots']
                
                # Check current specialty count
                cur.execute("""
                    SELECT COUNT(*) as count 
                    FROM specialties 
                    WHERE user_id = ? AND character_name = ? AND skill_name = ?
                """, (user_id, char['name'], skill_name))
                current_count = cur.fetchone()['count']
                
                max_specialties = max(1, skill_dots)
                
                if current_count >= max_specialties:
                    errors.append(f"**{skill_name}** already has maximum specialties ({max_specialties})")
                    continue
                
                # Check for duplicate
                cur.execute("""
                    SELECT id 
                    FROM specialties 
                    WHERE user_id = ? AND character_name = ? AND skill_name = ? AND specialty_name = ?
                """, (user_id, char['name'], skill_name, specialty_name))
                
                if cur.fetchone():
                    errors.append(f"**{specialty_name}** already exists for {skill_name}")
                    continue
                
                # Add to successful list
                added_specialties.append((skill_name, specialty_name))
            
            if errors:
                error_text = "\n".join(errors)
                await interaction.response.send_message(f"❌ Errors found:\n{error_text}", ephemeral=True)
                return
            
            # Apply all updates
            for skill_name, specialty_name in added_specialties:
                cur.execute("""
                    INSERT INTO specialties (user_id, character_name, skill_name, specialty_name)
                    VALUES (?, ?, ?, ?)
                """, (user_id, char['name'], skill_name, specialty_name))
            
            conn.commit()
            conn.close()
            
            # Create response
            embed = discord.Embed(
                title=f"✅ Specialties Added for {char['name']}",
                color=0x228B22
            )
            
            update_text = []
            for skill_name, specialty_name in added_specialties:
                update_text.append(f"**{skill_name}:** {specialty_name}")
            
            # Handle long lists
            if len(update_text) <= 15:
                embed.add_field(name="🎯 Added Specialties", value="\n".join(update_text), inline=False)
            else:
                # Split into multiple fields
                for i in range(0, len(update_text), 15):
                    chunk = update_text[i:i+15]
                    field_name = "🎯 Added Specialties" if i == 0 else f"🎯 Added Specialties (cont.)"
                    embed.add_field(name=field_name, value="\n".join(chunk), inline=False)
            
            embed.set_footer(text=f"Added {len(added_specialties)} specialties")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            logger.info(f"Bulk added {len(added_specialties)} specialties for {char['name']} (user {user_id})")
            
        except Exception as e:
            logger.error(f"Error in specialty_bulk command: {e}")
            await interaction.response.send_message("❌ An error occurred while adding specialties", ephemeral=True)

#==== Start of Part 4 ====

    # ===== EXPERIENCE POINT COMMANDS =====

    @app_commands.command(name="xp", description="View or manage your character's experience points")
    @app_commands.describe(
        character="Character name",
        action="What to do with experience points",
        amount="Amount of XP to add/subtract/set (optional for 'view')",
        reason="Reason for XP change (optional)"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="View", value="view"),
        app_commands.Choice(name="Add", value="add"),
        app_commands.Choice(name="Subtract", value="subtract"),
        app_commands.Choice(name="Set", value="set")
    ])
    async def experience_points(
        self, 
        interaction: discord.Interaction, 
        character: str, 
        action: str, 
        amount: int = None, 
        reason: str = None
    ):
        """Manage character experience points"""
        user_id = str(interaction.user.id)
        
        try:
            # Use fuzzy character matching
            char = await find_character(user_id, character)
            
            if not char:
                await interaction.response.send_message(f"⚠️ No character named **{character}** found", ephemeral=True)
                return
            
            # Get current XP (add columns if they don't exist)
            conn = get_db_connection()
            
            # Check if XP columns exist, add them if not
            cur = conn.cursor()
            cur.execute("PRAGMA table_info(characters)")
            columns = [row[1] for row in cur.fetchall()]
            
            if 'experience_total' not in columns:
                logger.info("Adding experience tracking columns to characters table")
                cur.execute("ALTER TABLE characters ADD COLUMN experience_total INTEGER DEFAULT 0")
                cur.execute("ALTER TABLE characters ADD COLUMN experience_spent INTEGER DEFAULT 0")
                
                # Create XP log table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS xp_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        character_name TEXT NOT NULL,
                        action TEXT NOT NULL,
                        amount INTEGER NOT NULL,
                        reason TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id, character_name) REFERENCES characters(user_id, name) ON DELETE CASCADE
                    )
                """)
                conn.commit()
            
            # Get character with XP data
            cur.execute("SELECT * FROM characters WHERE user_id = ? AND name = ?", (user_id, char['name']))
            char_with_xp = cur.fetchone()
            
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
                cur.execute("""
                    SELECT action, amount, reason, created_at 
                    FROM xp_log 
                    WHERE user_id = ? AND character_name = ? 
                    ORDER BY created_at DESC 
                    LIMIT 3
                """, (user_id, char['name']))
                recent_logs = cur.fetchall()
                
                if recent_logs:
                    history_text = []
                    for log in recent_logs:
                        date_str = log['created_at'][:10]  # Just the date part
                        reason_text = f" ({log['reason']})" if log['reason'] else ""
                        history_text.append(f"• {log['action']} {log['amount']} XP{reason_text} - {date_str}")
                    
                    embed.add_field(
                        name="📜 Recent Activity",
                        value="\n".join(history_text),
                        inline=False
                    )
                
                await interaction.response.send_message(embed=embed)
                
            else:
                # Actions that modify XP require amount
                if amount is None:
                    await interaction.response.send_message(f"⚠️ Amount required for **{action}** action", ephemeral=True)
                    return
                    
                if amount < 0:
                    await interaction.response.send_message("❌ XP amount must be positive", ephemeral=True)
                    return
                
                # Calculate new values
                if action == "add":
                    new_total = current_total + amount
                    new_spent = current_spent
                    action_text = f"Gained {amount} XP"
                elif action == "subtract":
                    # Subtract from available XP (increase spent)
                    if amount > current_available:
                        await interaction.response.send_message(
                            f"❌ Cannot subtract {amount} XP. Only {current_available} XP available.", 
                            ephemeral=True
                        )
                        return
                    new_total = current_total
                    new_spent = current_spent + amount
                    action_text = f"Spent {amount} XP"
                elif action == "set":
                    new_total = amount
                    new_spent = min(current_spent, amount)  # Don't exceed new total
                    action_text = f"Set total XP to {amount}"
                
                new_available = new_total - new_spent
                
                # Update database
                cur.execute("""
                    UPDATE characters 
                    SET experience_total = ?, experience_spent = ? 
                    WHERE user_id = ? AND name = ?
                """, (new_total, new_spent, user_id, char['name']))
                
                # Log the change
                cur.execute("""
                    INSERT INTO xp_log (user_id, character_name, action, amount, reason, created_at)
                    VALUES (?, ?, ?, ?, ?, datetime('now'))
                """, (user_id, char['name'], action_text, amount, reason))
                
                conn.commit()
                
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
            await interaction.response.send_message("❌ An error occurred while managing experience points", ephemeral=True)
        finally:
            conn.close()

    @app_commands.command(name="spend_xp", description="Spend XP to improve attributes or skills")
    @app_commands.describe(
        character="Character name",
        improvement_type="What to improve",
        target="Attribute or skill name",
        new_rating="New rating (current rating + 1)"
    )
    @app_commands.choices(
        improvement_type=[
            app_commands.Choice(name="Attribute", value="attribute"),
            app_commands.Choice(name="Skill", value="skill")
        ]
    )
    async def spend_xp(
        self,
        interaction: discord.Interaction,
        character: str,
        improvement_type: str,
        target: str,
        new_rating: int
    ):
        """Spend XP to improve character abilities"""
        user_id = str(interaction.user.id)
        
        if new_rating < 1 or new_rating > 5:
            await interaction.response.send_message("❌ Ratings must be between 1 and 5", ephemeral=True)
            return
        
        try:
            # Use fuzzy character matching
            char = await find_character(user_id, character)
            
            if not char:
                await interaction.response.send_message(f"⚠️ No character named **{character}** found", ephemeral=True)
                return
            
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Get current XP
            cur.execute("SELECT experience_total, experience_spent FROM characters WHERE user_id = ? AND name = ?", 
                       (user_id, char['name']))
            xp_data = cur.fetchone()
            
            if not xp_data:
                await interaction.response.send_message("❌ XP data not found. Use `/xp` command first.", ephemeral=True)
                return
            
            current_total = xp_data['experience_total'] or 0
            current_spent = xp_data['experience_spent'] or 0
            available_xp = current_total - current_spent
            
            if improvement_type == "attribute":
                # Check if attribute exists and get current value
                target_lower = target.lower()
                if target_lower not in ['strength', 'dexterity', 'stamina', 'charisma', 'manipulation', 'composure', 'intelligence', 'wits', 'resolve']:
                    await interaction.response.send_message(f"❌ **{target}** is not a valid attribute", ephemeral=True)
                    return
                
                cur.execute(f"SELECT {target_lower} FROM characters WHERE user_id = ? AND name = ?", (user_id, char['name']))
                current_rating = cur.fetchone()[target_lower]
                
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
                cur.execute(f"""
                    UPDATE characters 
                    SET {target_lower} = ?, experience_spent = experience_spent + ?
                    WHERE user_id = ? AND name = ?
                """, (new_rating, xp_cost, user_id, char['name']))
                
                # Update derived stats if needed
                if target_lower == 'stamina':
                    new_health = new_rating + 3
                    cur.execute("UPDATE characters SET health = ? WHERE user_id = ? AND name = ?", 
                               (new_health, user_id, char['name']))
                elif target_lower in ['resolve', 'composure']:
                    # Recalculate willpower
                    cur.execute("SELECT resolve, composure FROM characters WHERE user_id = ? AND name = ?", 
                               (user_id, char['name']))
                    attrs = cur.fetchone()
                    new_willpower = attrs['resolve'] + attrs['composure']
                    cur.execute("UPDATE characters SET willpower = ? WHERE user_id = ? AND name = ?", 
                               (new_willpower, user_id, char['name']))
                
                improvement_text = f"{target} {current_rating} → {new_rating}"
                
            else:  # skill
                # Check if skill exists and get current value
                cur.execute("SELECT dots FROM skills WHERE user_id = ? AND character_name = ? AND skill_name = ?", 
                           (user_id, char['name'], target))
                skill_data = cur.fetchone()
                
                if not skill_data:
                    await interaction.response.send_message(f"❌ Skill **{target}** not found", ephemeral=True)
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
                cur.execute("""
                    UPDATE skills 
                    SET dots = ? 
                    WHERE user_id = ? AND character_name = ? AND skill_name = ?
                """, (new_rating, user_id, char['name'], target))
                
                cur.execute("""
                    UPDATE characters 
                    SET experience_spent = experience_spent + ?
                    WHERE user_id = ? AND name = ?
                """, (xp_cost, user_id, char['name']))
                
                improvement_text = f"{target} {current_rating} → {new_rating}"
            
            # Log the expenditure
            cur.execute("""
                INSERT INTO xp_log (user_id, character_name, action, amount, reason, created_at)
                VALUES (?, ?, ?, ?, ?, datetime('now'))
            """, (user_id, char['name'], f"Spent {xp_cost} XP", xp_cost, improvement_text))
            
            conn.commit()
            
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
            await interaction.response.send_message("❌ An error occurred while spending XP", ephemeral=True)
        finally:
            conn.close()

    @app_commands.command(name="xp_log", description="View your character's experience point history")
    @app_commands.describe(
        character="Character name",
        limit="Number of recent entries to show (default: 10)"
    )
    async def xp_log(self, interaction: discord.Interaction, character: str, limit: int = 10):
        """View character's XP transaction log"""
        user_id = str(interaction.user.id)
        
        if limit < 1 or limit > 50:
            await interaction.response.send_message("❌ Limit must be between 1 and 50", ephemeral=True)
            return
        
        try:
            # Use fuzzy character matching
            char = await find_character(user_id, character)
            
            if not char:
                await interaction.response.send_message(f"⚠️ No character named **{character}** found", ephemeral=True)
                return
            
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Get XP log entries
            cur.execute("""
                SELECT action, amount, reason, created_at 
                FROM xp_log 
                WHERE user_id = ? AND character_name = ? 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (user_id, char['name'], limit))
            
            log_entries = cur.fetchall()
            conn.close()
            
            if not log_entries:
                await interaction.response.send_message(
                    f"📋 No experience log found for **{char['name']}**", ephemeral=True
                )
                return
            
            embed = discord.Embed(
                title=f"📜 {char['name']}'s Experience Log",
                color=0x4169E1
            )
            
            log_text = []
            for entry in log_entries:
                date_str = entry['created_at'][:16].replace('T', ' ')  # Format: YYYY-MM-DD HH:MM
                reason_text = f" - {entry['reason']}" if entry['reason'] else ""
                log_text.append(f"**{date_str}:** {entry['action']}{reason_text}")
            
            # Split into multiple fields if too long
            full_text = "\n".join(log_text)
            if len(full_text) <= 1024:
                embed.add_field(name="Recent Activity", value=full_text, inline=False)
            else:
                # Split into chunks
                chunks = []
                current_chunk = []
                current_length = 0
                
                for line in log_text:
                    if current_length + len(line) + 1 > 1024:
                        chunks.append("\n".join(current_chunk))
                        current_chunk = [line]
                        current_length = len(line)
                    else:
                        current_chunk.append(line)
                        current_length += len(line) + 1
                
                if current_chunk:
                    chunks.append("\n".join(current_chunk))
                
                for i, chunk in enumerate(chunks):
                    field_name = "Recent Activity" if i == 0 else f"Recent Activity (cont. {i+1})"
                    embed.add_field(name=field_name, value=chunk, inline=False)
            
            embed.set_footer(text=f"Showing last {len(log_entries)} entries")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in xp_log command: {e}")
            await interaction.response.send_message("❌ An error occurred while loading XP log", ephemeral=True)

#==== Start of Part 5 ====

    # ===== HELP COMMAND =====

    @app_commands.command(name="help", description="Get help with Herald bot commands")
    @app_commands.describe(topic="Specific help topic (optional)")
    @app_commands.choices(topic=[
        app_commands.Choice(name="Character Creation", value="creation"),
        app_commands.Choice(name="Character Management", value="management"),
        app_commands.Choice(name="Dice Rolling", value="rolling"),
        app_commands.Choice(name="Experience Points", value="experience"),
        app_commands.Choice(name="Hunter Mechanics", value="mechanics"),
        app_commands.Choice(name="Equipment & Notes", value="extras"),
        app_commands.Choice(name="All Commands", value="commands")
    ])
    async def help_command(self, interaction: discord.Interaction, topic: str = None):
        """Comprehensive help system for Herald bot"""
        
        if topic is None:
            # General overview
            embed = discord.Embed(
                title="🏹 Herald - Hunter: The Reckoning 5E Bot",
                description="A comprehensive character management and dice rolling bot for H5E",
                color=0x4169E1
            )
            
            embed.add_field(
                name="📚 Quick Start",
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
            
            embed.set_footer(text="Made for Hunter: The Reckoning 5th Edition")
            
        elif topic == "creation":
            embed = discord.Embed(
                title="📋 Character Creation Help",
                color=0x228B22
            )
            
            embed.add_field(
                name="🆕 Creating Characters",
                value=(
                    "**Basic Creation:**\n"
                    "`/create name:\"Character Name\"`\n\n"
                    "**With Attributes:**\n"
                    "`/create name:\"Raven\" strength:3 dexterity:4 intelligence:2`\n\n"
                    "All attributes default to 1 if not specified."
                ),
                inline=False
            )
            
            embed.add_field(
                name="⚖️ H5E Rules",
                value=(
                    "• Attributes range from 1-5\n"
                    "• Health = Stamina + 3\n"
                    "• Willpower = Resolve + Composure\n"
                    "• All skills start at 0 dots"
                ),
                inline=False
            )
            
            embed.add_field(
                name="🔧 After Creation",
                value=(
                    "• Set skills: `/skill_set`\n"
                    "• Set Creed: `/creed`\n" 
                    "• View sheet: `/sheet`"
                ),
                inline=False
            )
            
        elif topic == "management":
            embed = discord.Embed(
                title="🔧 Character Management Help",
                color=0x8B4513
            )
            
            embed.add_field(
                name="📝 Basic Management",
                value=(
                    "• **View characters:** `/characters`\n"
                    "• **View sheet:** `/sheet character:Name`\n"
                    "• **Rename:** `/rename old_name:Old new_name:New`\n"
                    "• **Delete:** `/delete name:Character` (with confirmation)"
                ),
                inline=False
            )
            
            embed.add_field(
                name="🎯 Skills & Attributes",
                value=(
                    "• **Set skill:** `/skill_set character:Name skill:Athletics dots:3`\n"
                    "• **Skill templates:** `/skill_template character:Name template:balanced`\n"
                    "• **Bulk skills:** `/skill_bulk character:Name skill_list:\"Athletics:3,Stealth:2\"`\n"
                    "• **Spend XP:** `/spend_xp` (see Experience Points help)"
                ),
                inline=False
            )
            
            embed.add_field(
                name="💔 Damage & Healing",
                value=(
                    "• **Apply damage:** `/damage character:Name track:health amount:2`\n"
                    "• **Heal damage:** `/heal character:Name track:health amount:1`\n"
                    "• Supports both superficial and aggravated damage"
                ),
                inline=False
            )
            
        elif topic == "rolling":
            embed = discord.Embed(
                title="🎲 Dice Rolling Help",
                color=0x8B0000
            )
            
            embed.add_field(
                name="🎯 Basic Rolling",
                value=(
                    "**Manual Roll:**\n"
                    "`/roll attribute:3 skill:2 difficulty:0`\n\n"
                    "**Character Roll:**\n"
                    "`/roll_char character:Raven attribute:strength skill:brawl`\n\n"
                    "**Simple Roll:**\n"
                    "`/simple pool:5`"
                ),
                inline=False
            )
            
            embed.add_field(
                name="⚡ H5E Mechanics",
                value=(
                    "• **Success:** 6+ on d10\n"
                    "• **Critical:** Pairs of 10s = +1 success each\n"
                    "• **Edge dice:** Explode on 10s (keep rolling)\n"
                    "• **Desperation:** Can cause messy criticals\n"
                    "• **Difficulty:** Modifier to dice pool"
                ),
                inline=False
            )
            
            embed.add_field(
                name="🔥 Advanced Options",
                value=(
                    "• `desperation:true` - Add desperation die\n"
                    "• `edge:2` - Add 2 edge dice\n"
                    "• `difficulty:2` - +2 difficulty\n"
                    "• `modifier:-1` - -1 dice to pool"
                ),
                inline=False
            )
            
        elif topic == "experience":
            embed = discord.Embed(
                title="⭐ Experience Points Help",
                color=0xFFD700
            )
            
            embed.add_field(
                name="💰 Managing XP",
                value=(
                    "**View XP:** `/xp character:Name action:view`\n"
                    "**Add XP:** `/xp character:Name action:add amount:5 reason:\"Mission complete\"`\n"
                    "**Set XP:** `/xp character:Name action:set amount:20`\n"
                    "**View Log:** `/xp_log character:Name limit:10`"
                ),
                inline=False
            )
            
            embed.add_field(
                name="🎯 Spending XP",
                value=(
                    "**Improve Attribute:**\n"
                    "`/spend_xp character:Name improvement_type:attribute target:Strength new_rating:3`\n\n"
                    "**Improve Skill:**\n"
                    "`/spend_xp character:Name improvement_type:skill target:Investigation new_rating:2`"
                ),
                inline=False
            )
            
            embed.add_field(
                name="💎 H5E Costs",
                value=(
                    "• **Attributes:** New rating × 4 XP\n"
                    "• **Skills:** New rating × 2 XP\n"
                    "• Can only increase by 1 dot at a time\n"
                    "• Derived stats update automatically"
                ),
                inline=False
            )
            
        elif topic == "mechanics":
            embed = discord.Embed(
                title="🏹 Hunter Mechanics Help", 
                color=0x8B4513
            )
            
            embed.add_field(
                name="⚡ Edge",
                value=(
                    "**View/Set:** `/edge character:Name action:view`\n"
                    "**Modify:** `/edge character:Name action:add amount:1`\n\n"
                    "Edge adds dice to Danger rolls and provides supernatural resistance."
                ),
                inline=False
            )
            
            embed.add_field(
                name="🌑 Desperation",
                value=(
                    "**View/Set:** `/desperation character:Name action:view`\n"
                    "**Modify:** `/desperation character:Name action:add amount:1`\n\n"
                    "High Desperation (7+) adds Desperation dice to failed rolls."
                ),
                inline=False
            )
            
            embed.add_field(
                name="🗡️ Creed & Character Goals",
                value=(
                    "**Creed:** `/creed character:Name creed:\"Innocent\"`\n"
                    "**Ambition:** `/ambition character:Name ambition:\"Long-term goal\"`\n"
                    "**Desire:** `/desire character:Name desire:\"Short-term goal\"`\n"
                    "**Drive:** `/drive character:Name drive:\"Why you hunt\"`\n\n"
                    "Common Creeds: Innocent, Martyr, Redeemer, Visionary, Wayward"
                ),
                inline=False
            )
            
            embed.add_field(
                name="🎯 Specialties",
                value=(
                    "**View:** `/specialty character:Name action:view`\n"
                    "**Add:** `/specialty character:Name action:add skill:Athletics specialty:\"Running\"`\n"
                    "**Bulk Add:** `/specialty_bulk character:Name specialty_list:\"Athletics:Running,Firearms:Pistols\"`\n\n"
                    "Specialties give bonus dice when they apply to rolls."
                ),
                inline=False
            )
            
        elif topic == "extras":
            embed = discord.Embed(
                title="🎒 Equipment & Notes Help",
                color=0x8B4513
            )
            
            embed.add_field(
                name="🎒 Equipment",
                value=(
                    "**View:** `/equipment character:Name action:view`\n"
                    "**Add:** `/equipment character:Name action:add item:\"Shotgun\" description:\"12-gauge\"`\n"
                    "**Remove:** `/equipment character:Name action:remove item:\"Shotgun\"`\n"
                    "**Clear:** `/equipment character:Name action:clear`"
                ),
                inline=False
            )
            
            embed.add_field(
                name="📓 Notes",
                value=(
                    "**View:** `/notes character:Name action:view`\n"
                    "**Add:** `/notes character:Name action:add title:\"Session 1\" content:\"We met the vampire...\"`\n"
                    "**Remove:** `/notes character:Name action:remove title:\"Session 1\"`\n"
                    "**Clear:** `/notes character:Name action:clear`"
                ),
                inline=False
            )
            
            embed.add_field(
                name="💡 Tips",
                value=(
                    "• Use quotes for multi-word names/titles\n"
                    "• Equipment supports optional descriptions\n"
                    "• Notes are limited to 2000 characters\n"
                    "• Both systems support fuzzy name matching"
                ),
                inline=False
            )
            
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
                name="🎲 Dice Rolling",
                value=(
                    "`/roll` - Manual dice roll\n"
                    "`/roll_char` - Character-based roll\n"
                    "`/simple` - Simple dice pool\n"
                    "`/rouse` - Rouse check for desperation"
                ),
                inline=False
            )
            
            embed.add_field(
                name="🎯 Character Development",
                value=(
                    "`/skill_set` - Set skill dots\n"
                    "`/skill_template` - Apply H5E skill templates\n"
                    "`/skill_bulk` - Set multiple skills at once\n"
                    "`/specialty` - Manage skill specialties\n"
                    "`/specialty_bulk` - Add multiple specialties\n"
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
                    "`/ambition` - Set long-term goals\n"
                    "`/desire` - Set short-term goals\n"
                    "`/drive` - Set hunting motivation\n"
                    "`/damage` - Apply damage\n"
                    "`/heal` - Heal damage"
                ),
                inline=False
            )
            
            embed.add_field(
                name="🎒 Extras",
                value=(
                    "`/equipment` - Manage character equipment\n"
                    "`/notes` - Manage character notes/journal\n"
                    "`/help` - This help system"
                ),
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ===== AUTOCOMPLETE FUNCTIONS =====

    @skill_set.autocomplete('character_name')
    @skill_template.autocomplete('character')
    @skill_bulk.autocomplete('character')
    @specialty.autocomplete('character')
    @specialty_bulk.autocomplete('character')
    @experience_points.autocomplete('character')
    @spend_xp.autocomplete('character')
    @xp_log.autocomplete('character')
    async def progression_character_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> List[app_commands.Choice[str]]:
        """Autocomplete character names for progression commands"""
        return await character_autocomplete(interaction, current)

    @specialty.autocomplete('skill')
    async def specialty_skill_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> List[app_commands.Choice[str]]:
        """Autocomplete skill names with more options than choices allow"""
        # Filter skills based on current input
        filtered = [
            skill for skill in ALL_SKILLS 
            if current.lower() in skill.lower()
        ]
        
        return [
            app_commands.Choice(name=skill, value=skill)
            for skill in filtered[:25]  # Discord limit
        ]

    @specialty.autocomplete('specialty')
    async def specialty_name_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> List[app_commands.Choice[str]]:
        """Autocomplete existing specialty names for removal"""
        # Only provide autocomplete for remove action
        if not hasattr(interaction, 'namespace') or interaction.namespace.action != "remove":
            return []
        
        try:
            user_id = str(interaction.user.id)
            character = getattr(interaction.namespace, 'character', None)
            skill = getattr(interaction.namespace, 'skill', None)
            
            if not character or not skill:
                return []
            
            # Find character using fuzzy matching
            char = await find_character(user_id, character)
            if not char:
                return []
            
            conn = get_db_connection()
            cur = conn.cursor()
            
            cur.execute("""
                SELECT specialty_name 
                FROM specialties 
                WHERE user_id = ? AND character_name = ? AND skill_name = ?
                ORDER BY specialty_name
            """, (user_id, char['name'], skill))
            specialties = cur.fetchall()
            conn.close()
            
            filtered = [
                spec['specialty_name'] for spec in specialties 
                if current.lower() in spec['specialty_name'].lower()
            ]
            
            return [
                app_commands.Choice(name=specialty_name, value=specialty_name)
                for specialty_name in filtered[:25]
            ]
        except Exception as e:
            logger.error(f"Error in specialty name autocomplete: {e}")
            return []

    @spend_xp.autocomplete('target')
    async def spend_xp_target_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> List[app_commands.Choice[str]]:
        """Autocomplete attribute and skill names for spending XP"""
        # Get the improvement type to filter appropriately
        improvement_type = None
        if hasattr(interaction, 'namespace') and hasattr(interaction.namespace, 'improvement_type'):
            improvement_type = interaction.namespace.improvement_type
        
        targets = []
        
        if improvement_type == "attribute" or improvement_type is None:
            attributes = ["Strength", "Dexterity", "Stamina", "Charisma", "Manipulation", "Composure", "Intelligence", "Wits", "Resolve"]
            targets.extend(attributes)
        
        if improvement_type == "skill" or improvement_type is None:
            targets.extend(ALL_SKILLS)
        
        # Filter based on current input
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
    
    # Only register guild commands if GUILD_ID is set (development mode)
    if GUILD_ID:
        for command in cog.get_app_commands():
            bot.tree.add_command(command, guild=discord.Object(id=GUILD_ID))
        logger.info(f"Character Progression cog loaded with {len(cog.get_app_commands())} guild commands")
    else:
        logger.info(f"Character Progression cog loaded with {len(cog.get_app_commands())} global commands")

#==== End of Part 5 ====
