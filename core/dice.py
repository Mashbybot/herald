import random
from typing import Dict, List, Any

class DiceResult:
    """Container for dice roll results with H5E-specific data"""
    def __init__(self, dice: List[int], edge_dice: List[int] = None, 
                 desperation_dice: List[int] = None):
        self.dice = dice
        self.edge_dice = edge_dice or []
        self.desperation_dice = desperation_dice or []
        
        # Calculate results
        self.all_dice = self.dice + self.edge_dice + self.desperation_dice
        self.successes = self._count_successes()
        self.crits = self._count_crits()
        self.total_successes = self.successes + self.crits
        self.messy_critical = self._check_messy_critical()
    
    def _count_successes(self) -> int:
        """Count successes (6+ on dice)"""
        return sum(1 for die in self.all_dice if die >= 6)
    
    def _count_crits(self) -> int:
        """Count critical successes (pairs of 10s = +1 success each pair)"""
        tens = sum(1 for die in self.all_dice if die == 10)
        return tens // 2
    
    def _check_messy_critical(self) -> bool:
        """Check if any desperation dice contributed to criticals"""
        if not self.desperation_dice:
            return False
        desperation_tens = sum(1 for die in self.desperation_dice if die == 10)
        return desperation_tens > 0 and self.crits > 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for easy serialization"""
        return {
            "dice": self.dice,
            "edge_dice": self.edge_dice,
            "desperation_dice": self.desperation_dice,
            "all_dice": self.all_dice,
            "successes": self.successes,
            "crits": self.crits,
            "total_successes": self.total_successes,
            "messy_critical": self.messy_critical
        }

def roll_pool(attribute: int, skill: int, desperation: bool = False, 
              edge: int = 0, difficulty: int = 0) -> DiceResult:
    """
    Roll a dice pool for Hunter: The Reckoning 5th Edition
    
    Args:
        attribute: Attribute rating (0-5 typically)
        skill: Skill rating (0-5 typically)  
        desperation: Whether this is a desperation roll
        edge: Number of edge dice to add
        difficulty: Difficulty modifier (negative = easier, positive = harder)
    
    Returns:
        DiceResult object with all roll information
    """
    # Calculate base pool
    base_pool = max(1, attribute + skill - difficulty)  # Minimum 1 die
    
    # Roll base dice
    base_dice = [random.randint(1, 10) for _ in range(base_pool)]
    
    # Roll edge dice (can explode on 10s)
    edge_dice = []
    if edge > 0:
        edge_dice = _roll_edge_dice(edge)
    
    # Roll desperation dice if applicable
    desperation_dice = []
    if desperation:
        desperation_dice = [random.randint(1, 10) for _ in range(1)]
    
    return DiceResult(base_dice, edge_dice, desperation_dice)

def _roll_edge_dice(count: int) -> List[int]:
    """
    Roll edge dice with exploding 10s
    Edge dice explode: when you roll a 10, roll another die
    """
    dice = []
    remaining = count
    
    while remaining > 0:
        new_dice = [random.randint(1, 10) for _ in range(remaining)]
        dice.extend(new_dice)
        
        # Count 10s for explosion
        tens = sum(1 for die in new_dice if die == 10)
        remaining = tens
        
        # Safety check to prevent infinite loops
        if len(dice) > count * 10:  # Arbitrary large limit
            break
    
    return dice

def roll_rouse_check() -> Dict[str, Any]:
    """
    Roll a rouse check for desperation escalation
    1-5: Success (no desperation gain)
    6-10: Failure (gain 1 desperation)
    """
    die = random.randint(1, 10)
    success = die <= 5
    
    return {
        "die": die,
        "success": success,
        "desperation_gained": 0 if success else 1
    }

def simple_roll(pool_size: int) -> Dict[str, Any]:
    """
    Simple dice pool roll without H5E specific mechanics
    Useful for basic rolls or non-Hunter systems
    """
    if pool_size < 1:
        pool_size = 1
    
    dice = [random.randint(1, 10) for _ in range(pool_size)]
    successes = sum(1 for die in dice if die >= 6)
    crits = dice.count(10) // 2
    
    return {
        "dice": dice,
        "successes": successes + crits,
        "crits": crits,
        "total_successes": successes + crits
    }

# Legacy function for backward compatibility
def roll_pool_legacy(attribute: int, skill: int, desperation: bool = False):
    """Backward compatible version of the original function"""
    result = roll_pool(attribute, skill, desperation)
    return {
        "dice": result.all_dice,
        "successes": result.total_successes,
        "crits": result.crits,
        "desperation": desperation
    }
