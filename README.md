# 🔸 Herald

Herald is a comprehensive Discord bot designed specifically for Hunter: The Reckoning 5th Edition gameplay.

*Built by Hunters, for Hunters.*

---

## 🔸 Add Herald to Your Server

<div align="center">

### **[📥 Invite Herald to Your Server](https://discord.com/oauth2/authorize?client_id=1388202365198270595)**

[![Invite Herald](https://img.shields.io/badge/Add%20to%20Discord-5865F2?style=for-the-badge&logo=discord&logoColor=white)](https://discord.com/oauth2/authorize?client_id=1388202365198270595)

*Get started in under 5 minutes. No setup required. Just add Herald and start hunting.*

---

### Need Help or Want to Report Issues?

[![Join Support Server](https://img.shields.io/badge/Support%20Server-7289DA?style=for-the-badge&logo=discord&logoColor=white)](https://discord.gg/BJde7UDUTf)

*Get help from the community, report bugs, and suggest features*

</div>

---

## About Herald

> **🔸 Herald Protocol**
>
> *"Query recognized. Assistance requested."*
>
> Herald is your assistant for Hunter: The Reckoning 5th Edition gameplay. Operations available: character management, H5E dice mechanics, progression tracking, and hunt coordination.
>
> **What are we Hunting?**

---

## Why Herald?

**Pattern observed:** When official tools are absent, Hunters build their own.

Herald exists because the Hunter community couldn't wait. We needed character tracking. We needed H5E-specific dice mechanics. We needed something that understood Edge, Desperation, and Conviction decay.

So we built it.

**Key design principles:**
- ✅ **H5E mechanical accuracy** - Edge, Desperation, and messy crits work correctly
- ✅ **Zero setup required** - Add bot, create character, start rolling
- ✅ **Privacy-focused** - PostgreSQL database, no external data collection
- ✅ **Open source** - Community-driven development
- ✅ **Free forever** - No premium tiers, no paywalls, no subscriptions

Herald is maintained by active H5E players who use it in their own campaigns. We hunt with you.

---

## Core Systems

### 🔸 Character Protocol
- Complete H5E character creation and management
- Attributes, skills, specialties, edges, perks
- Health, Willpower, Conviction, Desperation tracking
- Damage tracking with automatic status updates
- Multiple characters per user supported

### 🔸 H5E Dice Mechanics
- Edge system (reroll all 10s once)
- Desperation rolls (escalating consequences)
- Messy criticals (10s + 1s = complications)
- Rouse checks for supernatural abilities
- Automatic success calculation and formatting

### 🔸 Progression Systems
- Experience point (XP) tracking
- Attribute and skill advancement
- Edge and perk acquisition
- Session logging and chronicle history
- Creed-based character development

### 🔸 Hunt Coordination
- Cell operations (group hunts)
- Session tracking
- Organizational chart management
- Character import/export
- Privacy-focused data handling

---

## Screenshots

### Character Sheet
![Character Sheet](docs/images/sheet.webp)
*Complete character tracking with Creed, Drive, Desire, Ambition, and all H5E stats*

### Dice Rolling
![Successful Roll](docs/images/success.webp)
*Edge system in action with automatic success calculation*

![Desperation Roll](docs/images/despair.webp)
*Automatic Despair triggers with narrative consequences*

### Help System
![Help Command](docs/images/help.webp)
*Intuitive command structure with comprehensive help*

---

## Quick Start

**1. Invite Herald** (link above)

**2. Create a character:**
```
/create name:YourHunterName
```

**3. Make your first roll:**
```
/roll dexterity athletics
```

**4. Need help?**
```
/help
```

**Full documentation:** [mashbybot.github.io/herald-docs](https://mashbybot.github.io/herald-docs)

---

## Development Setup

Want to tinker with Herald's code? Here's the bare minimum to get started.

**Requirements:**
- Python 3.11+
- PostgreSQL database
- Discord bot token

**Setup:**
```bash
# Clone repository
git clone https://github.com/Mashbybot/herald.git
cd herald

# Install dependencies
pip install -r requirements.txt

# Configure environment (copy .env.example to .env and fill in values)
cp .env.example .env

# Run bot
python bot.py
```

**Note:** Self-hosting support is minimal. The hosted version is actively maintained and recommended for gameplay.

---

## Tech Stack

- **Language:** Python 3.11+
- **Framework:** discord.py 2.x (slash commands)
- **Database:** PostgreSQL
- **Architecture:** Modular cogs system
- **Deployment:** Railway (hosted version)

---

## Contributing

Herald is community-driven and welcomes contributions from H5E players and developers.

**Special Thanks:**
- **[Tiltowait](https://github.com/tiltowait)** - Creator of [Inconnu](https://github.com/tiltowait/inconnu) (Vampire: The Masquerade bot), whose excellent work inspired Herald's architecture and provided valuable code feedback

**How to Contribute:**
- Report bugs and suggest features on [GitHub Issues](https://github.com/Mashbybot/herald/issues)
- Join the [Support Discord](https://discord.gg/BJde7UDUTf) to discuss development
- Submit pull requests (please discuss major changes first)

**Development Credits:**
- Developed with assistance from Claude (Anthropic)

---

## License

Herald is open source software released under the [MIT License](LICENSE).

Free to use, modify, and distribute. Built for the Hunter community.

---

## 🤝 Community & Support

**[Support Discord Server](https://discord.gg/BJde7UDUTf)** - Get help, report bugs, suggest features

---

*🔸 Protocol active. Happy hunting.*
