import discord
from discord import app_commands
from discord.ext import commands

from core.db import get_db_connection

class Character(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="create_sheet", description="Create your Hunter character sheet")
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
    async def create_sheet(
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
                    intelligence, wits, resolve
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id, name,
                strength, dexterity, stamina,
                charisma, manipulation, composure,
                intelligence, wits, resolve
            ))

            conn.commit()
            conn.close()

            await interaction.response.send_message(
                f"✅ Character sheet for **{name}** created!", ephemeral=True
            )

        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error creating character: `{str(e)}`", ephemeral=True
            )

    @app_commands.command(name="sheet", description="View your Hunter character sheet")
    @app_commands.describe(name="Name of the character to view")
    async def sheet(
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
            conn.close()

            if not character:
                await interaction.response.send_message(
                    f"⚠ No character named **{name}** found for you.", ephemeral=True
                )
                return

            msg = (
                f"**Character Sheet: {character['name']}**\n"
                f"Strength: {character['strength']}\n"
                f"Dexterity: {character['dexterity']}\n"
                f"Stamina: {character['stamina']}\n"
                f"Charisma: {character['charisma']}\n"
                f"Manipulation: {character['manipulation']}\n"
                f"Composure: {character['composure']}\n"
                f"Intelligence: {character['intelligence']}\n"
                f"Wits: {character['wits']}\n"
                f"Resolve: {character['resolve']}\n"
            )

            await interaction.response.send_message(msg, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error fetching character sheet: `{str(e)}`", ephemeral=True
            )

async def setup(bot: commands.Bot):
    cog = Character(bot)
    await bot.add_cog(cog)
