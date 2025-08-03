import discord
from discord import app_commands
from discord.ext import commands

from core.db import get_db_connection

# List of H5e Skills for choices in the skill_set command
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

class Character(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="create", description="Create your Hunter character sheet")
    @app_commands.describe(
        name="Character name",
        strength="Strength (default: 1)",
        dexterity="Dexterity (default: 1)",
        stamina="Stamina (default: 1)",
        charisma="Charisma (default: 1)",
        manipulation="Manipulation (default: 1)",
        composure="Composure (default: 1)",
        intelligence="Intelligence (default: 1)",
        wits="Wits (default: 1)",
        resolve="Resolve (default: 1)",
    )
    async def create_character(
        self,
        interaction: discord.Interaction,
        name: str,
        strength: int = 1,
        dexterity: int = 1,
        stamina: int = 1,
        charisma: int = 1,
        manipulation: int = 1,
        composure: int = 1,
        intelligence: int = 1,
        wits: int = 1,
        resolve: int = 1,
    ):
        print(f"[DEBUG] Received /create command from {interaction.user} ({interaction.user.id})")
        user_id = str(interaction.user.id)
        try:
            conn = get_db_connection()
            cur = conn.cursor()

            cur.execute("SELECT * FROM characters WHERE user_id = ? AND name = ?", (user_id, name))
            existing = cur.fetchone()

            if existing:
                await interaction.response.send_message(
                    f"⚠ You already have a character named **{name}**.", ephemeral=True
                )
                return

            cur.execute("""
                INSERT INTO characters (
                    user_id, name,
                    strength, dexterity, stamina,
                    charisma, manipulation, composure,
                    intelligence, wits, resolve,
                    health, willpower
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id, name,
                strength, dexterity, stamina,
                charisma, manipulation, composure,
                intelligence, wits, resolve,
                stamina,  # Health = stamina at creation
                resolve + composure  # Willpower = resolve + composure
            ))

            # Insert default skills (all 0 dots)
            for skill in H5E_SKILLS:
                cur.execute("""
                    INSERT INTO skills (user_id, character_name, skill_name, dots)
                    VALUES (?, ?, ?, 0)
                """, (user_id, name, skill))

            conn.commit()
            conn.close()

            await interaction.response.send_message(
                f"✅ Character sheet for **{name}** created with default skills!", ephemeral=True
            )

        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error creating character: `{str(e)}`", ephemeral=True
            )

    @app_commands.command(name="sheet", description="View your Hunter character sheet")
    @app_commands.describe(name="Name of the character to view")
    async def character_sheet(
        self,
        interaction: discord.Interaction,
        name: str,
    ):
        user_id = str(interaction.user.id)
        try:
            conn = get_db_connection()
            cur = conn.cursor()

            cur.execute("SELECT * FROM characters WHERE user_id = ? AND name = ?", (user_id, name))
            character = cur.fetchone()

            if not character:
                await interaction.response.send_message(
                    f"⚠ No character named **{name}** found for you.", ephemeral=True
                )
                conn.close()
                return

            cur.execute(
                "SELECT skill_name, dots FROM skills WHERE user_id = ? AND character_name = ? ORDER BY skill_name ASC",
                (user_id, name)
            )
            skills = cur.fetchall()
            conn.close()

            skill_lines = [f"{row['skill_name']}: {row['dots']}" for row in skills]

            msg = (
                f"**Character Sheet: {character['name']}**\n"
                f"Health: {character['health']}\n"
                f"Willpower: {character['willpower']}\n\n"
                f"Strength: {character['strength']}\n"
                f"Dexterity: {character['dexterity']}\n"
                f"Stamina: {character['stamina']}\n"
                f"Charisma: {character['charisma']}\n"
                f"Manipulation: {character['manipulation']}\n"
                f"Composure: {character['composure']}\n"
                f"Intelligence: {character['intelligence']}\n"
                f"Wits: {character['wits']}\n"
                f"Resolve: {character['resolve']}\n\n"
                f"**Skills:**\n" + "\n".join(skill_lines)
            )

            await interaction.response.send_message(msg, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error fetching character sheet: `{str(e)}`", ephemeral=True
            )

    @app_commands.command(name="skill_set", description="Set dots for a skill on your character")
    @app_commands.describe(
        character_name="Name of your character",
        skill="Skill to update",
        dots="Dots to assign (0–5)"
    )
    @app_commands.choices(skill=[
        app_commands.Choice(name=skill, value=skill)
        for skill in H5E_SKILLS[:25]  # Discord max choices = 25
    ])
    async def skill_set(
        self,
        interaction: discord.Interaction,
        character_name: str,
        skill: str,
        dots: int,
    ):
        user_id = str(interaction.user.id)
        dots = max(0, min(dots, 5))  # Clamp between 0 and 5

        try:
            conn = get_db_connection()
            cur = conn.cursor()

            cur.execute("SELECT * FROM characters WHERE user_id = ? AND name = ?", (user_id, character_name))
            character = cur.fetchone()
            if not character:
                await interaction.response.send_message(
                    f"⚠ Character **{character_name}** not found.", ephemeral=True
                )
                conn.close()
                return

            cur.execute(
                "SELECT * FROM skills WHERE user_id = ? AND character_name = ? AND skill_name = ?",
                (user_id, character_name, skill)
            )
            skill_row = cur.fetchone()
            if not skill_row:
                await interaction.response.send_message(
                    f"⚠ Skill **{skill}** not found on character **{character_name}**.", ephemeral=True
                )
                conn.close()
                return

            cur.execute(
                "UPDATE skills SET dots = ? WHERE user_id = ? AND character_name = ? AND skill_name = ?",
                (dots, user_id, character_name, skill)
            )
            conn.commit()
            conn.close()

            await interaction.response.send_message(
                f"✅ Skill **{skill}** on **{character_name}** set to {dots} dots.", ephemeral=True
            )

        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error setting skill dots: `{str(e)}`", ephemeral=True
            )

async def setup(bot: commands.Bot):
    cog = Character(bot)
    await bot.add_cog(cog)

    # Register each app command with the command tree
    for command in cog.get_app_commands():
        bot.tree.add_command(command, guild=discord.Object(id=1388201771532554390))

    print("[DEBUG] Character cog loaded with commands:", [cmd.name for cmd in cog.get_app_commands()])
