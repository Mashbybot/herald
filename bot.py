import discord
from discord.ext import commands
from config.settings import DISCORD_TOKEN
from core.db import init_db

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

has_synced = False  # Flag to ensure syncing happens only once

@bot.event
async def on_ready():
    global has_synced
    print(f"Bot is live as {bot.user}")
    init_db()

    if not has_synced:
        try:
            # Force fetch application info so application_id is set
            await bot.application_info()

            guild = discord.Object(id=1388201771532554390)  # Replace with your guild ID

            # Uncomment the following lines once to clear old guild commands if needed
#            await bot.tree.clear_commands(guild=guild)
#            print("🧹 Cleared guild commands")

            synced = await bot.tree.sync(guild=guild)
            print(f"🔁 Synced {len(synced)} commands to guild {guild.id}")

            has_synced = True
        except Exception as e:
            print(f"❌ Error syncing commands: {e}")

async def main():
    print("🔧 Loading roll cog")
    await bot.load_extension("cogs.roll")
    print("✅ Roll cog loaded")

    print("🔧 Loading character cog")
    await bot.load_extension("cogs.character")
    print("✅ Character cog loaded")

    await bot.start(DISCORD_TOKEN)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

@bot.event
async def on_interaction(interaction: discord.Interaction):
    print(f"[DEBUG] Received interaction: {interaction.data}")
