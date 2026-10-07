import random

import pytest

from helpers import RandomWalker, Scripted, StandStill, ship_from_ascii
from ship import generate_ship
from sim import Outcome, place_entities, run_trial

# One open corridor along row 2: (2, 0) .. (2, 4).
CORRIDOR = ship_from_ascii("""
    #####
    #####
    .....
    #####
    #####
""")


def test_placement_gives_three_distinct_open_cells():
    ship = generate_ship(25, seed=3)
    rng = random.Random(0)
    for _ in range(500):
        cells = place_entities(ship, rng)
        assert len(set(cells)) == 3
        assert all(ship.open[c] for c in cells)


def test_reaching_button_as_fire_would_reach_it_succeeds():
    # At q = 1 the fire would reach the button (2, 2) at t = 1, the same step the bot does.
    result = run_trial(CORRIDOR, Scripted([(2, 2)]), (2, 1), (2, 2), (2, 3), 1.0, fire_seed=0)
    assert result.outcome is Outcome.SUCCESS


def test_bot_on_igniting_cell_burns():
    result = run_trial(CORRIDOR, StandStill(), (2, 0), (2, 4), (2, 1), 1.0, fire_seed=0)
    assert result.outcome is Outcome.BURNED


def test_bot_stepping_into_fire_burns():
    result = run_trial(CORRIDOR, Scripted([(2, 1)]), (2, 0), (2, 4), (2, 1), 0.0, fire_seed=0)
    assert result.outcome is Outcome.BURNED


def test_illegal_move_raises():
    # Two steps away, blocked, and diagonal.
    for move in [(2, 2), (1, 0), (3, 1)]:
        with pytest.raises(ValueError):
            run_trial(CORRIDOR, Scripted([move]), (2, 0), (2, 4), (2, 3), 0.0, fire_seed=0)


def test_different_bots_see_the_same_fire():
    ship = generate_ship(25, seed=3)
    rng = random.Random(21)
    for trial in range(20):
        bot_start, button, fire_start = place_entities(ship, rng)
        fire_seed = rng.randrange(10**6)
        a = run_trial(ship, StandStill(), bot_start, button, fire_start, 0.25, fire_seed)
        b = run_trial(ship, RandomWalker(random.Random(trial)), bot_start, button,
                      fire_start, 0.25, fire_seed)
        # A trial can end before the fire moves on its last timestep, so only
        # compare fire steps that both trials certainly ran.
        horizon = min(a.steps, b.steps) - 1
        assert ({c: t for c, t in a.ignition_time.items() if t <= horizon}
                == {c: t for c, t in b.ignition_time.items() if t <= horizon})
