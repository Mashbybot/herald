"""
Hunter: The Reckoning 5E - Advantages and Flaws Data
Official list from Hunter: The Reckoning 5E Core Rulebook

Advantages are divided into Merits and Backgrounds.
Flaws cause ongoing problems for the character.
"""

# MERITS
# Merits describe knacks, gifts, and just plain good fortune inherent to the character

MERITS = {
    # === Linguistics ===
    "Linguistics": {
        "dots": 2,
        "description": "Each dot of Linguistics allows the character to read, write and speak fluently in another language outside the default two they already know, which is their native language and the language of the common ground (eg. English) when writing.",
        "effect_type": "language",
        "effect_value": None,
        "effect_condition": "Per dot gained"
    },
    "Dead Tongues": {
        "dots": 2,
        "description": "The character adds 2 bonus dice when attempting to translate an extinct language.",
        "effect_type": "dice_bonus",
        "effect_value": 2,
        "effect_condition": "translating extinct languages"
    },

    # === The World of Academia ===
    "Forbidden Texts": {
        "dots": 2,
        "description": "The character has acquired writings from an expert. Upon choosing this merit, the character picks a monster or type of phenomenon to focus on all research relating to such a topic. The subject in question will most likely want the writings back.",
        "effect_type": "dice_bonus",
        "effect_value": 2,
        "effect_condition": "research tests about the supernatural"
    },
    "Thesis": {
        "dots": 2,
        "description": "Dive deeper into additional Specialty, though not tied to any Skill but applying to any of them when used in a research test. The Storyteller needs to approve this specialty, though player chooses whether it is occult and not the supernatural.",
        "effect_type": "specialty",
        "effect_value": 1,
        "effect_condition": "research tests only"
    },
    "Part of the Furniture": {
        "dots": 3,
        "description": "Once given tenure when interacting with campus staff, or while on campus, the character may add 2 dice to any single pool.",
        "effect_type": "dice_bonus",
        "effect_value": 2,
        "effect_condition": "when on campus or with campus staff"
    },

    # === Looks ===
    "Beautiful": {
        "dots": 2,
        "description": "Add one die to related Social pools.",
        "effect_type": "dice_bonus",
        "effect_value": 1,
        "effect_condition": "related social rolls"
    },
    "Stunning": {
        "dots": 4,
        "description": "Add two dice to related Social pools.",
        "effect_type": "dice_bonus",
        "effect_value": 2,
        "effect_condition": "related social rolls"
    },

    # === Nutritionist ===
    "Solo Cooking": {
        "dots": 1,
        "description": "Heal one extra Superficial Health at the beginning of a session if the Hunter has time to prepare a meal before the session begins.",
        "effect_type": "healing_bonus",
        "effect_value": 1,
        "effect_condition": "at session start with meal prep"
    },
    "Cell Chef": {
        "dots": 2,
        "description": "The entire cell heals one extra Superficial Health at the beginning of a session if the Hunter has time to prepare a meal before the session begins. Any Hunters separated from the cell at the start of session would not receive this benefit.",
        "effect_type": "healing_bonus",
        "effect_value": 1,
        "effect_condition": "entire cell at session start with meal prep"
    },

    # === Mental Feats ===
    "Always Prepared": {
        "dots": 2,
        "description": "The character is efficient and practical, and adds 2 bonus dice to Preparedness for pools related to Ambush or where they are studying, watching, or keeping watch, they must roll a die, and will asleep if the result is a failure.",
        "effect_type": "dice_bonus",
        "effect_value": 2,
        "effect_condition": "preparedness and ambush"
    },
    "Eidetic Memory": {
        "dots": 2,
        "description": "The character benefits from photographic memory, only requiring a bit of study before they can recall a text or details verbatim. They gain 2 bonus dice on any test related to recall for things such as codes, directions, maps, facial recognition, formulae, and rote behaviors.",
        "effect_type": "dice_bonus",
        "effect_value": 2,
        "effect_condition": "recall tests (codes, directions, maps, facial recognition, formulae, rote behaviors)"
    },

    # === Supernatural Situations ===
    "Unseemly Aura": {
        "dots": 2,
        "description": "Monsters will occasionally believe the Hunter to be one of their own or another supernatural creature entirely.",
        "effect_type": None,
        "effect_value": None,
        "effect_condition": None
    },
}

# BACKGROUNDS
# Backgrounds describe advantages of relationship, circumstance, and opportunity

