"""Small utilities shared by the tests (not part of the project's API)."""

from collections import deque

import numpy as np

from ship import Cell, Ship


def distances_from(ship: Ship, start: Cell) -> dict[Cell, int]:
    """Plain BFS distances over open cells."""
    dist = {start: 0}
    queue = deque([start])
    while queue:
        cell = queue.popleft()
        for n in ship.neighbors[cell]:
            if n not in dist:
                dist[n] = dist[cell] + 1
                queue.append(n)
    return dist


def ship_from_ascii(text: str) -> Ship:
    """Build a Ship from rows of '.' (open) and '#' (blocked)."""
    rows = [line.strip() for line in text.strip().splitlines()]
    return Ship(np.array([[ch == "." for ch in row] for row in rows]))


class StandStill:
    def start(self, state):
        pass

    def next_move(self, state):
        return state.bot


class Scripted:
    """Follows a fixed list of cells, then stands still."""

    def __init__(self, moves):
        self.moves = list(moves)

    def start(self, state):
        self.i = 0

    def next_move(self, state):
        if self.i < len(self.moves):
            self.i += 1
            return self.moves[self.i - 1]
        return state.bot


class RandomWalker:
    """Moves to a random open neighbor (or stays) using its own seeded RNG."""

    def __init__(self, rng):
        self.rng = rng

    def start(self, state):
        pass

    def next_move(self, state):
        return self.rng.choice(state.ship.neighbors[state.bot] + (state.bot,))
