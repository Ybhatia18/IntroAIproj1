import random

from fire import Fire, fire_timeline
from helpers import StandStill, distances_from, ship_from_ascii
from ship import generate_ship
from sim import place_entities, run_trial

SHIP = generate_ship(30, seed=11)


def test_q0_never_spreads():
    start = SHIP.open_cells[0]
    fire = Fire(SHIP, start, 0.0, random.Random(0))
    for _ in range(100):
        fire.step()
    assert fire.burning == {start}


def test_q1_burns_exactly_distance_t():
    # at q = 1 everything next to fire catches, so after t steps it should be exactly
    # everything within distance t. if the update wasnt synchronous it would go further
    start = SHIP.open_cells[100]
    dist = distances_from(SHIP, start)
    fire = Fire(SHIP, start, 1.0, random.Random(0))
    for t in range(1, max(dist.values()) + 1):
        fire.step()
        assert fire.burning == {c for c, d in dist.items() if d <= t}


def test_never_burns_blocked_and_only_grows():
    fire = Fire(SHIP, SHIP.open_cells[0], 0.4, random.Random(5))
    previous = set(fire.burning)
    for _ in range(100):
        fire.step()
        assert previous <= fire.burning
        assert all(SHIP.open[c] for c in fire.burning)
        previous = set(fire.burning)


def test_ignition_rate_matches_formula():
    # S starts burning. A and B touch S, T touches A and B but not S. after step 1
    # T has 0, 1 or 2 burning neighbors, so we can check how often it catches in step 2
    ship = ship_from_ascii("""
        ####
        #..#
        #..#
        ####
    """)
    S, A, B, T = (1, 1), (1, 2), (2, 1), (2, 2)
    q = 0.3
    counts = {1: [0, 0], 2: [0, 0]}  # K -> [ignitions, samples]
    rng = random.Random(1234)
    for _ in range(20000):
        fire = Fire(ship, S, q, random.Random(rng.randrange(2**32)))
        fire.step()
        k = (A in fire.burning) + (B in fire.burning)
        fire.step()
        if k:
            counts[k][0] += T in fire.burning
            counts[k][1] += 1
    # 0.04 is loose enough that random noise wont fail the test
    for k, (hits, n) in counts.items():
        assert abs(hits / n - (1 - (1 - q) ** k)) < 0.04


def test_same_seed_same_fire_and_matches_run_trial():
    rng = random.Random(4)
    for _ in range(10):
        bot, button, fire_start = place_entities(SHIP, rng)
        seed = rng.randrange(10**6)
        timeline = fire_timeline(SHIP, fire_start, 0.3, seed, max_steps=10**6)
        assert timeline == fire_timeline(SHIP, fire_start, 0.3, seed, max_steps=10**6)
        # a bot that stands still can only lose after the fire moves, so steps = fire steps here
        result = run_trial(SHIP, StandStill(), bot, button, fire_start, 0.3, seed)
        assert result.ignition_time == {c: t for c, t in timeline.items() if t <= result.steps}


def test_clone_leaves_original_unchanged():
    start = SHIP.open_cells[200]
    original = Fire(SHIP, start, 0.4, random.Random(8))
    reference = Fire(SHIP, start, 0.4, random.Random(8))
    for _ in range(5):
        original.step()
        reference.step()
    clone = original.clone(random.Random(0))
    for _ in range(20):
        clone.step()
    assert original.burning == reference.burning
    assert original.step() == reference.step()