BACKGROUNDS = {
    # === Allies ===
    "Allies": {
        "dots": "1-5",
        "description": "A group who will support or aid the Hunter. Family, friends, or an organization that has loyalty. Build them between (1-3) Effectiveness and (1-3) Reliability. The maximum amount of total points is 5. Effectiveness defines how proficient they are at a task. Reliability determines how dependable they are.",
        "effect_type": None,
        "effect_value": None,
        "effect_condition": None
    },

    # === Contacts ===
    "Contacts": {
        "dots": "1-3",
        "description": "These are people who can get the character information, items or other things of value.",
        "effect_type": None,
        "effect_value": None,
        "effect_condition": None
    },

    # === Fame ===
    "Fame": {
        "dots": "1-5",
        "description": "The character might be a pop singer, actress, or other celebrity. The level of fame can subtract from tests against fans and can be used instead of a another trait in Social tests as allowed by the Storyteller. However, this can also be a negative trait as failing a target unnoticed may become difficult with fans spotting the character.",
        "effect_type": None,
        "effect_value": None,
        "effect_condition": None
    },

    # === Influence ===
    "Influence": {
        "dots": "1-5",
        "description": "They have sway in communities, be they political, through financial status and prestige, or manipulation. By default, this merit usually applies to a specific group or region of the city.",
        "effect_type": None,
        "effect_value": None,
        "effect_condition": None
    },

    # === Mask ===
    "Mask": {
        "dots": "1-3",
        "description": "A false identity that allows the Hunter to keep their true selves away from the law or rival orgs; this might include bank accounts, a birth certificate and everything else. It requires maintenance.",
        "effect_type": None,
        "effect_value": None,
        "effect_condition": None
    },
    "Zeroed": {
        "dots": 1,
        "description": "All of the character's past self has been purged from all systems if they never existed. The character must have a +1 dot mask in order to take this.",
        "effect_type": None,
        "effect_value": None,
        "effect_condition": "Requires Mask 1+"
    },
    "Cobbler": {
        "dots": 1,
        "description": "The ability to create new or source old masks. Making a mask takes 3 days per dot.",
        "effect_type": None,
        "effect_value": None,
        "effect_condition": None
    },
    "Faked Death": {
        "dots": 2,
        "description": "As long as you keep a low profile and a new identity nobody from your old life is going to be looking for you including Enemies, Stalkers, and orgs. You do maintain a limited relationship with any Contacts. The character must have a 2-dot Mask in order to take this, unless you buy a separate Mask Merit you have the same identity.",
        "effect_type": None,
        "effect_value": None,
        "effect_condition": "Requires Mask 2"
    },

    # === Mentor ===
    "Mentor": {
        "dots": "1-5",
        "description": "Another Hunter or group of Hunters who has taken the character under their wing. Their relationship with either one or a group of Hunters who look out for them, offer them guidance, information, or aid in other ways once in awhile. Generally a group costs one more dot than a single mentor of the equivalent level; for example, a cell of three experienced hunters might be a four dot group.",
        "effect_type": None,
        "effect_value": None,
        "effect_condition": None
    },
    "Generous": {
        "dots": "1-3",
        "description": "You can call upon your mentor for a valuable favor once per story. This does not run the usual risk of offending your mentor but you lose a dot from this background each time you do.",
        "effect_type": "favor",
        "effect_value": 1,
        "effect_condition": "once per story"
    },
    "Spirit Guide (Arcanum)": {
        "dots": 2,
        "description": "Your mentor is some kind of ghost or unearthly being that you studied and formed a rapport with. You have the ability to summon them. They are unable to aid with corporeal matters like law enforcement or politics but they do have valuable knowledge on ghosts.",
        "effect_type": None,
        "effect_value": None,
        "effect_condition": "Arcanum merit"
    },

    # === Resources ===
    "Resources": {
        "dots": "1-5",
        "description": "Resources represents the income of a Hunter; be it physical cash, items or places. The source of the income must be defined when obtained. Cash flow, be it from stock trading or equipment to working as a barista at night.",
        "effect_type": None,
        "effect_value": None,
        "effect_condition": None
    },

    # === Retainers ===
    "Retainers": {
        "dots": "1-3",
        "description": "A loyal servant or assistant; they can be paid employees, longtime stewards of the Hunter or the Hunter's family, or a victim of some type of scheme that keeps them reliant on the Hunter. Loyal followers who will accomplish a request for the Hunter.",
        "effect_type": None,
        "effect_value": None,
        "effect_condition": None
    },

    # === Safe House ===
    "Safe House": {
        "dots": "1-3",
        "description": "A Safe House represents the degree of security and distinction beyond a place to sleep and eat. Hunters without dots in this background can still have a place to resides and remain safe, and other Backgrounds can be used as justification for safe houses such as Resources, Status and Influence. However, if these Backgrounds disappear, so does the safe house.",
        "effect_type": None,
        "effect_value": None,
        "effect_condition": None
    },
    "Hidden Armory": {
        "dots": 2,
        "description": "Each dot adds one pistol and one long firearm inside the safe house, safely concealed. These aren't as strong as those earned from the Arsenal Edge, nor do they automatically replenish if misplaced.",
        "effect_type": "equipment",
        "effect_value": None,
        "effect_condition": "Each dot adds +1 pistol and +1 long firearm"
    },
    "Panic Room": {
        "dots": 2,
        "description": "The ability to house to individuals and breaching this requires a base Difficulty of 5, this can only be breached/escape through brute force and houses either twice as many individuals with a cap of 32 in large safe houses or adds +1 to the breach/escape Difficulty. This is not available in one dot safe houses.",
        "effect_type": "protection",
        "effect_value": None,
        "effect_condition": "Difficulty 5 to breach"
    },
    "Watchmen": {
        "dots": 2,
        "description": "Each dot supplies 4 Average Mortals and one Gifted Mortal to watch over the safe house.",
        "effect_type": "guards",
        "effect_value": None,
        "effect_condition": "4 Average Mortals + 1 Gifted Mortal per dot"
    },
    "Laboratory": {
        "dots": 2,
        "description": "Each dot of this merit contributes to dice rolls related to one Science or Technology specialty. Not available in one dot safe houses.",
        "effect_type": "dice_bonus",
        "effect_value": None,
        "effect_condition": "per dot to one Science/Technology specialty in safe house"
    },
    "Luxury": {
        "dots": 2,
        "description": "Rich and full of value, the safe house is well decorated with high-end décor and items. +2 dice bonus to Social tests when mortals are inside the safe house. Without at least 3 dots in Resources, these items are stolen or illegally obtained.",
        "effect_type": "dice_bonus",
        "effect_value": 2,
        "effect_condition": "social tests when mortals are inside safe house"
    },
    "Postern": {
        "dots": 2,
        "description": "The safe house has some kind of secret exit that allows them a safe passage out. For each dot of this merit add one die to pools of evasion or escaping surveillance near the safe house.",
        "effect_type": "dice_bonus",
        "effect_value": 1,
        "effect_condition": "per dot to evasion/escaping surveillance near safe house"
    },
    "Security System": {
        "dots": 2,
        "description": "For each dot of this merit, add one die to pools to resist (or to alert the Hunter to) unwelcome guests into the safe house.",
        "effect_type": "dice_bonus",
        "effect_value": 1,
        "effect_condition": "per dot to resist or alert to unwelcome guests"
    },
    "Surgery": {
        "dots": 1,
        "description": "Add two die to relevant pools for relevant tests performed in safe houses.",
        "effect_type": "dice_bonus",
        "effect_value": 2,
        "effect_condition": "relevant tests in safe house"
    },
    "Bolt Hole": {
        "dots": 1,
        "description": "Whenever hiding or attempting to move from one safe place to another undetected, receive a 2 dice bonus.",
        "effect_type": "dice_bonus",
        "effect_value": 2,
        "effect_condition": "hiding or moving between safe places"
    },

    # === Status ===
    "Status": {
        "dots": "1-5",
        "description": "Reputation and standing within a specific local community of Hunters. The character has built a name for themselves with a group of Hunters.",
        "effect_type": None,
        "effect_value": None,
        "effect_condition": None
    },
}

