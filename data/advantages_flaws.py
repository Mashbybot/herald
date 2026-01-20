"""
Character Advantages and Flaws Data
A mix of mechanical and narrative traits for character customization
"""

# Advantages provide benefits to characters
# Each advantage has a name, description, and optional mechanical effects
# effect_type: dice_bonus, attribute_bonus, damage_reduction, reroll, or None (narrative)
# effect_value: numerical value for mechanical effects
# effect_condition: when the effect applies

ADVANTAGES = {
    # Mechanical Advantages
    "Quick Reflexes": {
        "description": "You have lightning-fast reactions and can act before others in tense situations.",
        "effect_type": "dice_bonus",
        "effect_value": 2,
        "effect_condition": "initiative rolls"
    },
    "Silver Tongue": {
        "description": "You have a natural gift for persuasion and can talk your way out of most situations.",
        "effect_type": "dice_bonus",
        "effect_value": 2,
        "effect_condition": "persuasion and deception rolls"
    },
    "Tough as Nails": {
        "description": "Your body can withstand tremendous punishment. You have natural resilience to physical harm.",
        "effect_type": "damage_reduction",
        "effect_value": 1,
        "effect_condition": "all physical damage"
    },
    "Natural Leader": {
        "description": "People naturally look to you for guidance and follow your lead.",
        "effect_type": "dice_bonus",
        "effect_value": 2,
        "effect_condition": "leadership and inspiration rolls"
    },
    "Keen Senses": {
        "description": "Your senses are exceptionally sharp, allowing you to notice details others miss.",
        "effect_type": "dice_bonus",
        "effect_value": 2,
        "effect_condition": "perception and awareness rolls"
    },
    "Fast Healer": {
        "description": "Your body recovers from injuries at an accelerated rate.",
        "effect_type": "healing_bonus",
        "effect_value": 2,
        "effect_condition": "natural healing"
    },
    "Lucky": {
        "description": "Fortune seems to smile upon you more often than not.",
        "effect_type": "reroll",
        "effect_value": 1,
        "effect_condition": "once per session, reroll any failed roll"
    },
    "Physically Imposing": {
        "description": "Your size and presence make you naturally intimidating.",
        "effect_type": "dice_bonus",
        "effect_value": 2,
        "effect_condition": "intimidation rolls"
    },
    "Crack Shot": {
        "description": "You have exceptional aim with ranged weapons.",
        "effect_type": "dice_bonus",
        "effect_value": 2,
        "effect_condition": "ranged attack rolls"
    },
    "Iron Will": {
        "description": "Your mental fortitude is exceptional, allowing you to resist mental influence.",
        "effect_type": "dice_bonus",
        "effect_value": 2,
        "effect_condition": "resisting mental influence or fear"
    },

    # Narrative/Social Advantages
    "Ambidextrous": {
        "description": "You can use both hands with equal skill, giving you flexibility in combat and tasks.",
        "effect_type": None,
        "effect_value": None,
        "effect_condition": None
    },
    "Eidetic Memory": {
        "description": "You can recall information with perfect clarity, remembering details others would forget.",
        "effect_type": None,
        "effect_value": None,
        "effect_condition": None
    },
    "Street Contacts": {
        "description": "You have connections in the criminal underworld who owe you favors.",
        "effect_type": None,
        "effect_value": None,
        "effect_condition": None
    },
    "Law Enforcement Contacts": {
        "description": "You have friends in law enforcement who can provide information or assistance.",
        "effect_type": None,
        "effect_value": None,
        "effect_condition": None
    },
    "Academic Connections": {
        "description": "You have ties to universities and research institutions.",
        "effect_type": None,
        "effect_value": None,
        "effect_condition": None
    },
    "Wealthy": {
        "description": "You have significant financial resources at your disposal.",
        "effect_type": None,
        "effect_value": None,
        "effect_condition": None
    },
    "Famous": {
        "description": "You're well-known in certain circles, which can open doors or create complications.",
        "effect_type": None,
        "effect_value": None,
        "effect_condition": None
    },
    "Safe House": {
        "description": "You have access to a secure location unknown to your enemies.",
        "effect_type": None,
        "effect_value": None,
        "effect_condition": None
    },
    "Multilingual": {
        "description": "You speak multiple languages fluently, allowing you to communicate across cultures.",
        "effect_type": None,
        "effect_value": None,
        "effect_condition": None
    },
    "Natural Athlete": {
        "description": "You have exceptional physical coordination and natural athletic ability.",
        "effect_type": None,
        "effect_value": None,
        "effect_condition": None
    }
}

