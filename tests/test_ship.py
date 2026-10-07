import random
import time

import numpy as np

from helpers import distances_from
from ship import _grow_maze, _reduce_dead_ends, generate_ship, grid_neighbors


def count_open_neighbors(is_open, cell):
    return sum(1 for n in grid_neighbors(is_open.shape[0], cell) if is_open[n])


def count_dead_ends(is_open):
    D = is_open.shape[0]
    return sum(
        1 for r in range(D) for c in range(D)
        if is_open[r, c] and count_open_neighbors(is_open, (r, c)) == 1
    )


def test_all_open_cells_reachable():
    for seed in range(10):
        ship = generate_ship(30, seed=seed)
        assert set(distances_from(ship, ship.open_cells[0])) == set(ship.open_cells)


def test_step3_leaves_no_blocked_cell_with_one_open_neighbor():
    for seed in range(10):
        is_open, _ = _grow_maze(30, random.Random(seed))
        for r in range(30):
            for c in range(30):
                if not is_open[r, c]:
                    assert count_open_neighbors(is_open, (r, c)) != 1


def test_step5_halves_dead_ends():
    for seed in range(10):
        is_open, count = _grow_maze(30, random.Random(seed))
        before = count_dead_ends(is_open)
        _reduce_dead_ends(is_open, count, random.Random(seed))
        assert 2 * count_dead_ends(is_open) <= before


def test_seeds():
    assert np.array_equal(generate_ship(40, seed=7).open, generate_ship(40, seed=7).open)
    assert not np.array_equal(generate_ship(40, seed=7).open, generate_ship(40, seed=8).open)


def test_neighbors_match_grid():
    ship = generate_ship(25, seed=0)
    assert set(ship.neighbors) == set(ship.open_cells)
    for cell in ship.open_cells:
        expected = {n for n in grid_neighbors(ship.D, cell) if ship.open[n]}
        assert set(ship.neighbors[cell]) == expected


def test_d100_under_one_second():
    start = time.perf_counter()
    generate_ship(100, seed=0)
    assert time.perf_counter() - start < 1.0
