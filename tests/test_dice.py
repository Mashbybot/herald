"""
Tests for dice rolling mechanics
"""

import pytest
from core.dice import DiceResult, roll_pool, _roll_edge_dice, roll_rouse_check, simple_roll


class TestDiceResult:
    """Test DiceResult class"""

    def test_basic_dice_result(self):
        """Test creating a basic dice result"""
        dice = [1, 5, 7, 10]
        result = DiceResult(dice)

        assert result.dice == dice
        assert result.edge_dice == []
        assert result.desperation_dice == []
        assert len(result.all_dice) == 4

    def test_success_counting(self):
        """Test that successes are counted correctly"""
        dice = [1, 5, 6, 7, 10]  # 3 successes (6, 7, 10)
        result = DiceResult(dice)

        assert result.successes == 3

    def test_critical_counting(self):
        """Test that criticals (pairs of 10s) are counted correctly"""
        dice = [10, 10, 5, 6]  # 1 crit (pair of 10s) + 2 successes = 3 total
        result = DiceResult(dice)

        assert result.crits == 1
        assert result.total_successes == 3  # 2 from 10s + 1 from 6 + 1 crit bonus

    def test_messy_critical(self):
        """Test messy critical detection"""
        # Desperation dice with 10s should trigger messy critical
        dice = [5, 10]
        desperation = [10]
        result = DiceResult(dice, desperation_dice=desperation)

        assert result.messy_critical is True

    def test_no_messy_critical_without_desperation(self):
        """Test that normal 10s don't trigger messy criticals"""
        dice = [10, 10]
        result = DiceResult(dice)

        assert result.messy_critical is False


class TestRollPool:
    """Test roll_pool function"""

    def test_basic_roll(self):
        """Test basic dice pool rolling"""
        result = roll_pool(attribute=3, skill=2)

        assert isinstance(result, DiceResult)
        assert len(result.dice) == 5  # 3 + 2

    def test_minimum_dice_pool(self):
        """Test that minimum pool size is 1"""
        result = roll_pool(attribute=0, skill=0)

        assert len(result.dice) >= 1

    def test_edge_dice_added(self):
        """Test that edge dice are added to the pool"""
        result = roll_pool(attribute=2, skill=2, edge=2)

        assert len(result.edge_dice) >= 2  # At least 2, could be more with explosions

    def test_desperation_dice(self):
        """Test desperation dice are added"""
        result = roll_pool(attribute=2, skill=2, desperation=True)

        assert len(result.desperation_dice) == 1


class TestEdgeDice:
    """Test edge dice explosion mechanics"""

    def test_edge_dice_returns_list(self):
        """Test that edge dice rolling returns a list"""
        result = _roll_edge_dice(2)

        assert isinstance(result, list)
        assert len(result) >= 2  # At least the initial dice

    def test_edge_dice_explosion_limit(self):
        """Test that edge dice don't explode infinitely"""
        # Even with unlucky RNG, should terminate
        result = _roll_edge_dice(5)

        # Should not have absurdly large number of dice
        assert len(result) < 100


class TestRoureCheck:
    """Test rouse check mechanics"""

    def test_rouse_check_returns_dict(self):
        """Test rouse check returns proper structure"""
        result = roll_rouse_check()

        assert isinstance(result, dict)
        assert 'die' in result
        assert 'success' in result
        assert 'desperation_gained' in result

    def test_rouse_check_die_range(self):
        """Test rouse check die is in valid range"""
        result = roll_rouse_check()

        assert 1 <= result['die'] <= 10

    def test_rouse_check_success_logic(self):
        """Test rouse check success/failure logic"""
        # Run multiple times to test logic
        for _ in range(10):
            result = roll_rouse_check()

            if result['die'] <= 5:
                assert result['success'] is True
                assert result['desperation_gained'] == 0
            else:
                assert result['success'] is False
                assert result['desperation_gained'] == 1


class TestSimpleRoll:
    """Test simple dice rolling"""

    def test_simple_roll_returns_dict(self):
        """Test simple roll returns proper structure"""
        result = simple_roll(5)

        assert isinstance(result, dict)
        assert 'dice' in result
        assert 'successes' in result

    def test_simple_roll_dice_count(self):
        """Test simple roll produces correct number of dice"""
        result = simple_roll(3)

        assert len(result['dice']) == 3

    def test_simple_roll_minimum_pool(self):
        """Test simple roll has minimum pool of 1"""
        result = simple_roll(0)

        assert len(result['dice']) >= 1
