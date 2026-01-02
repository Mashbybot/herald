"""
Character Management Cog for Herald Bot
Handles basic character CRUD operations: create, delete, list, sheet display

CONVERTED TO ASYNC POSTGRESQL - All database operations now use async/await patterns
"""

import discord
from discord import app_commands
from discord.ext import commands
from typing import List
import logging

from core.db import get_async_db
from core.character_utils import (
    find_character, character_autocomplete, get_character_and_skills,
    ensure_h5e_columns, ALL_SKILLS, H5E_SKILLS, get_active_character,
    set_active_character
)
from core.ui_utils import create_health_bar, create_willpower_bar, HeraldColors, HeraldMessages
from config.settings import GUILD_ID

logger = logging.getLogger('Herald.Character.Management')


def safe_get_character_field(character, field, default=None):
    """Safely get a field from database row with default value"""
    try:
        value = character[field]
        return value if value is not None else default
    except (KeyError, IndexError):
        return default


class CharacterSelectionView(discord.ui.View):
    """Interactive button view for selecting active character"""

    def __init__(self, user_id: str, characters: List[dict], active_character_name: str = None, timeout: float = 60):
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.selected_character = None

        # Dynamically create buttons for each character
        for i, char in enumerate(characters):
            char_name = char['name']
            # Use different style for active character
            is_active = active_character_name and char_name == active_character_name
            style = discord.ButtonStyle.success if is_active else discord.ButtonStyle.secondary
            label = f"{char_name}" + (" (Active)" if is_active else "")

            # All buttons use Herald's orange diamond emoji
            button = discord.ui.Button(
                label=label,
                style=style,
                emoji="🔸",
                custom_id=f"char_{i}"
            )
            button.callback = self._create_callback(char_name)
            self.add_item(button)

    def _create_callback(self, character_name: str):
        """Create a callback function for a specific character"""
        async def callback(interaction: discord.Interaction):
            await self._select_character(interaction, character_name)
        return callback

    async def _select_character(self, interaction: discord.Interaction, character_name: str):
        """Handle character selection"""
        try:
            from core.character_utils import set_active_character

            # Set the active character
            success = await set_active_character(self.user_id, character_name)

            if not success:
                await interaction.response.send_message(
                    f"❌ Error setting active character to **{character_name}**",
                    ephemeral=True
                )
                return

            # Create success embed
            embed = discord.Embed(
                title="🔸 Active Character Set",
                description=f"Now playing as **{character_name}**\n\nAll commands will now default to this character",
                color=HeraldColors.ORANGE
            )

            embed.add_field(
                name="💡 Tip",
                value="Use `/character` to switch between your characters at any time",
                inline=False
            )

            # Disable all buttons
            for item in self.children:
                item.disabled = True

            await interaction.response.edit_message(embed=embed, view=self)
            logger.info(f"User {self.user_id} set active character to: {character_name}")

        except Exception as e:
            logger.error(f"Error selecting character: {e}")
            await interaction.response.send_message(
                f"❌ Error setting active character: {str(e)}",
                ephemeral=True
            )

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Ensure only the original user can interact"""
        return str(interaction.user.id) == self.user_id

    async def on_timeout(self):
        """Handle timeout"""
        for item in self.children:
            item.disabled = True


class DeleteConfirmationView(discord.ui.View):
    """Confirmation view for character deletion"""

    def __init__(self, user_id: str, character_name: str, timeout: float = 30):
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.character_name = character_name
        self.confirmed = False
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Ensure only the original user can interact"""
        return str(interaction.user.id) == self.user_id
    
    @discord.ui.button(label="Delete Character", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def confirm_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Confirm and execute character deletion"""
        try:
            
            async with get_async_db() as conn:
                # PostgreSQL returns "DELETE N" where N is the number of deleted rows
                result = await conn.execute(
                    "DELETE FROM characters WHERE user_id = $1 AND name = $2",
                    self.user_id, self.character_name
                )
                
                # Parse the row count from the result string
                rows_deleted = int(result.split()[-1]) if result else 0
                
                if rows_deleted == 0:
                    await interaction.response.send_message(
                        "⚠️ Character not found or already deleted", ephemeral=True
                    )
                    return
            

            embed = discord.Embed(
                title=f"🔸 Pattern purged: {self.character_name}",
                description=f"**{self.character_name}** has been permanently deleted",
                color=HeraldColors.SUCCESS
            )

            embed.add_field(
                name="Data Removed",
                value="• Character sheet\n• All skill ratings\n• Equipment and notes",
                inline=False
            )
            
            # Disable all buttons
            for item in self.children:
                item.disabled = True
            
            await interaction.response.edit_message(embed=embed, view=self)
            logger.info(f"Deleted character '{self.character_name}' for user {self.user_id}")
            
        except Exception as e:
            logger.error(f"Error deleting character: {e}")
            await interaction.response.send_message(
                f"❌ Error deleting character: {str(e)}", ephemeral=True
            )
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel character deletion"""
        embed = discord.Embed(
            title="❌ Deletion Cancelled",
            description=f"**{self.character_name}** was not deleted",
            color=0x4169E1
        )
        
        # Disable all buttons
        for item in self.children:
            item.disabled = True
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def on_timeout(self):
        """Handle timeout"""
        # Disable all buttons when timeout occurs
        for item in self.children:
            item.disabled = True


class EdgeButtonView(discord.ui.View):
    """Interactive orange button view for character edges"""

    # Edge pool information for each edge
    EDGE_POOLS = {
        "Arsenal": "Intelligence + Craft (or Manipulation + Streetwise for contacts)",
        "Fleet": "Manipulation + Streetwise (or Technology)",
        "Ordnance": "Composure + Science (or Composure + Streetwise)",
        "Library": "Resolve + Academics",
        "Experimental Medicine": "Stamina + Medicine (or Composure + Medicine)",
        "Improvised Gear": "Intelligence + Craft/Technology/Science",
        "Global Access": "Intelligence + Technology",
        "Drone Jockey": "Wits + Technology (or Intelligence + Craft)",
        "Beast Whisperer": "Composure + Animal Ken",
        "Turncoat": "Manipulation + Subterfuge (or Intelligence + Wits)",
        "Sense the Unnatural": "Composure + Resolve (or Wits + Insight)",
        "Repel the Unnatural": "Composure + Resolve (varies by Endowment)",
        "Thwart the Unnatural": "Based on Endowment nature",
        "Artifact": "Intelligence + Occult (or Science)",
        "Cleanse the Unnatural": "Charisma + Persuasion (or Resolve + Science, or Manipulation + Occult)",
        "Great Destiny": "Creates a pool of 2 dice at start of session",
        "Unnatural Changes": "Stamina/Composure/Resolve + Insight"
    }

    def __init__(self, edges: List[dict], timeout: float = 180):
        super().__init__(timeout=timeout)

        # Dynamically create orange buttons for each edge (max 25 buttons)
        for i, edge in enumerate(edges[:25]):  # Discord limit
            edge_name = edge.get('edge_name', 'Unknown')
            button = discord.ui.Button(
                label=edge_name,
                style=discord.ButtonStyle.secondary,  # Orange/gray style
                custom_id=f"edge_{i}",
                emoji="🔸",
                row=i // 5  # 5 buttons per row
            )
            button.callback = self._create_edge_callback(edge)
            self.add_item(button)

    def _create_edge_callback(self, edge: dict):
        """Create callback for edge button"""
        async def edge_button_callback(interaction: discord.Interaction):
            edge_name = edge.get('edge_name', 'Unknown')
            edge_desc = edge.get('description', 'No description available')
            edge_pool = self.EDGE_POOLS.get(edge_name, "See rulebook for dice pool")

            embed = discord.Embed(
                title=f"🔸 {edge_name}",
                description=edge_desc,
                color=0xFFA500  # Orange
            )

            embed.add_field(
                name="🎲 Dice Pool",
                value=edge_pool,
                inline=False
            )

            embed.set_footer(text="Use /roll to make an Edge test with the appropriate pool")

            await interaction.response.send_message(embed=embed, ephemeral=True)

        return edge_button_callback


class CharacterManagement(commands.Cog):
    """Character Management - Basic CRUD operations for Hunter characters"""
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger('Herald.Character.Management')

    @app_commands.command(name="create", description="Create your Hunter character sheet")
    @app_commands.describe(
        name="Character name",
        strength="Strength (1-5, default: 1)",
        dexterity="Dexterity (1-5, default: 1)",
        stamina="Stamina (1-5, default: 1)",
        charisma="Charisma (1-5, default: 1)",
        manipulation="Manipulation (1-5, default: 1)",
        composure="Composure (1-5, default: 1)",
        intelligence="Intelligence (1-5, default: 1)",
        wits="Wits (1-5, default: 1)",
        resolve="Resolve (1-5, default: 1)",
        ambition="Long-term goal (recovers aggravated willpower damage)",
        desire="Short-term goal (recovers superficial willpower damage)",
        drive="Why you hunt the supernatural"
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
        ambition: str = None,
        desire: str = None,
        drive: str = None,
    ):
        """Create a new Hunter character"""
        user_id = str(interaction.user.id)
        
        # Validate attribute ranges
        attributes = {
            "Strength": strength, "Dexterity": dexterity, "Stamina": stamina,
            "Charisma": charisma, "Manipulation": manipulation, "Composure": composure,
            "Intelligence": intelligence, "Wits": wits, "Resolve": resolve
        }
        
        for attr_name, value in attributes.items():
            if not 1 <= value <= 5:
                await interaction.response.send_message(
                    f"❌ {attr_name} must be between 1 and 5 (got {value})", ephemeral=True
                )
                return
        
        # Validate character name
        if len(name) < 2 or len(name) > 32:
            await interaction.response.send_message(
                "❌ Character name must be between 2 and 32 characters", ephemeral=True
            )
            return

        # Validate optional text fields
        if ambition and len(ambition) > 200:
            await interaction.response.send_message(
                "❌ Ambition must be 200 characters or less", ephemeral=True
            )
            return
        
        if desire and len(desire) > 200:
            await interaction.response.send_message(
                "❌ Desire must be 200 characters or less", ephemeral=True
            )
            return
            
        if drive and len(drive) > 200:
            await interaction.response.send_message(
                "❌ Drive must be 200 characters or less", ephemeral=True
            )
            return
        
        try:
            
            async with get_async_db() as conn:
                await ensure_h5e_columns()

                existing = await conn.fetchrow(
                    "SELECT name FROM characters WHERE user_id = $1 AND name = $2",
                    user_id, name
                )
                
                if existing:
                    await interaction.response.send_message(
                        f"⚠️ You already have a character named **{name}**", ephemeral=True
                    )
                    return

                # Calculate derived stats (H5E rules)
                health = stamina + 3
                willpower = resolve + composure

                # Create character with H5E mechanics
                # NOTE: PostgreSQL uses $1, $2, $3... instead of ?
                # Parameters are passed directly, not in a tuple
                await conn.execute("""
                    INSERT INTO characters (
                        user_id, name,
                        strength, dexterity, stamina,
                        charisma, manipulation, composure,
                        intelligence, wits, resolve,
                        health, willpower,
                        health_sup, health_agg,
                        willpower_sup, willpower_agg,
                        ambition, desire, drive
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, 0, 0, 0, 0, $14, $15, $16)
                """,
                    user_id, name,
                    strength, dexterity, stamina,
                    charisma, manipulation, composure,
                    intelligence, wits, resolve,
                    health, willpower,
                    ambition, desire, drive
                )

                # Initialize all skills at 0
                # Multiple INSERTs - do them in a loop with await
                for skill in ALL_SKILLS:
                    await conn.execute(
                        "INSERT INTO skills (user_id, character_name, skill_name, dots) VALUES ($1, $2, $3, 0)",
                        user_id, name, skill
                    )

            # Success response with Herald's voice
            embed = discord.Embed(
                title="🔸 Hunter Identified",
                description=(
                    f"{HeraldMessages.QUERY_RECOGNIZED}: Hunter identified\n"
                    f"{HeraldMessages.PROTOCOL_ESTABLISHED}: {name}\n"
                    f"{HeraldMessages.PATTERN_LOGGED}: Ready for deployment"
                ),
                color=HeraldColors.ORANGE
            )

            # Physical attributes
            embed.add_field(
                name="Physical",
                value=f"💪 Strength: {strength}\n🤸 Dexterity: {dexterity}\n❤️ Stamina: {stamina}",
                inline=True
            )

            # Social attributes
            embed.add_field(
                name="Social",
                value=f"✨ Charisma: {charisma}\n🎭 Manipulation: {manipulation}\n🧘 Composure: {composure}",
                inline=True
            )

            # Mental attributes
            embed.add_field(
                name="Mental",
                value=f"🧠 Intelligence: {intelligence}\n⚡ Wits: {wits}\n🎯 Resolve: {resolve}",
                inline=True
            )

            # Derived stats
            embed.add_field(
                name="Derived Stats",
                value=f"❤️ Health: {health}\n💙 Willpower: {willpower}",
                inline=False
            )

            # Touchstones (if provided)
            if ambition or desire or drive:
                touchstones_text = []
                if ambition:
                    touchstones_text.append(f"**Ambition:** {ambition}")
                if desire:
                    touchstones_text.append(f"**Desire:** {desire}")
                if drive:
                    touchstones_text.append(f"**Drive:** {drive}")

                embed.add_field(
                    name="Touchstones",
                    value="\n".join(touchstones_text),
                    inline=False
                )

            embed.set_footer(text=HeraldMessages.CATCHPHRASE)
            
            await interaction.response.send_message(embed=embed)
            self.logger.info(f"Created character '{name}' for user {user_id}")
            
        except Exception as e:
            self.logger.error(f"Error creating character: {e}", exc_info=True)
            await interaction.response.send_message(
                f"❌ Error creating character: {str(e)}", ephemeral=True
            )

    @app_commands.command(name="delete", description="Delete your active character")
    async def delete_character(self, interaction: discord.Interaction):
        """Delete active character with confirmation"""
        user_id = str(interaction.user.id)

        try:
            # Get active character
            active_char_name = await get_active_character(user_id)
            if not active_char_name:
                await interaction.response.send_message(
                    f"{HeraldEmojis.ERROR} No active character set. Use `/character` to set your active character first.",
                    ephemeral=True
                )
                return

            character = await find_character(user_id, active_char_name)

            if not character:
                await interaction.response.send_message(
                    f"{HeraldEmojis.ERROR} Active character '{active_char_name}' not found.",
                    ephemeral=True
                )
                return
            
            # Create confirmation view
            view = DeleteConfirmationView(user_id, character['name'], timeout=30)
            
            embed = discord.Embed(
                title="⚠️ Confirm Character Deletion",
                description=f"Are you sure you want to delete **{character['name']}**?",
                color=0xFF4444
            )
            
            embed.add_field(
                name="⚠️ Warning",
                value="This action cannot be undone! All character data will be permanently lost.",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            self.logger.error(f"Error initiating character deletion: {e}")
            await interaction.response.send_message(
                f"❌ Error: {str(e)}", ephemeral=True
            )

    @app_commands.command(name="character", description="View and switch between your characters")
    async def set_character(self, interaction: discord.Interaction):
        """Display all characters as clickable buttons for selection"""
        user_id = str(interaction.user.id)

        try:
            # Fetch all user's characters
            async with get_async_db() as conn:
                characters = await conn.fetch(
                    "SELECT name FROM characters WHERE user_id = $1 ORDER BY name",
                    user_id
                )

            if not characters:
                await interaction.response.send_message(
                    "📝 You don't have any characters yet. Use `/create` to make one!",
                    ephemeral=True
                )
                return

            # Get active character
            active_char_name = await get_active_character(user_id)

            # Create selection view
            view = CharacterSelectionView(user_id, characters, active_char_name)

            # Build character list for embed description
            char_list = []
            for char in characters:
                if active_char_name and char['name'] == active_char_name:
                    char_list.append(f"🔸 **{char['name']}** (Active)")
                else:
                    char_list.append(f"• {char['name']}")

            embed = discord.Embed(
                title="🔸 Your Hunters",
                description="Select a character to set as your active Hunter:\n\n" + "\n".join(char_list),
                color=HeraldColors.ORANGE
            )

            if active_char_name:
                embed.add_field(
                    name="💡 Current Active",
                    value=f"Commands currently default to **{active_char_name}**",
                    inline=False
                )
            else:
                embed.add_field(
                    name="💡 No Active Character",
                    value="Select a character below to set as active",
                    inline=False
                )

            await interaction.response.send_message(embed=embed, view=view)

        except Exception as e:
            self.logger.error(f"Error displaying character selection: {e}")
            await interaction.response.send_message(
                f"❌ Error loading characters: {str(e)}",
                ephemeral=True
            )

    @app_commands.command(name="sheet", description="View your active Hunter character sheet")
    async def character_sheet(self, interaction: discord.Interaction):
        """Display character sheet for active character"""
        user_id = str(interaction.user.id)

        try:
            # Import the enhanced character sheet creator and edge/perk fetchers
            from core.character_utils import (
                create_enhanced_character_sheet,
                get_character_edges,
                get_character_perks
            )

            # Get active character
            active_char_name = await get_active_character(user_id)
            if not active_char_name:
                await interaction.response.send_message(
                    f"{HeraldEmojis.ERROR} No active character set. Use `/character` to set your active character.",
                    ephemeral=True
                )
                return

            # Get character and skills
            character, skills = await get_character_and_skills(user_id, active_char_name)

            if not character:
                await interaction.response.send_message(
                    f"{HeraldEmojis.ERROR} Active character '{active_char_name}' not found.",
                    ephemeral=True
                )
                return

            # Get edges and perks
            edges = await get_character_edges(user_id, character['name'])
            perks = await get_character_perks(user_id, character['name'])

            # Create enhanced character sheet with all features
            embed = create_enhanced_character_sheet(character, skills, edges, perks)

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            self.logger.error(f"Error displaying character sheet: {e}", exc_info=True)
            await interaction.response.send_message(
                f"❌ Error loading character sheet: {str(e)}", ephemeral=True
            )

    @app_commands.command(name="about", description="About Herald - Hunter character management system")
    async def about_command(self, interaction: discord.Interaction):
        """Display information about Herald bot"""

        # Get character count for this guild if possible
        try:
            async with get_async_db() as conn:
                char_count = await conn.fetchval(
                    "SELECT COUNT(*) FROM characters"
                )
        except Exception:
            char_count = "Unknown"

        embed = discord.Embed(
            title="🔸 Herald the Reckoning",
            description=(
                f"{HeraldMessages.PROTOCOL_ESTABLISHED}\n"
                f"{HeraldMessages.QUERY_RECOGNIZED}: System information requested\n\n"
                "**Mission:** Herald the Reckoning\n\n"
                "Built by Hunters, for Hunters.\n"
                "The Reckoning doesn't wait for official tools.\n"
            ),
            color=HeraldColors.ORANGE
        )

        embed.add_field(
            name="🔸 System Status",
            value=(
                f"**Version:** 2.0\n"
                f"**Active Hunters:** {char_count}\n"
                f"**Database:** PostgreSQL (Async)\n"
                f"**Engine:** Hunter: The Reckoning 5E"
            ),
            inline=False
        )

        embed.add_field(
            name="🔸 Core Operations",
            value=(
                "• Character management\n"
                "• Dice rolling (H5E mechanics)\n"
                "• Edge & Desperation tracking\n"
                "• Experience & progression\n"
                "• Equipment & notes"
            ),
            inline=True
        )

        embed.add_field(
            name="🔸 Investigation",
            value=(
                "Some truths are earned through investigation.\n\n"
                "Use `/help` to access operational protocols."
            ),
            inline=False
        )

        embed.set_footer(text=HeraldMessages.CATCHPHRASE)

        await interaction.response.send_message(embed=embed)



async def setup(bot: commands.Bot):
    """Setup function for the Character Management cog"""
    cog = CharacterManagement(bot)
    await bot.add_cog(cog)
    logger.info(f"Character Management cog loaded with {len(cog.get_app_commands())} commands")
