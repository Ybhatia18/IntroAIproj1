import random

from bots.bot1 import Bot1
from bots.bot2 import Bot2
from bots.bot3 import Bot3
from bots.pathfinding import bfs_path
from helpers import distances_from, ship_from_ascii
from ship import generate_ship
from sim import Outcome, place_entities, run_trial

# Two routes from the left side to the right side of the ship: a short top
# corridor (row 1) and a longer bottom loop (rows 1-5).
TWO_ROUTES = ship_from_ascii("""
    #######
    .......
    .#####.
    .#####.
    .#####.
    .......
    #######
""")


def test_bfs_finds_shortest_path_and_respects_avoid():
    ship = generate_ship(30, seed=2)
    start, goal = ship.open_cells[0], ship.open_cells[-1]
    path = bfs_path(ship, start, goal, avoid=set())
    assert path[0] == start and path[-1] == goal
    assert len(path) - 1 == distances_from(ship, start)[goal]
    for a, b in zip(path, path[1:]):
        assert b in ship.neighbors[a]
    blocked = set(path[1:-1])
    detour = bfs_path(ship, start, goal, avoid=blocked)
    assert detour is None or blocked.isdisjoint(detour)


def test_all_bots_take_the_short_route_when_fire_is_away():
    # Fire at (5, 3) is on the long loop and never spreads (q = 0).
    for bot in (Bot1(), Bot2(), Bot3()):
        result = run_trial(TWO_ROUTES, bot, (1, 0), (1, 6), (5, 3), 0.0, fire_seed=0)
        assert result.outcome is Outcome.SUCCESS
        assert result.steps == 6


def test_bot1_follows_its_first_plan_no_matter_what():
    ship = generate_ship(30, seed=5)
    rng = random.Random(0)
    for _ in range(50):
        bot_start, button, fire_start = place_entities(ship, rng)
        plan = bfs_path(ship, bot_start, button, avoid={fire_start})
        result = run_trial(ship, Bot1(), bot_start, button, fire_start, 0.3, rng.randrange(10**6))
        if plan is not None:
            assert result.bot_path == plan[: len(result.bot_path)]


def test_bot3_keeps_a_buffer_when_it_can():
    # Fire at (1, 3) on the short corridor. Bot 3 must not step next to it if
    # the long loop exists; with q = 0 it should take the loop and succeed.
    result = run_trial(TWO_ROUTES, Bot3(), (1, 0), (1, 6), (1, 3), 0.0, fire_seed=0)
    assert result.outcome is Outcome.SUCCESS
    near_fire = {(1, 2), (1, 4)}
    assert near_fire.isdisjoint(result.bot_path)


def test_bot2_gives_up_when_cut_off():
    corridor = ship_from_ascii("""
        #####
        #####
        .....
        #####
        #####
    """)
    result = run_trial(corridor, Bot2(), (2, 0), (2, 4), (2, 2), 0.0, fire_seed=0)
    assert result.outcome is Outcome.GAVE_UP
