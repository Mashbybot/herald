import random

def roll_pool(attribute: int, skill: int, desperation: bool = False):
    pool = attribute + skill
    dice = [random.randint(1, 10) for _ in range(pool)]
    
    successes = sum(1 for die in dice if die >= 6)
    crits = dice.count(10) // 2  # every pair of 10s = +1 success
    
    return {
        "dice": dice,
        "successes": successes + crits,
        "crits": crits,
        "desperation": desperation
    }
