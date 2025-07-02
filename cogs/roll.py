import nextcord
from nextcord.ext import commands
from nextcord import Interaction, SlashOption
from core.dice import roll_pool

class RollCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @nextcord.slash_command(name="roll", description="Roll a Hunter dice pool")
    async def roll(
        self,
        interaction: Interaction,
        attribute: int = SlashOption(description="Attribute dice", required=True),
        skill: int = SlashOption(description="Skill dice", required=True),
        desperation: bool = SlashOption(description="Use desperation?", required=False, default=False)
    ):
        result = roll_pool(attribute, skill, desperation)
        dice_str = " ".join(str(d) for d in result["dice"])
        await interaction.response.send_message(
            f"🎲 Rolled: {dice_str}\n✅ Successes: {result['successes']} (Crits: {result['crits']})"
        )

def setup(bot):
    bot.add_cog(RollCog(bot))
