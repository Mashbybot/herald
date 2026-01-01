# Herald Bot - Complete System Documentation

> **Purpose:** This document provides a comprehensive technical overview of Herald, a Discord bot for Hunter: The Reckoning 5th Edition gameplay. Use this as a reference for building documentation websites or understanding Herald's complete feature set.

**Project Repository:** https://github.com/Mashbybot/herald
**License:** MIT
**Python Version:** 3.11+
**Framework:** discord.py 2.x
**Database:** PostgreSQL (async with asyncpg)

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [Slash Commands Reference](#slash-commands-reference)
4. [Hunter 5E Game Mechanics](#hunter-5e-game-mechanics)
5. [Database Schema](#database-schema)
6. [UI/UX Patterns](#uiux-patterns)
7. [Edge and Perks System](#edge-and-perks-system)
8. [Dice Rolling System](#dice-rolling-system)

---

## System Overview

### What is Herald?

Herald is a Discord bot that provides comprehensive character management and dice rolling for **Hunter: The Reckoning 5th Edition** (H5E). It implements all core H5E mechanics including:

- Character creation and management
- H5E-specific dice mechanics (Edge, Desperation, messy criticals)
- Complete attribute and skill tracking
- Hunter-specific systems (Creeds, Drives, Edges, Perks)
- Damage tracking (Health and Willpower with Superficial/Aggravated)
- Experience point management
- Active character system (set one character as "active" for quick command access)

### Design Philosophy

- **Zero setup required** - Add bot, create character, start playing
- **H5E mechanical accuracy** - All game mechanics work per the rulebook
- **Privacy-focused** - PostgreSQL database, no external data collection
- **Herald's Voice** - Bot uses analytical, present-tense language with 🔸 diamond branding

---

## Architecture

### Tech Stack

```
Language:     Python 3.11+
Framework:    discord.py 2.x (slash commands only)
Database:     PostgreSQL (asyncpg for async operations)
Deployment:   Railway (hosted version)
Structure:    Cog-based modular system
```

### Project Structure

```
herald/
├── bot.py                          # Main bot entry point
├── cogs/
│   ├── character_management.py     # /create, /delete, /character, /sheet
│   ├── dice_rolling.py             # /roll, /danger
│   ├── character_progression.py    # /skill_set, /specialty, /xp, /attributes, /help
│   ├── character_gameplay.py       # /damage, /heal, /creed, /edge, /perks, /drive, etc.
│   └── character_inventory.py      # (equipment/notes - not actively used)
├── core/
│   ├── db.py                       # PostgreSQL async database layer
│   ├── dice.py                     # H5E dice mechanics
│   ├── dice_utils.py               # Dice formatting utilities
│   ├── character_utils.py          # Character database operations, caching
│   ├── ui_utils.py                 # Emojis, colors, embed creation
│   ├── validation.py               # Input validation
│   └── constants.py                # Configuration constants
├── data/
│   └── perks.py                    # All Edge Perks organized by Edge
└── config/
    └── settings.py                 # Environment configuration
```

### Key Architectural Features

1. **Async/Await Throughout** - All database operations use async PostgreSQL
2. **Caching System** - LRU cache for character data (5-minute TTL)
3. **Active Character System** - Users set one character as "active" for streamlined commands
4. **Modular Cog System** - Features organized by category
5. **Herald's Voice** - Consistent messaging system with analytical tone

---

## Slash Commands Reference

### Character Management (`character_management.py`)

#### `/create`
**Description:** Create a new Hunter character sheet

**Parameters:**
- `name` (required): Character name (2-32 characters)
- `strength` (optional): 1-5, default 1
- `dexterity` (optional): 1-5, default 1
- `stamina` (optional): 1-5, default 1
- `charisma` (optional): 1-5, default 1
- `manipulation` (optional): 1-5, default 1
- `composure` (optional): 1-5, default 1
- `intelligence` (optional): 1-5, default 1
- `wits` (optional): 1-5, default 1
- `resolve` (optional): 1-5, default 1
- `ambition` (optional): Long-term goal, max 200 chars
- `desire` (optional): Short-term goal, max 200 chars
- `drive` (optional): Reason for hunting, max 200 chars

**Derived Stats:**
- Health = Stamina + 3
- Willpower = Resolve + Composure

**Notes:**
- Creates character with all skills initialized to 0
- Character names must be unique per user

---

#### `/character`
**Description:** View and switch between your characters

**Parameters:** None

**Behavior:**
- Displays all your characters as interactive buttons
- Shows which character is currently active
- Click a button to set that character as active
- Active character is used by default in all commands

---

#### `/sheet`
**Description:** View your active Hunter character sheet

**Parameters:** None

**Display Includes:**
- Creed, Drive, Desire, Ambition
- Health, Willpower, Desperation, Danger (all as visual bars)
- All 9 attributes with dots
- Trained skills (skills with dots > 0)
- Edges and Perks
- Despair state (if applicable)

---

#### `/delete`
**Description:** Delete your active character (with confirmation)

**Parameters:** None

**Behavior:**
- Shows confirmation dialog
- Requires button click to confirm deletion
- Permanently removes character and all associated data

---

#### `/about`
**Description:** Display information about Herald bot

**Parameters:** None

---

### Dice Rolling (`dice_rolling.py`)

#### `/roll`
**Description:** Roll dice using H5E mechanics

**Parameters:**
- `pool` (required): Total dice pool (1-20)
- `desperate` (optional): Use Desperation dice (adds character's Desperation rating)
- `difficulty` (optional): Target successes needed (0-6)
  - 0 = Automatic
  - 1 = Simple
  - 2 = Standard
  - 3 = Hard
  - 4 = Extreme
  - 5 = Nearly Impossible
  - 6 = Legendary
- `comment` (optional): Description of the roll

**H5E Mechanics:**
- Success = 6+ on a die
- Critical = Pair of 10s (adds 2 extra successes)
- Desperation dice are orange (visually distinct)
- Rolling 1s on Desperation dice = Overreach/Despair choice
- Automatic Despair if failed roll + Desperation 1s

**Visual Output:**
- Shows dice as emojis (custom Discord emojis or Unicode fallback)
- Displays margin of success/failure
- Shows thumbnails based on result type
- Warns about messy criticals, Overreach, and Despair

---

#### `/danger`
**Description:** View or manage your character's Danger rating

**Parameters:**
- `action` (required): view, set, add, subtract, reset
- `amount` (optional): Amount to modify (required for set/add/subtract)

**Danger System:**
- Range: 0-10
- Represents ongoing supernatural threats
- Adds to difficulty of all rolls
- Visual bar display: 🟥 (filled) ⚫ (empty)

---

### Character Progression (`character_progression.py`)

#### `/attributes`
**Description:** Set your character's attribute ratings

**Parameters:**
- `attribute` (required): strength, dexterity, stamina, charisma, manipulation, composure, intelligence, wits, resolve
- `dots` (required): 1-5

**Auto-Recalculation:**
- Stamina change → Health = new Stamina + 3
- Composure/Resolve change → Willpower = Composure + Resolve

---

#### `/skill_set`
**Description:** Set dots for a skill on your character

**Parameters:**
- `skill` (required): Skill name (dropdown with all 27 H5E skills)
- `dots` (required): 0-5

**Skills List:**
- **Physical:** Athletics, Brawl, Craft, Driving, Firearms, Larceny, Melee, Stealth, Survival
- **Social:** Animal Ken, Etiquette, Insight, Intimidation, Leadership, Performance, Persuasion, Streetwise, Subterfuge
- **Mental:** Academics, Awareness, Finance, Investigation, Medicine, Occult, Politics, Science, Technology

---

#### `/specialty`
**Description:** Manage skill specialties

**Parameters:**
- `action` (required): view, add, remove
- `skill` (optional): Skill name (for add/remove)
- `specialty` (optional): Specialty name (for add/remove)

**Rules:**
- Skill must have at least 1 dot to add specialty
- Max specialties = skill dots (minimum 1)
- Specialties are unique per skill

---

#### `/xp`
**Description:** View or manage experience points

**Parameters:**
- `action` (required): view, add, spend, set
- `amount` (optional): XP amount (required for add/spend/set)
- `reason` (optional): Reason for XP change

**XP System:**
- Tracks total earned and spent XP
- Available XP = Total - Spent
- Logs all XP changes with timestamps
- Shows spending guide and recent history

**Spending Costs:**
- Attributes: New rating × 4 XP
- Skills: New rating × 2 XP
- Specialties: 3 XP each
- Edges: Varies by type

---

#### `/help`
**Description:** Get help with Herald commands

**Parameters:**
- `topic` (optional): start, management, rolling, progression, mechanics, commands

**Topics:**
- **Getting Started** - Quick start guide
- **Character Management** - Creating and managing characters
- **Dice Rolling** - H5E dice mechanics
- **Skills & XP** - Character progression
- **Hunter Mechanics** - Desperation, Drive, Edges, etc.
- **All Commands** - Complete command list

---

### Character Gameplay (`character_gameplay.py`)

#### `/damage`
**Description:** Apply health or willpower damage

**Parameters:**
- `track` (required): health, willpower
- `amount` (required): Damage amount
- `damage_type` (required): superficial, aggravated

**Damage System:**
- **Superficial** - Fills available track spaces
- **Aggravated** - Converts superficial to aggravated, reduces total capacity
- Visual bars show damage types with different emojis
- Warns when track is fully damaged

---

#### `/heal`
**Description:** Heal damage from your character

**Parameters:**
- `track` (required): health, willpower
- `heal_type` (required): all, superficial, aggravated
- `amount` (optional): Amount to heal (required for superficial/aggravated)

---

#### `/desperation`
**Description:** View or modify Desperation level

**Parameters:**
- `action` (required): view, set, add, subtract
- `amount` (optional): Amount (required for set/add/subtract)

**Desperation System:**
- Range: 0-10
- At 7+: High Desperation warnings
- Used with `/roll desperate:true` to add Desperation dice
- Rolling 1s on Desperation dice triggers Overreach/Despair

---

#### `/creed`
**Description:** View or set Hunter Creed

**Parameters:**
- `action` (required): view, set

**Creeds:**
- **Entrepreneurial** (🔨) - Building, inventing, repairing
- **Faithful** (✝️) - Direct conflict with the supernatural
- **Inquisitive** (🔍) - Gaining information
- **Martial** (⚔️) - Physical conflict
- **Underground** (🎭) - Stealth and subterfuge

**Interactive Selection:**
- Shows buttons for each Creed
- Displays Creed field description

---

#### `/drive`
**Description:** View or set Hunter Drive and Redemption

**Parameters:**
- `action` (required): view, set

**Drives & Redemptions:**
- **Curiosity** (🔍) → Uncover new information about quarry
- **Vengeance** (⚔️) → Hurt your quarry
- **Oath** (🤝) → Actively uphold or fulfill oath
- **Greed** (💰) → Acquire resources from enemies
- **Pride** (👑) → Best your quarry in contest
- **Envy** (💚) → Ally with your quarry
- **Atonement** (🕊️) → Protect someone from quarry

**Interactive Selection:**
- Shows buttons for each Drive
- Automatically assigns matching Redemption

---

#### `/ambition`
**Description:** View or set long-term goal

**Parameters:**
- `ambition` (optional): Long-term goal (max 200 chars)

**Purpose:**
- Progress toward Ambition recovers Aggravated Willpower

---

#### `/desire`
**Description:** View or set short-term goal

**Parameters:**
- `desire` (optional): Short-term goal (max 200 chars)

**Purpose:**
- Accomplishing Desire recovers Superficial Willpower

---

#### `/edge`
**Description:** Manage Hunter Edges

**Parameters:**
- `action` (required): view, add, remove
- `edge_name` (optional): Edge name (dropdown with all 17 Edges)

**Edge Categories:**

**Assets (5):**
- Arsenal - Weapons and military equipment
- Fleet - Vehicles and transportation
- Ordnance - Explosives and munitions
- Library - Information and research
- Experimental Medicine - Medical experiments and healing

**Aptitudes (5):**
- Improvised Gear - Create short-lived tools
- Global Access - Digital larceny and hacking
- Drone Jockey - Control drones
- Beast Whisperer - Loyal animal companions
- Turncoat - Double agent abilities

**Endowments (7):**
- Sense the Unnatural - Detect supernatural presence
- Repel the Unnatural - Repel supernatural creatures
- Thwart the Unnatural - Resist supernatural abilities
- Artifact - Rare supernatural relic
- Cleanse the Unnatural - Remove supernatural influence
- Great Destiny - Empowered by higher purpose
- Unnatural Changes - Use body in supernatural ways

---

#### `/perks`
**Description:** Manage Edge Perks

**Parameters:**
- `action` (required): view, add, remove
- `edge_name` (optional): Edge to view perks for (autocomplete from your edges)
- `perk_name` (optional): Perk name (autocomplete from available perks)

**Autocomplete:**
- Shows only edges your character has
- Shows only perks available for selected edge
- Filters out perks you already have (for add action)

**Note:** See "Edge and Perks System" section for complete perk list

---

#### `/despair`
**Description:** Mark character as entering Despair state

**Parameters:** None

**Despair Effects:**
- Cannot use Desperation dice
- Drive becomes unusable
- Must complete Redemption to recover
- Visual indicator on character sheet

---

#### `/redemption`
**Description:** Mark character as redeemed from Despair

**Parameters:** None

**Recovery:**
- Drive restored
- Can use Desperation dice again
- Character ready to hunt

---

## Hunter 5E Game Mechanics

### Dice Rolling Mechanics

**Basic Roll:**
```
Roll d10s equal to pool size
Success = 6-10
Critical = Pair of 10s (adds 2 additional successes)
Total Successes = Successes + Criticals
```

**Edge System:**
Herald doesn't implement the "Edge reroll 10s" mechanic directly. Edge in H5E refers to supernatural advantages (Arsenal, Fleet, etc.) which are tracked as character abilities.

**Desperation System:**
```
Character has Desperation rating (0-10)
When rolling with Desperation:
  - Add Desperation dice to pool (orange)
  - If roll succeeds AND Desperation dice show 10s → Messy Critical
  - If Desperation dice show 1s:
    - On success → Choose Overreach or Despair
    - On failure → Automatic Despair
```

**Overreach:**
- Accept success + gain Danger equal to 1s rolled
- Or reject success + enter Despair

**Messy Critical:**
- Desperation dice contributed to critical success
- Leaves supernatural traces
- Complications ensue

### Health and Willpower

**Damage Types:**
- **Superficial** - Temporary, heals faster (⛛ chevron emoji)
- **Aggravated** - Serious, harder to heal (🔻 red triangle)

**Health:**
- Maximum = Stamina + 3
- Visual: 🔶 (undamaged) ⛛ (superficial) 🔻 (aggravated) ▪️ (empty)
- At 0 Health = Incapacitated/dying

**Willpower:**
- Maximum = Resolve + Composure
- Visual: 🔷 (undamaged) ⛛ (superficial) 🔻 (aggravated) ▪️ (empty)
- At 0 Willpower = Emotionally broken

**Recovery:**
- Ambition progress → Recovers 1 Aggravated Willpower
- Desire accomplishment → Recovers 1 Superficial Willpower

### Character Progression

**Attributes:**
- Range: 1-5 (can't be 0)
- Three categories: Physical, Social, Mental
- Cost: New rating × 4 XP

**Skills:**
- Range: 0-5
- Three categories: Physical, Social, Mental
- 27 total skills
- Cost: New rating × 2 XP

**Specialties:**
- Cost: 3 XP each
- Max per skill = skill dots (minimum 1)
- Provides bonus when applicable

### Creeds and Drives

**Creed:**
- Hunter's philosophy and approach
- Determines preferred methods
- Field of expertise

**Drive:**
- Why the Hunter hunts
- Tied to Redemption path
- Can become unusable (Despair)

**Despair State:**
- Entered when Drive fails or automatic despair triggered
- Cannot use Desperation dice
- Must complete Redemption to recover
- Visual indicator: 💀 and despair thumbnail on sheet

---

## Database Schema

### PostgreSQL Tables

#### `characters`
```sql
CREATE TABLE characters (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    -- Attributes (1-5)
    strength INTEGER DEFAULT 1 CHECK(strength >= 1 AND strength <= 5),
    dexterity INTEGER DEFAULT 1,
    stamina INTEGER DEFAULT 1,
    charisma INTEGER DEFAULT 1,
    manipulation INTEGER DEFAULT 1,
    composure INTEGER DEFAULT 1,
    intelligence INTEGER DEFAULT 1,
    wits INTEGER DEFAULT 1,
    resolve INTEGER DEFAULT 1,
    -- Derived Stats
    health INTEGER DEFAULT 0,
    willpower INTEGER DEFAULT 0,
    -- Damage Tracking
    health_sup INTEGER DEFAULT 0 CHECK(health_sup >= 0),
    health_agg INTEGER DEFAULT 0 CHECK(health_agg >= 0),
    willpower_sup INTEGER DEFAULT 0 CHECK(willpower_sup >= 0),
    willpower_agg INTEGER DEFAULT 0 CHECK(willpower_agg >= 0),
    -- H5E Mechanics
    desperation INTEGER DEFAULT 0 CHECK(desperation >= 0 AND desperation <= 10),
    in_despair BOOLEAN DEFAULT FALSE,
    creed TEXT DEFAULT NULL,
    ambition TEXT DEFAULT NULL,
    desire TEXT DEFAULT NULL,
    drive TEXT DEFAULT NULL,
    redemption TEXT DEFAULT NULL,
    danger INTEGER DEFAULT 0 CHECK(danger >= 0 AND danger <= 10),
    -- Experience
    experience_total INTEGER DEFAULT 0,
    experience_spent INTEGER DEFAULT 0,
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, name)
);
```

#### `skills`
```sql
CREATE TABLE skills (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    character_name TEXT NOT NULL,
    skill_name TEXT NOT NULL,
    dots INTEGER DEFAULT 0 CHECK(dots >= 0 AND dots <= 5),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, character_name, skill_name),
    FOREIGN KEY (user_id, character_name)
        REFERENCES characters(user_id, name) ON DELETE CASCADE
);
```

#### `edges`
```sql
CREATE TABLE edges (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    character_name TEXT NOT NULL,
    edge_name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, character_name, edge_name),
    FOREIGN KEY (user_id, character_name)
        REFERENCES characters(user_id, name) ON DELETE CASCADE
);
```

#### `perks`
```sql
CREATE TABLE perks (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    character_name TEXT NOT NULL,
    edge_name TEXT NOT NULL,
    perk_name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, character_name, perk_name),
    FOREIGN KEY (user_id, character_name)
        REFERENCES characters(user_id, name) ON DELETE CASCADE
);
```

#### `specialties`
```sql
CREATE TABLE specialties (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    character_name TEXT NOT NULL,
    skill_name TEXT NOT NULL,
    specialty_name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, character_name, skill_name, specialty_name),
    FOREIGN KEY (user_id, character_name)
        REFERENCES characters(user_id, name) ON DELETE CASCADE
);
```

#### `xp_log`
```sql
CREATE TABLE xp_log (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    character_name TEXT NOT NULL,
    action TEXT NOT NULL,
    amount INTEGER NOT NULL,
    reason TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (user_id, character_name)
        REFERENCES characters(user_id, name) ON DELETE CASCADE
);
```

#### `user_settings`
```sql
CREATE TABLE user_settings (
    user_id TEXT PRIMARY KEY,
    active_character_name TEXT DEFAULT NULL,
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Indexes
```sql
CREATE INDEX idx_characters_user_id ON characters(user_id);
CREATE INDEX idx_characters_user_name ON characters(user_id, name);
CREATE INDEX idx_skills_user_char ON skills(user_id, character_name);
```

---

## UI/UX Patterns

### Herald's Voice

**Characteristics:**
- Analytical, present-tense language
- Short declarative statements
- Uses 🔸 diamond emoji for state changes
- Minimal emotional language
- "Protocol" and "Pattern" terminology

**Example Messages:**
```
🔸 Query recognized
🔸 Protocol established
🔸 Pattern logged
🔸 Pattern warning
🔸 What are we Hunting? (catchphrase)
```

### Color Palette

```python
# Core Brand Colors
ORANGE = 0xFF8C00          # Signature orange
DARK_ORANGE = 0xCC7000     # Darker shade
BLOOD_RED = 0x8B0000       # Dark red (serious warnings)

# Semantic Colors
SUCCESS = 0xFF8C00         # Orange
WARNING = 0xFFD700         # Gold
ERROR = 0x8B0000           # Blood red
INFO = 0xFF8C00            # Orange

# Dice Colors
CRITICAL = 0x00FF00              # Green
MESSY_CRITICAL = 0xEA3323        # Red-orange
DICE_SUCCESS = 0x7777FF          # Blue
DICE_FAILURE = 0x808080          # Gray
```

### Emoji System

**Status & Results:**
- ✅ SUCCESS
- ❌ ERROR
- ⚠️ WARNING
- ℹ️ INFO
- ✨ NEW

**Health Tracking (10 dots):**
- 🔶 HEALTH_FULL (orange diamond)
- ⛛ HEALTH_SUPERFICIAL (chevron)
- 🔻 HEALTH_AGGRAVATED (red triangle)
- ▪️ HEALTH_EMPTY (black square)

**Willpower Tracking (10 dots):**
- 🔷 WILLPOWER_FULL (blue diamond)
- ⛛ WILLPOWER_SUPERFICIAL
- 🔻 WILLPOWER_AGGRAVATED
- ▪️ WILLPOWER_EMPTY

**Desperation/Danger (10 dots):**
- 🟨 DESPERATION_FULL (yellow square)
- 🟥 DANGER_FULL (red square)
- ▪️ EMPTY (black square)

**Skills (5 dots):**
- ● SKILL_FILLED
- ○ SKILL_EMPTY

**Dice Emojis:**
Herald uses custom Discord emojis with Unicode fallbacks:
```python
# Regular Dice
REGULAR_BOTCH = <:Dice_reg_over:...>      # or 💥
REGULAR_FAILURE = <:Dice_reg_fail:...>    # or ⚫
REGULAR_SUCCESS = <:Dice_reg_succ:...>    # or 🎯
REGULAR_CRITICAL = <:Dice_reg_crit:...>   # or ⭐

# Desperation Dice (orange-themed)
DESPERATION_BOTCH = <:Dice_des_over:...>      # or 🔥
DESPERATION_FAILURE = <:Dice_des_fail:...>    # or 🟠
DESPERATION_SUCCESS = <:Dice_des_succ:...>    # or 🟡
DESPERATION_CRITICAL = <:Dice_des_crit:...>   # or ✨
```

### Visual Displays

**Health Bar Example:**
```
🔶🔶🔶⛛⛛🔻▪️▪️▪️▪️ 3/6
(3 undamaged, 2 superficial, 1 aggravated, max 6, 4 empty capacity)
```

**Skill Display Example:**
```
Athletics: ●●●○○ 3
```

**Character Sheet Layout:**
1. Title: "🔸 Hunter Dossier: [Name]"
2. Creed, Drive, Desire, Ambition (vertical list)
3. Separator
4. Health, Willpower, Desperation, Danger (vertical bars with numbers)
5. Despair state indicator (if applicable)
6. Separator
7. Attributes (3-column grid: Physical, Social, Mental)
8. Separator
9. Trained Skills (vertical list)
10. Separator
11. Edges (if any)
12. Perks (if any)
13. Footer with tips

### Interactive Elements

**Button Views:**
- Character selection (green for active, gray for others)
- Creed selection (blue buttons with emojis)
- Drive selection (blue buttons with emojis)
- Edge selection (gray buttons in categorized rows)
- Confirmation dialogs (red danger, gray cancel)

**Timeouts:**
- Confirmation dialogs: 30 seconds
- Selection menus: 60 seconds
- Pagination: 180 seconds

---

## Edge and Perks System

### Complete Perks by Edge

#### Arsenal Perks
- **Team Requisition** - Provide additional copies of weapon up to margin
- **Special Features** - Weapon comes with special features up to margin
- **Exotics** - Procure rare or one-of-a-kind weapons
- **Untraceable** - Weapons never lead to Hunters
- **Backup Piece** - Once per scene, declare a hidden weapon

#### Fleet Perks
- **Armor** - Vehicles armored against small firearms
- **Performance** - Superior handling, bonus to pursuit
- **Surveillance** - Vehicle has surveillance tools
- **Untraceable** - Vehicles never lead to Hunters
- **Hidden Cache** - Hidden compartment for Arsenal/Ordnance
- **Wagon Train** - Get replacement vehicle if lost

#### Ordnance Perks
- **Multiple Payloads** - Additional copies up to margin
- **Exotics** - Custom or rare substances
- **Non-lethal Munitions** - Flash grenades, tear gas, etc.
- **Disguised Delivery** - Items disguised as mundane objects

#### Library Perks
- **Where They Hide** - Bonus to locate lair
- **Who They Are** - Bonus to identify prey
- **How to Halt Them** - Bonus to ward/protect
- **How to Harm Them** - Bonus to exploit weaknesses
- **Binge** - Research time cut in half
- **Friendly Librarian** - 1 automatic success if wait 1-2 days
- **Group Study** - +1 die per cell member participating
- **Permanent Fixture** - Library usable as safe house
- **How to Silence Them** - Bonus to social combat damage
- **Pattern Analysis** - Narrow down monster behavior
- **Where they Go** - Identify prey's targets/hunting grounds

#### Experimental Medicine Perks
- **Improved Resilience** - Armor Value 1 until end of story
- **Phoenix Protocol** - Heal twice as fast, aggravated→superficial
- **Monstrous Enhancement** - +2 dots to attribute, gain weakness
- **Unstable Steroids** - +1 dot to attribute until end of story

#### Improvised Gear Perks
- **Frugal** - Apply any Perk skill bonus with trinkets
- **Specialization** - 3-dice bonus instead of 2 for one skill
- **Mass Production** - Create additional items equal to margin
- **Speed Crafting** - Craft faster (3 turns minus margin, min 1)
- **Made to Last** - Items last additional scenes up to 6

#### Global Access Perks
- **Watching Big Brother** - Manipulate surveillance footage
- **Money Trap** - Manipulate financial data
- **All-Access Pass** - Bypass electronic locks
- **The Letter of the Law** - Manipulate criminal records
- **Digital Cannon Fodder** - Reduce digital surveillance success by 2
- **Intranet Insertion** - Access air-gapped systems remotely
- **Spoof** - Pin intrusion on false/real person

#### Drone Jockey Perks
- **Autonomous** - Drones run simple patterns on their own
- **Variants** - Summon additional drone variant
- **Specialist Skill** - Drone equipped for specific skill use
- **Armaments** - Drone equipped with taser
- **Payload** - Drone can carry large cargo
- **Electronic Shield** - Protection against hacking

#### Beast Whisperer Perks
- **Incorruptible** - Animal immune to supernatural control
- **Complex Commands** - Animal performs complex tasks
- **Menagerie** - Add another animal type to pool
- **Incognito** - Animal blends into environments
- **Supernatural Scent** - Trained to detect specific creature type

#### Turncoat Perks
- **Deathbed Confession** - Use Turncoat during combat
- **Stick to the Plan** - Cell understands intent without communication
- **Poker Face** - 2-dice bonus when questioned
- **We Come as a Team** - Bring cellmate along per margin

#### Sense the Unnatural Perks
- **Creature Specialization** - 2-dice bonus vs specific creature type
- **Precision** - Determine which creature in room
- **Range** - Extended to city block size
- **Handfree** - No object of focus needed
- **Horrid Detail** - See through supernatural disguises
- **Network** - Detect supernatural influence/contact

#### Repel the Unnatural Perks
- **Ward** - Extend protection radius ~2 meters
- **Damage** - Use focus object as melee weapon (10 aggravated)
- **Creature Specialization** - 2-dice bonus vs specific creature
- **Handfree** - No object of focus needed

#### Thwart the Unnatural Perks
- **Ward** - Extend protection radius ~2 meters
- **Creature Specialization** - 2-dice bonus vs specific creature
- **Recognition** - Learn what power would have done
- **Handfree** - No object of focus needed
- **Redirection** - Redirect resisted ability to quarry

#### Artifact Perks
- **Empower** - Once per scene, increase bonus to 3 dice
- **Attraction** - Use as bait, 2-dice ambush bonus
- **Detection** - Acts like Sense the Unnatural
- **Shield** - Halve physical damage from supernatural sources
- **Feature Unlocked** - At Danger 5, reroll dice (treat as crits)

#### Cleanse the Unnatural Perks
- **Bedside Manner** - Damage becomes superficial, rounded down
- **Trace the Threads** - Answer questions about controller's location
- **Inflict Stigmata** - +1 aggravated damage, -2 difficulty
- **Psychic Backlash** - Controller receives aggravated damage

#### Great Destiny Perks
- **Divine Protection** - Reduce Health damage by 2
- **Heavenly Resolve** - Reduce social combat damage
- **Sacred Insight** - Once per story, get supernatural clue
- **Influence Fate** - Force target to aid destiny

#### Unnatural Changes Perks
- **Breadth** - Select second attribute to enhance
- **Maximized Neuropathways** - Activation doesn't use action
- **Neuropathway Practice** - Reduce difficulty from 4 to 3
- **Handsfree** - No object of focus needed

---

## Dice Rolling System

### DiceResult Class

```python
class DiceResult:
    dice: List[int]                  # Regular dice results
    desperation_dice: List[int]      # Desperation dice results
    all_dice: List[int]              # Combined dice
    successes: int                   # Count of 6+ on all dice
    crits: int                       # Bonus from pairs of 10s
    total_successes: int             # successes + crits
    messy_critical: bool             # Desperation dice contributed to crit
    desperation_ones: int            # Count of 1s on Desperation dice
    has_overreach: bool              # desperation_ones > 0
```

### Success Calculation

```python
def _count_successes() -> int:
    # Count all dice showing 6+
    return sum(1 for die in all_dice if die >= 6)

def _count_crits() -> int:
    # Count 10s, divide by 2, multiply by 2
    # Each PAIR of 10s adds 2 additional successes
    tens = sum(1 for die in all_dice if die == 10)
    pairs = tens // 2
    return pairs * 2
```

### Messy Critical Detection

```python
def _check_messy_critical() -> bool:
    # True if:
    # - Has Desperation dice
    # - Desperation dice include 10s
    # - Total roll has criticals
    desperation_tens = sum(1 for die in desperation_dice if die == 10)
    return desperation_tens > 0 and crits > 0
```

### Dice Display Formatting

**Sorting:**
Dice are sorted for display: 10s first, then 6-9, then 1-5

**Visual Example:**
```
Regular: ⭐⭐🎯🎯⚫ | Desperation: ✨🟡🔥
(Two critical 10s, two successes, one failure | One critical, one success, one botch)
```

### Roll Result Thumbnails

Herald displays different thumbnails based on roll outcome:
- **Success** - Success thumbnail (green)
- **Critical** - Critical thumbnail (gold)
- **Failure** - Failure thumbnail (gray)
- **Overreach/Despair** - Overreach thumbnail (red/orange warning)

---

## Caching System

### Character Cache

**Implementation:** LRU-style cache with TTL

**Configuration:**
- Max size: 100 entries
- TTL: 5 minutes (300 seconds)
- Autocomplete cache: 1 minute

**Cache Keys:**
```
char:{user_id}:{character_name}
char_skills:{user_id}:{character_name}
attr:{user_id}:{character_name}:{attribute}
skill:{user_id}:{character_name}:{skill_name}
autocomplete:{user_id}
```

**Invalidation:**
- Manual invalidation after updates
- Automatic expiry after TTL
- Pattern-based invalidation (e.g., all caches for a user)

---

## Constants and Configuration

### Limits

```python
# Character
CHAR_NAME_MIN_LENGTH = 2
CHAR_NAME_MAX_LENGTH = 32
TEXT_FIELD_MAX_LENGTH = 200  # Ambition, Desire, Drive

# Attributes & Skills
ATTRIBUTE_MIN = 1
ATTRIBUTE_MAX = 5
SKILL_MIN = 0
SKILL_MAX = 5

# H5E Mechanics
DESPERATION_MIN = 0
DESPERATION_MAX = 10
DANGER_MIN = 0
DANGER_MAX = 10

# Dice
MAX_DICE_POOL = 100  # Safety limit

# Discord
MAX_AUTOCOMPLETE_RESULTS = 25
```

### Database Connection

```python
DB_POOL_MIN_SIZE = 1
DB_POOL_MAX_SIZE = 5
DB_COMMAND_TIMEOUT = 60  # seconds
```

---

## API-Style Command Summary

For quick reference when building documentation:

```yaml
Character Management:
  /create: Create new character with attributes
  /character: Switch active character (interactive buttons)
  /sheet: Display full character sheet
  /delete: Delete active character (confirmation required)
  /about: Bot information

Dice Rolling:
  /roll: H5E dice mechanics with Desperation support
  /danger: Manage Danger rating (0-10)

Progression:
  /attributes: Set attribute dots (1-5)
  /skill_set: Set skill dots (0-5)
  /specialty: Add/remove skill specialties
  /xp: Manage experience points
  /help: Command help and guides

Gameplay:
  /damage: Apply health/willpower damage
  /heal: Heal damage
  /desperation: Manage Desperation level
  /creed: Set Hunter Creed
  /drive: Set Drive and Redemption
  /ambition: Set long-term goal
  /desire: Set short-term goal
  /edge: Manage Edge abilities
  /perks: Manage Edge Perks
  /despair: Enter Despair state
  /redemption: Exit Despair state
```

---

## Development Notes

### Environment Variables

```bash
# Required
DATABASE_URL=postgresql://user:pass@host:port/dbname
DISCORD_BOT_TOKEN=your_bot_token

# Optional
USE_CUSTOM_EMOJIS=true  # Use custom Discord emojis vs Unicode
GUILD_ID=123456789      # Test guild for slash command registration
```

### Running Herald

```bash
# Install dependencies
pip install -r requirements.txt

# Configure .env
cp .env.example .env
# Edit .env with your credentials

# Run bot
python bot.py
```

### Testing

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
pytest
```

---

## Credits

**Development:**
- Built by Mashbybot
- Developed with assistance from Claude (Anthropic)

**Inspiration:**
- **[Tiltowait](https://github.com/tiltowait)** - Creator of [Inconnu](https://github.com/tiltowait/inconnu) (Vampire: The Masquerade bot), whose excellent work inspired Herald's architecture

**Community:**
- Hunter: The Reckoning 5E player community

---

*🔸 What are we Hunting?*