# FLAWS
# The flip side of Advantages, Flaws cause ongoing problems for the character

FLAWS = {
    # === Linguistics Flaws ===
    "Illiterate": {
        "dots": 1,
        "description": "The character cannot read nor write and their Science and Academics Skills may not go beyond 1 dot. The character also cannot have Specialty that incorporates modern knowledge.",
        "effect_type": "skill_cap",
        "effect_value": None,
        "effect_condition": "Science and Academics capped at 1"
    },
    "El Mala Educación": {
        "dots": 2,
        "description": "The character makes +1 total failures or of critical results when they try to translate any extinct language.",
        "effect_type": "critical_failure",
        "effect_value": None,
        "effect_condition": "translating extinct languages"
    },

    # === The World of Academia Flaws ===
    "Failing Grades": {
        "dots": 1,
        "description": "Reduce social pools by two when dealing with campus staff.",
        "effect_type": "dice_penalty",
        "effect_value": -2,
        "effect_condition": "social pools with campus staff"
    },
    "Dangerous Knowledge": {
        "dots": 2,
        "description": "Upon purchasing this merit, the Storyteller chooses a monster type. When making research or perception-related tests on that monster type, if the result is a total failure or a critical, the Danger rating increases by 1.",
        "effect_type": "danger_increase",
        "effect_value": None,
        "effect_condition": "on critical failure or total failure researching specific monster type"
    },

    # === Looks Flaws ===
    "Ugly": {
        "dots": 1,
        "description": "Lose one die from related Social pools.",
        "effect_type": "dice_penalty",
        "effect_value": -1,
        "effect_condition": "related social rolls"
    },
    "Repulsive": {
        "dots": 2,
        "description": "Lose two dice from related Social pools.",
        "effect_type": "dice_penalty",
        "effect_value": -2,
        "effect_condition": "related social rolls"
    },

    # === Nutritionist Flaws ===
    "Malnourished": {
        "dots": 2,
        "description": "The character is too busy, poor or inept to eat properly, and their Health is calculated as Stamina + 2 instead of Stamina + 3.",
        "effect_type": "health_penalty",
        "effect_value": -1,
        "effect_condition": "maximum health reduced by 1"
    },

    # === Mental Feats Flaws ===
    "Disordered Sleep": {
        "dots": 2,
        "description": "Sleep catches the character at the least convenient time possible, due to their faulty sleep schedule. When they are studying, watching, or keeping watch, they must roll a die, and fall asleep if the result is a failure. It is generally too late if an impact occurs but it generally means the character can't complete a task, misses a detail, or it is easy to ambush.",
        "effect_type": "sleep_risk",
        "effect_value": None,
        "effect_condition": "must roll die when studying/watching, sleep on failure"
    },

    # === Psychologist Traits Flaws ===
    "Living on the Edge": {
        "dots": 2,
        "description": "When confronted with a risky temperament that the character hasn't done before, they suffer a two-dice penalty for all actions till they participate in or the scene ends.",
        "effect_type": "dice_penalty",
        "effect_value": -2,
        "effect_condition": "all actions until participate in risky action"
    },
    "Weak-Willed": {
        "dots": 3,
        "description": "Even when they are aware that someone is attempting to sway they may not use the active resistance systems to avoid the attempts.",
        "effect_type": "no_resistance",
        "effect_value": None,
        "effect_condition": "cannot use active resistance against mental influence"
    },

    # === Substance Abuse Flaws ===
    "Addiction": {
        "dots": 1,
        "description": "Unless the action is to immediately gain their drug, lose one die to all pools if the character did not indulge in their substance of choice during the last scene.",
        "effect_type": "dice_penalty",
        "effect_value": -1,
        "effect_condition": "all pools if didn't indulge last scene"
    },
    "Severe Addiction": {
        "dots": 2,
        "description": "Unless the action is to immediately gain their drug, lose two dice to all pools if the character did not indulge in their substance of choice during the last scene.",
        "effect_type": "dice_penalty",
        "effect_value": -2,
        "effect_condition": "all pools if didn't indulge last scene"
    },

    # === Supernatural Situations Flaws ===
    "Crone's Curse": {
        "dots": 3,
        "description": "The character appears at least a decade older than they actually are which reduces their Health tracker by one.",
        "effect_type": "health_penalty",
        "effect_value": -1,
        "effect_condition": "maximum health reduced by 1"
    },
    "Stigmata": {
        "dots": 2,
        "description": "Select either Health or Willpower damage at character creation. This Flaw may also be taken a second time for the other type of damage. The Hunter bleeds from open wounds on their hands, feet and forehead whenever they suffer physical or Willpower damage. However this does not trigger when they spend Willpower.",
        "effect_type": "stigmata",
        "effect_value": None,
        "effect_condition": "bleeds from wounds when taking selected damage type"
    },

    # === Backgrounds Flaws ===
    "Enemy": {
        "dots": "1-3",
        "description": "The opposite to Allies, and are rated two dots less than their Effectiveness. A Gifted Ally costs three dots as an Ally, but only provides one dot as a Flaw.",
        "effect_type": None,
        "effect_value": None,
        "effect_condition": None
    },
    "Infamy": {
        "dots": 2,
        "description": "They've done something atrocious and others know.",
        "effect_type": None,
        "effect_value": None,
        "effect_condition": None
    },
    "Dark Secret": {
        "dots": 1,
        "description": "What they've done is still a secret, except to one or two very motivated enemies.",
        "effect_type": None,
        "effect_value": None,
        "effect_condition": None
    },
    "Infamous Partner": {
        "dots": 1,
        "description": "A spouse, lover or someone else significant to the character has Infamy that will sometimes tarnish the reputation of the Hunter by association.",
        "effect_type": None,
        "effect_value": None,
        "effect_condition": None
    },
    "Disliked": {
        "dots": 1,
        "description": "Subtract one die from Social tests involving groups outside of the character's loyal followers.",
        "effect_type": "dice_penalty",
        "effect_value": -1,
        "effect_condition": "social tests with groups outside loyal followers"
    },
    "Despised": {
        "dots": 2,
        "description": "One group/region of the city goes out of its way to thwart the character's plans.",
        "effect_type": None,
        "effect_value": None,
        "effect_condition": None
    },
    "Serial Error": {
        "dots": 1,
        "description": "A mistake has been made in the character's background checks showing that they'd recently died, are on a dangerous watchlist, or otherwise likely to be called on by the law. This won't last long but until they are cleared by the law then take a 2 dice penalty to Social tests with the offended Hunters.",
        "effect_type": "dice_penalty",
        "effect_value": -2,
        "effect_condition": "social tests until cleared by law"
    },
    "Person of Interest": {
        "dots": 2,
        "description": "The Hunter has become a person of interest and with their biometrics and information been logged as a potential terrorist in agency databases.",
        "effect_type": None,
        "effect_value": None,
        "effect_condition": None
    },
    "Adversary": {
        "dots": "1-2",
        "description": "A rival Hunter or group who wants to do the Hunter or their cell harm.",
        "effect_type": None,
        "effect_value": None,
        "effect_condition": None
    },
    "Credit Hungry (Arcanum)": {
        "dots": 1,
        "description": "On any hunt where you call upon your mentor for aid, they will take credit for all achievements but not negative consequences.",
        "effect_type": None,
        "effect_value": None,
        "effect_condition": "Arcanum flaw"
    },
    "Destitute": {
        "dots": 1,
        "description": "No money and no home.",
        "effect_type": None,
        "effect_value": None,
        "effect_condition": None
    },
    "Stalkers": {
        "dots": 1,
        "description": "Something about the character tends to attract others who get a little too attached and just won't let go. Be it a former retainer or past lover, should they get rid of them, another soon appears.",
        "effect_type": None,
        "effect_value": None,
        "effect_condition": None
    },
    "No Safe House": {
        "dots": 1,
        "description": "The character has no expectation of security while at home.",
        "effect_type": None,
        "effect_value": None,
        "effect_condition": None
    },
    "Creepy": {
        "dots": 1,
        "description": "Take a two-dice penalty on Social pools in the safe house with human guests.",
        "effect_type": "dice_penalty",
        "effect_value": -2,
        "effect_condition": "social pools in safe house with human guests"
    },
    "Haunted": {
        "dots": "1-3",
        "description": "There is a supernatural manifestation taking hold over the safe house with the penalties defined by the Storyteller. It should at least give a one-die penalty or bonus to affected pools used in the safe house per dot of Haunted.",
        "effect_type": "dice_penalty",
        "effect_value": -1,
        "effect_condition": "per dot to affected pools in safe house (ST discretion)"
    },
    "Compromised": {
        "dots": 2,
        "description": "This safe house is on a watchlist and may have been raided at some point, adding two dice to pools to penetrate or watch the safe house.",
        "effect_type": "surveillance_risk",
        "effect_value": None,
        "effect_condition": "+2 dice for enemies to penetrate/watch"
    },
    "Interfering Roommate": {
        "dots": 1,
        "description": "The safe house isn't private, with someone else also using it for legitimate purpose, keeping an eye on the character. Suspicious or outright criminal activity will be reported to relevant authorities.",
        "effect_type": None,
        "effect_value": None,
        "effect_condition": None
    },
    "Suspect": {
        "dots": 1,
        "description": "Breaking the rules or weaseling out of something owed has netted this character the ire of this Hunter group. Stay out of sight and mind and nothing will happen but until they prove their worth again but until then take a 2 dice penalty to Social tests with the offended Hunters.",
        "effect_type": "dice_penalty",
        "effect_value": -2,
        "effect_condition": "social tests with offended Hunter group"
    },
    "Shunned": {
        "dots": 2,
        "description": "Despised by a Hunter group, a line was crossed that never should have been, and now members of this group actively work against them at any opportunity.",
        "effect_type": None,
        "effect_value": None,
        "effect_condition": None
    },
}

# Combine all for easy access
ALL_ADVANTAGES = {**MERITS, **BACKGROUNDS}
ALL_FLAWS = FLAWS
