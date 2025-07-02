import nextcord
from nextcord.ext import commands
from config.settings import DISCORD_TOKEN
from core.db import init_db

intents = nextcord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Bot is live as {bot.user}")
    init_db()

# Load all cogs
bot.load_extension("cogs.roll")

bot.run(DISCORD_TOKEN)
