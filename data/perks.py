"""
Hunter: The Reckoning 5E - Edge Perks Data
All perks organized by their associated Edge
"""

# Perks are organized by Edge name
# Each perk has a name and description based on the Hunter 5E rulebook

EDGE_PERKS = {
    "Arsenal": {
        "Team Requisition": "Up to the margin of the win, the hunter can provide additional copies of the same weapon.",
        "Special Features": "The weapon obtained comes with a number of special features, up to the margin of the win. Each feature is like a firearm sight which makes the final decision of what qualifies as a special feature.",
        "Exotics": "The Hunter is able to procure rare or one-of-a-kind weapons or ammunition. The Difficulty of the test can increase in the case of something extremely rare or unique, as determined by the Storyteller.",
        "Untraceable": "The weapons are completely untraceable and will never lead authorities or quarry to the Hunters.",
        "Backup Piece": "As long as they can hide the piece on their person, once per scene, they can declare a weapon. This occurs even if the Hunter fails the test to activate the perk, or has no Perks and can be stolen or otherwise detected by ordinary means. If it is lost, a backup cannot be acquired until the next scene."
    },
    "Fleet": {
        "Armor": "Vehicles are armored to withstand small firearms. Flying vehicles benefit less from the armor but do so against ranged weaponry, adding to all of the Hunter's defense pools against ranged weaponry.",
        "Performance": "Vehicles have superior driving and handling. This gives a bonus equal to the margin on the die Edge test on win against pursuit-related Driving tests, however this bonus cannot be more than a dice.",
        "Surveillance": "Vehicles come with a variety of surveillance tools. This equipment gives bonus dice equal to the margin on the Edge test on stakeouts from the vehicle, such as Awareness + Technology tests. However, this bonus cannot exceed three dice.",
        "Untraceable": "The vehicles are completely untraceable and will never lead authorities or quarry to the Hunters.",
        "Hidden Cache": "The vehicle has a hidden compartment. The difficulty to locate the compartment is increased by 2 to locate the compartment if Difficulty 4, however, if the cache is not discovered, they can use all their Arsenal and Ordnance Edges even if the rest of their gear is taken. The limit of items stored is at ST discretion.",
        "Wagon Train": "If the Hunter lost a vehicle after using the Fleet Perk to gain a new one, they can make a second test of their Edge during the scene to obtain a new one. This vehicle either lacks one Perk, or increases the Difficulty while using it by 1."
    },
    "Ordnance": {
        "Multiple Payloads": "Up to the margin of the win, the hunter can provide additional copies of the same explosive.",
        "Exotics": "Custom or otherwise rare substances can be obtained. The Storyteller should alter the Difficulty of the test in cases of exceedingly rare items. These items are not inherently illegal but could be hard to get, and is determined wherewithal.",
        "Non-lethal Munitions": "The Hunter is able to obtain non-lethal munitions such as flash grenades or tear gas. The Storyteller should determine the effects of these substances on others, a good rule of thumb is to add difficulty to all actions equal to the margin of win (to the Edge) on the test at Difficulty 3 (global) and add three dice.",
        "Disguised Delivery": "Items obtained are disguised as mundane items. The Difficulty to detect them is increased by the margin on the Edge test, but this penalty cannot exceed more than three dice."
    },
    "Library": {
        "Where They Hide": "In addition to the clues obtained, any attempts to locate where the creature's lair is receive a bonus. This bonus is equal to the margin of the Edge test; it expires after use and cannot be greater than three dice.",
        "Who They Are": "In addition to the clues obtained, any attempts to identify the prey receive a bonus. This bonus is equal to the margin of the Edge test; it expires after use and cannot be greater than three dice.",
        "How to Halt Them": "In addition to the clues obtained, any attempts to ward or otherwise protect an area or person from the prey receive a bonus. This bonus is equal to the margin of the Edge test; it expires after use and cannot be greater than three dice. This does not apply to any direct attacks or augmentations.",
        "How to Harm Them": "In addition to the clues obtained, any attempts to harm the prey by exploiting their supernatural weaknesses receive a bonus. This bonus is equal to the margin of the Edge test; it expires after use and cannot exceed three dice.",
        "Binge": "Research time is cut in half.",
        "Friendly Librarian": "If the character can wait one or two days before the Edge roll, they gain one automatic success.",
        "Group Study": "The hunter may add 1 bonus die per cell member participating in the research, even if they do not have the Edge.",
        "Permanent Fixture": "The private library can be used as a safe house once per semester.",
        "How to Silence Them": "Gain bonus equal to margin to attempt to damage the target in social combat. Bonus expires after use and cannot exceed 3 dice.",
        "Pattern Analysis": "Able to narrow down specific monster behavior easily, alongside finding people alive to talk to who are familiar with the phenomenon.",
        "Where they Go": "In addition to the clues obtained, the information grants an additional bonus equal to the margin of the win to attempts to identify the prey's preferred targets, hunting grounds, or who the prey knows or associates with. This bonus expires after use and cannot exceed three dice."
    },
    "Experimental Medicine": {
        "Improved Resilience": "Until the end of the next story, the Hunter counts as having an Armor Value of 1 when unarmed, stacking with worn armor.",
        "Phoenix Protocol": "For the duration of the next story, the Hunter heals Health twice as quickly, and Aggravated damage downgraded to Superficial. However, they can't use Drive or Desperation dice. When effect ends, they gain Aggravated Willpower damage equal to the times this Perk was used.",
        "Monstrous Enhancement": "One of the Hunter's Attributes is increased by 2 dots (To max of 5), but develop a weakness to a common, mundane material (e.g. Silver, Seawater), taking Aggravated damage if they touch it. The penalty lasts for the duration of the story and is at ST discretion.",
        "Unstable Steroids": "One of the Hunter's Attributes is increased by one until the end of the next story. Should they achieve Despair on any tests before that, they also suffer 1 Aggravated damage."
    },
    "Improvised Gear": {
        "Frugal": "With their trinkets and tools on their person in a bag or other container, the Hunter can apply any Perk Skill bonus.",
        "Specialization": "Specializing in a specific Skill, the Hunter now can produce items that have a 3-dice bonus instead of 2. This perk can be taken multiple times, but only once per skill.",
        "Mass Production": "The Hunter can produce additional items equal to the margin of the test. These items are, however, all identical and grant the same bonus to the same skill, and when used under duress, such as in firefights, and the Hunter crafts the item in three turns minus the margin of the test. There is a minimum of one turn to create the item.",
        "Speed Crafting": "This Perk allows for fast for additional scenes equal to success margin. It has a maximum of six scenes before the additional scenes run out. At ST discretion, they can break after the additional scenes run out.",
        "Made to Last": "Generally, improvised weapons last for a single scene. This Perk allows for last for additional scenes equal to success margin. It has a maximum of six additional scenes before the additional scenes run out. At ST discretion, they can break before the additional scenes run out."
    },
    "Global Access": {
        "Watching Big Brother": "The Hunter can manipulate digital surveillance footage, editing people in and out of the records.",
        "Money Trap": "The Hunter can manipulate financial data and move money with little effort. This can be used to deprive prey or enemies of financial assets or guide authoritarian eyes toward something suspicious, such as a donation to a fringe group, when used offensively, by one margin of the test. This reduction lasts for one month. The Storyteller should determine the effects of fraud in the story, at least from any Perk, they must use it for personal gain, with at least an increase in Danger as they line their own pockets.",
        "All-Access Pass": "The Hunter can bypass electronic locks, tamper with, or disable security countermeasures such as alarm systems. The Difficulty depends on what the system is, with it usually being between 3-5 as determined by the Storyteller.",
        "The Letter of the Law": "The Hunter can manipulate criminal records. Making their enemies wanted criminals or erasing another's mistakes. The Difficulty ranges from 3 (local offense) to 5 (global scale) when attempting to is easily noticed. At ST discretion, they may use it.",
        "Digital Cannon Fodder": "Reduce the success of any attempt to digitally surveil, trace or locate the Hunter by 2.",
        "Intranet Insertion": "The Hunter gains access to non-networked or air gapped systems without a need to be physically present. They may use the Edge and any Perks as normal. Unless they cover their tracks, the remote intrusion is quickly noticed. At ST discretion, using this Perk may automatically increase Danger.",
        "Spoof": "Pin an intrusion on a false person or another real person. This may not fool everyone. The difficulty is determined by the ST and ranges 3-5 depending on how untraceable the spoof is."
    },
    "Drone Jockey": {
        "Autonomous": "The Hunter is able to run drones with simple patterns on their own. Complicated decision making is beyond their scope now. The drone flies with Wits + Technology at Difficulty 3 (or having it fly in this mode use a flat pool of two dice).",
        "Variants": "This Perk can be taken multiple times and allows an additional drone variant (complete with body and variant) to be summoned in previous drones. The Autonomous Perk will need to be used to run them, unless the Autonomous Perk is used to run them.",
        "Specialist Skill": "This drone is equipped with additional tools and sensors that are tailored to operate with a set of electronic picks or Science with an onboard mobile lab. This Perk only applies to one drone at a time, and can be activated on different or other Larceny with a set of electronic picks or Science with an onboard mobile lab. This Perk only applies when using their Wits + Technology when flying the drone. The controller can use their own skill with the drone, such as attempting to Larceny to open a safe at Difficulty 2.",
        "Armaments": "The drone is equipped with the equivalent of a taser, which uses a flat five-dice pool. The Specialist Skill Perk allows the controller to use their Wits + Technology when flying the drone at Difficulty 2.",
        "Payload": "The drone can carry cargo many times bigger than what it would seem to be able to carry. While it can't carry anything larger and add it to the margin of a rest made of Intelligence + Science at Difficulty 2. Drones have five health levels, with ground drones treating damage from anything other than shooting or blades as Superficial and flying drones treating any damage as Aggravated. Air drones also can be destroyed drones. But they must be fully restored before they can be used again.",
        "Electronic Shield": "Protection against signal interference or hacking. Unless a skill or ability states otherwise, the drone cannot be hacked. The Difficulty is 2 plus the margin of the operator's Intelligence + Technology test at Difficulty 2."
    },
    "Beast Whisperer": {
        "Incorruptible": "The animal is immune to supernatural powers that would seize it away from its master. Animals normally have a will not resist, and if is used to control, the Hunter will not resist. Charisma + Animal Ken is used to determine.",
        "Complex Commands": "In addition to simple commands like sit or attack the animal can perform complex tasks such as opening doors or fetching specific animal species or being subtle instead. While Intelligence + Animal Ken is used to determine the animal's actions intelligently, one cannot speak and the animal can remain with the animal.",
        "Menagerie": "Choose another animal type and add it to the available pool of animals. The animal can remain with the various animal types and only blending into environments. The Storyteller should determine the plausibility of this in certain situations, depending on the animal.",
        "Incognito": "The animal can now blend out of observed range or blending into environments. The Storyteller should determine the plausibility of this in certain situations, depending on the animal.",
        "Supernatural Scent": "Dogs trained over the course of a story, the supernatural has a distinct stimulus, and the scent cannot be 'older than 12 hours. It can be learned multiple times, but only for different creature types."
    },
    "Turncoat": {
        "Deathbed Confession": "Able to use Turncoat edge during combat, taking a full action.",
        "Stick to the Plan": "Cell is always firmly in sync with the hunter, able to understand the Turncoat Hunter's intent without communication needed.",
        "Poker Face": "2-dice bonus to Turncoat Edges when questioned.",
        "We Come as a Team": "For each point of margin, the can bring a cellmate along. The Hunter can make Turncoat Edge test to vouch for them."
    },
    "Sense the Unnatural": {
        "Creature Specialization": "Gain a two-dice bonus against a specific type of creature when attempting to detect it. This can be learned multiple times, but once for each creature type.",
        "Precision": "The Hunter is now able to determine the supernatural creature in the room is, but still not be able to tell who or what the creature is, nor are they able to determine the range for it.",
        "Range": "The range of the ability is extended to roughly the size of a city block, but it does not give precision beyond it. This does not inform them about the type of influence or the relationship type between them.",
        "Handfree": "The Hunter no longer needs an object of focus for this Edge.",
        "Horrid Detail": "Cut through any supernatural disguises to sense the Quarry's real or non-physical form.",
        "Network": "With a Wits+Insight test, they can determine if anyone is under the influence or had recent contact with the supernatural. If the influence is nearby, they can also see the connection between them. This does not inform them about the type of influence or the relationship type between them."
    },
    "Repel the Unnatural": {
        "Ward": "Radius of protection can be extended to include roughly two meters around the Hunter, with an additional meter per margin of success. Anyone in the area receives the benefit of this Edge, with the Hunter who possesses it making all the resistance tests and spending the Willpower for anyone entering the area.",
        "Damage": "The Hunter can use the object of their focus as a melee weapon with 10 damage and inflict Aggravated damage. If used in this manner, the Hunter may instead resist, or lose due to protective power fails.",
        "Creature Specialization": "Gain a two-dice bonus against a specific type of creature when attempting to repel it. This can be learned multiple times, but once for each creature type.",
        "Handfree": "The Hunter no longer needs an object of focus for this Edge."
    },
    "Thwart the Unnatural": {
        "Ward": "The area of protection can be extended to include roughly two meters around the Hunter, with an additional meter per margin of success. Anyone in the area receives the benefit of this Edge, with the Hunter who possesses it making all resistance tests and spending the Willpower for anyone entering the Willpower.",
        "Creature Specialization": "Gain a two-dice bonus against a specific type of creature when attempting to resist it. This can be learned multiple times, but once for each creature type.",
        "Recognition": "If they successfully resist an ability, the Hunter is made aware of the attempt and what the power would have done. This, however, does not give them the exact rules but instead gives hints.",
        "Handfree": "The Hunter no longer needs an object of focus for this Edge.",
        "Redirection": "When they successfully resist an ability they may take one perk of Superficial Willpower damage or redirect the effect to ST does not have to reveal the ability and may inflict a lesser version onto the quarry."
    },
    "Artifact": {
        "Empower": "Once per scene, the Hunter can make an Edge test at Difficulty 4 to increase the bonus dice to three. If this test fails, they suffer superficial Willpower damage equal to the amount they lost.",
        "Attraction": "Many people seek out this item, and so it can be used as bait and provides a two-dice bonus to any ambush attempt. Be warned: once it's revealed, those who know will continue to look for it as long as they know its location.",
        "Detection": "The Artifact acts similar to Sense the Unnatural Edge and uses the same base system rules.",
        "Shield": "Acting as a supernatural shield for the Hunter, while it's on their person, any physical damage stemming from supernatural sources is halved. (Or halved again, in cases of Superficial damage.)",
        "Feature Unlocked": "Once per story, when Danger is at 5, the Artifact allows to spend a Willpower to reroll as many non-Desperation dice as the Hunter likes. Successes are treated as critical wins."
    },
    "Cleanse the Unnatural": {
        "Bedside Manner": "Any damage dealt by this Edge becomes Superficial and after halving, is rounded down.",
        "Trace the Threads": "The Storyteller will answer 1 question about the supernatural controller's current location for each point of the margin.",
        "Inflict Stigmata": "Inflicting a Stigmata causes 1 additional point of Aggravated Health damage but reduces Difficulty of Edge test by 2. Stigmata are permanent.",
        "Psychic Backlash": "For every 2 point of the margin, the controlling entity receives 1 Aggravated damage. (Hunter chooses either Health or Willpower)"
    },
    "Great Destiny": {
        "Divine Protection": "When the Hunter takes Health damage in service of their destiny, they can reduce the damage by 2 (minimum of 0).",
        "Heavenly Resolve": "When the Hunter takes damage in Social Combat defending or proselytizing their destiny, can reduce the damage by 1 Aggravated Willpower damage.",
        "Sacred Insight": "Once per story, the Hunter can get a supernatural voice/vision providing a clue to help fulfil their destiny.",
        "Influence Fate": "Once per session, the Hunter may influence a target to take 1 action that would aid in the Hunter's destiny. Charisma + Occult vs target's Resolve + Occult."
    },
    "Unnatural Changes": {
        "Breadth": "Select a second Attribute to enhance. They gain 1 bonus die to all pools using the Attribute.",
        "Maximized Neuropathways": "Activation does not use an action.",
        "Neuropathway Practive": "The Edge's Difficulty is reduced from 4 to 3.",
        "Handsfree": "They no longer rely on the object of focus to activate."
    }
}

def get_perks_for_edge(edge_name: str) -> dict:
    """Get all perks associated with a specific edge."""
    return EDGE_PERKS.get(edge_name, {})

def get_all_edges_with_perks() -> list:
    """Get a list of all edges that have perks."""
    return list(EDGE_PERKS.keys())

def get_perk_description(edge_name: str, perk_name: str) -> str:
    """Get the description of a specific perk."""
    edge_perks = EDGE_PERKS.get(edge_name, {})
    return edge_perks.get(perk_name, "")
