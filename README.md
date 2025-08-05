
```markdown
# Herald
### *Discord Bot for Hunter: The Reckoning 5th Edition*

[![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)](https://python.org)
[![discord.py](https://img.shields.io/badge/discord.py-2.x-blue?logo=discord&logoColor=white)](https://discordpy.readthedocs.io/)
[![SQLite](https://img.shields.io/badge/SQLite-Database-green?logo=sqlite&logoColor=white)](https://sqlite.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

Herald is a comprehensive Discord bot designed specifically for **Hunter: The Reckoning 5th Edition** tabletop RPG sessions. It goes beyond basic dice rolling to provide full character management, H5E-specific mechanics, and quality-of-life tools that streamline gameplay and enhance storytelling.

---

## Getting Started

### Prerequisites
- Python 3.11 or higher
- Discord Bot Token
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/herald.git
   cd herald
   ```

2. **Set up virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure the bot**
   ```bash
   cp config/settings.py.example config/settings.py
   # Edit settings.py with your bot token and guild ID
   ```

5. **Run Herald**
   ```bash
   python bot.py
   ```

---

## Commands Reference

### Character Management
| Command | Description | Example |
|---------|-------------|---------|
| `/create` | Create a new character | `/create name:Sarah`
| `/sheet` | Display character sheet | `/sheet character:Sarah`
| `/characters` | List your characters | `/characters`

### Skills & Attributes
| Command | Description | Example |
|---------|-------------|---------|
| `/skill_set` | Set skill rating (0-5) | `/skill_set character:Sarah skill:Athletics dots:3`

### H5E Mechanics
| Command | Description | Example |
|---------|-------------|---------|
| `/desperation` | Manage desperation | `/desperation character:Sarah action:set value:5`
| `/edge` | Manage Edge rating | `/edge character:Sarah action:add value:1`
| `/creed` | Set character creed | `/creed character:Sarah creed:Innocent`

### Health & Damage
| Command | Description | Example |
|---------|-------------|---------|
| `/damage` | Apply damage | `/damage character:Sarah type:health amount:2 damage_type:superficial`
| `/heal` | Heal damage | `/heal character:Sarah type:health amount:1 damage_type:superficial`

---

## Visual Design Philosophy

Herald prioritizes visual consistency and professional presentation:

- **Health**: 💚 Healthy, 🧡 Superficial damage, 💔 Aggravated damage
- **Willpower**: 🟢 Full, 🟠 Superficial damage, ⭕ Aggravated damage  
- **Edge**: ⭐ Current rating, ▪️ Potential slots
- **Desperation**: 💢 Current level, ▫️ Empty slots
- **Layout**: Vertical organization with underlined headers and logical grouping

---

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## About Hunter: The Reckoning 5th Edition

Hunter: The Reckoning 5th Edition is a tabletop RPG published by Modiphius Entertainment, part of the World of Darkness universe. Players take on the roles of ordinary people who have witnessed the supernatural and chosen to fight back against the darkness.

*Herald is an unofficial fan project and is not affiliated with Modiphius Entertainment or the World of Darkness.*

---

## Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/herald/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/herald/discussions)
- **Discord**: [Your Discord Server](https://discord.gg/yourserver)

---

<div align="center">

**Made with ❤️ for the Hunter: The Reckoning community**

*Hunt the monsters that prey upon humanity*

</div>
```
