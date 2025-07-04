import discord
from discord.ext import commands
from config.settings import DISCORD_TOKEN
from core.db import init_db

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Bot is live as {bot.user}")
    init_db()
    try:
        guild = discord.Object(id=1388201771532554390)
        synced = await bot.tree.sync(guild=guild)
        print(f"🔁 Synced {len(synced)} commands to guild {guild.id}")
    except Exception as e:
        print(f"❌ Error syncing commands: {e}")

async def main():
    await bot.load_extension("cogs.roll")
    await bot.load_extension("cogs.character")
    await bot.start(DISCORD_TOKEN)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
