import random

from bots.bot4 import FEIN, RISK_AWARE, Bot4, Bot4Config, calculate_fire_risk
from helpers import ship_from_ascii
from ship import generate_ship
from sim import Outcome, place_entities, run_trial

TWO_ROUTES = ship_from_ascii("""
    #######
    .......
    .#####.
    .#####.
    .#####.
    .......
    #######
""")


def test_one_step_risk_matches_the_fire_rule():
    q = 0.3
    burning = {(1, 3)}
    risk = calculate_fire_risk(TWO_ROUTES, burning, q, horizon=1)
    # (1, 2) has K = 1 burning neighbor
    assert abs(risk[1][(1, 2)] - (1 - (1 - q) ** 1)) < 1e-12
    assert risk[1][(1, 3)] == 1.0
    assert (5, 0) not in risk[1]


def test_risk_only_grows_with_time():
    ship = generate_ship(30, seed=1)
    risk = calculate_fire_risk(ship, {ship.open_cells[100]}, 0.3, horizon=10)
    for s in range(10):
        for cell, p in risk[s].items():
            assert 0.0 <= p <= risk[s + 1][cell] <= 1.0


# fire starts in a pocket (6, 3) right under the short route along row 5.
# the long route goes up and around through row 1.
POCKET = ship_from_ascii("""
    #######
    .......
    .#####.
    .#####.
    .#####.
    .......
    ###.###
""")


def test_detours_around_fire_when_worth_it():
    # slow fire: walking right past it is risky, but it takes a long time to
    # reach the button, so the long way round is the better bet
    bot = Bot4(Bot4Config(max_detour_ratio=10.0))
    result = run_trial(POCKET, bot, (5, 0), (5, 6), (6, 3), 0.1, fire_seed=0)
    assert result.bot_path[1] == (4, 0)
    assert bot.log[0].mode == RISK_AWARE


def test_runs_for_it_when_detour_is_too_long():
    # same spot, but the default detour limit (2x) rules the long way out
    bot = Bot4()
    result = run_trial(POCKET, bot, (5, 0), (5, 6), (6, 3), 0.1, fire_seed=0)
    assert result.bot_path[1] == (5, 1)
    assert bot.fein_activated_at == 1


def test_never_steps_into_fire_and_logs_every_step():
    ship = generate_ship(30, seed=3)
    rng = random.Random(0)
    for _ in range(30):
        bot_start, button, fire_start = place_entities(ship, rng)
        bot = Bot4()
        result = run_trial(ship, bot, bot_start, button, fire_start, 0.3, rng.randrange(10**6))
        for t, cell in enumerate(result.bot_path[1:], start=1):
            # the cell can't have been burning before the bot stepped in
            assert result.ignition_time.get(cell, 10**9) >= t
        if result.outcome is not Outcome.GAVE_UP:
            assert len(bot.log) == result.steps
        assert all(entry.mode in (RISK_AWARE, FEIN) for entry in bot.log)
        if bot.fein_activated_at is not None:
            assert all(e.mode == FEIN for e in bot.log if e.t >= bot.fein_activated_at)


def test_does_not_lock_into_fein_when_fire_is_far():
    # fire far from the route at the start, so there's no detour and no reason to run yet
    ship = generate_ship(30, seed=3)
    rng = random.Random(1)
    early = 0
    for _ in range(30):
        bot_start, button, fire_start = place_entities(ship, rng)
        bot = Bot4()
        run_trial(ship, bot, bot_start, button, fire_start, 0.3, rng.randrange(10**6))
        early += bot.fein_activated_at == 1
    assert early < 10
