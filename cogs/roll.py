import discord
from discord.ext import commands
from discord import app_commands
from core.dice import roll_pool

class RollCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="roll", description="Roll a Hunter dice pool")
    @app_commands.describe(
        attribute="Attribute dice",
        skill="Skill dice",
        desperation="Use desperation?"
    )
    async def roll(
        self,
        interaction: discord.Interaction,
        attribute: int,
        skill: int,
        desperation: bool = False
    ):
        result = roll_pool(attribute, skill, desperation)
        dice_str = " ".join(str(d) for d in result["dice"])
        await interaction.response.send_message(
            f"🎲 Rolled: {dice_str}\n✅ Successes: {result['successes']} (Crits: {result['crits']})"
        )

async def setup(bot):
    await bot.add_cog(RollCog(bot))