# Flaws provide complications and challenges for characters
# Structure is the same as advantages but represents negative effects

FLAWS = {
    # Mechanical Flaws
    "Short Temper": {
        "description": "You have difficulty controlling your anger and may lash out inappropriately.",
        "effect_type": "dice_penalty",
        "effect_value": -2,
        "effect_condition": "composure and self-control rolls"
    },
    "Phobia (Specify)": {
        "description": "You have an irrational and debilitating fear of something specific.",
        "effect_type": "dice_penalty",
        "effect_value": -2,
        "effect_condition": "when confronting phobia"
    },
    "Bad Reputation": {
        "description": "You're known for something negative, making social interactions difficult.",
        "effect_type": "dice_penalty",
        "effect_value": -2,
        "effect_condition": "social rolls with those who know your reputation"
    },
    "Nightmares": {
        "description": "You suffer from terrible recurring nightmares that leave you exhausted.",
        "effect_type": "willpower_penalty",
        "effect_value": -1,
        "effect_condition": "maximum willpower reduced by 1"
    },
    "Clumsy": {
        "description": "You're naturally uncoordinated and prone to accidents.",
        "effect_type": "dice_penalty",
        "effect_value": -2,
        "effect_condition": "dexterity-based physical tasks"
    },
    "Weak Constitution": {
        "description": "You get sick easily and tire quickly.",
        "effect_type": "health_penalty",
        "effect_value": -1,
        "effect_condition": "maximum health reduced by 1"
    },
    "Gullible": {
        "description": "You tend to believe what others tell you and struggle to detect deception.",
        "effect_type": "dice_penalty",
        "effect_value": -2,
        "effect_condition": "detecting lies or deception"
    },
    "Poor Eyesight": {
        "description": "Your vision is impaired, requiring corrective lenses to see clearly.",
        "effect_type": "dice_penalty",
        "effect_value": -2,
        "effect_condition": "visual perception rolls when not wearing glasses"
    },
    "Combat Paralysis": {
        "description": "You freeze up in dangerous situations, unable to act decisively.",
        "effect_type": "dice_penalty",
        "effect_value": -2,
        "effect_condition": "first round of combat"
    },
    "Addicted (Specify)": {
        "description": "You struggle with an addiction that can interfere with your life.",
        "effect_type": "dice_penalty",
        "effect_value": -2,
        "effect_condition": "when craving or withdrawal"
    },

    # Narrative/Social Flaws
    "Haunted": {
        "description": "You're plagued by supernatural entities or the ghosts of your past.",
        "effect_type": None,
        "effect_value": None,
        "effect_condition": None
    },
    "Oath/Code of Honor": {
        "description": "You've sworn an oath or live by a code that restricts your actions.",
        "effect_type": None,
        "effect_value": None,
        "effect_condition": None
    },
    "Wanted": {
        "description": "Law enforcement or criminal organizations are actively looking for you.",
        "effect_type": None,
        "effect_value": None,
        "effect_condition": None
    },
    "Dark Secret": {
        "description": "You harbor a secret that could destroy your life if revealed.",
        "effect_type": None,
        "effect_value": None,
        "effect_condition": None
    },
    "Enemy": {
        "description": "You have a powerful enemy who wishes you harm.",
        "effect_type": None,
        "effect_value": None,
        "effect_condition": None
    },
    "Debt": {
        "description": "You owe someone a significant debt that they may call in at any time.",
        "effect_type": None,
        "effect_value": None,
        "effect_condition": None
    },
    "Overconfident": {
        "description": "You believe in your abilities beyond what's reasonable, leading to reckless decisions.",
        "effect_type": None,
        "effect_value": None,
        "effect_condition": None
    },
    "Prejudiced": {
        "description": "You hold strong biases against certain groups of people.",
        "effect_type": None,
        "effect_value": None,
        "effect_condition": None
    },
    "Compulsion": {
        "description": "You have a strong compulsion to perform certain behaviors or rituals.",
        "effect_type": None,
        "effect_value": None,
        "effect_condition": None
    },
    "Chronic Pain": {
        "description": "You suffer from ongoing pain from old injuries or illness.",
        "effect_type": None,
        "effect_value": None,
        "effect_condition": None
    }
}
