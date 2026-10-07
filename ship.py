"""Ship generation for CS 440 Project 1.

The ship is a D x D grid of open/blocked cells built in two phases:

  Step 3 (grow_maze): starting from one open interior cell, repeatedly open a
  random blocked cell that has exactly one open neighbor. This grows a tree-like
  maze with no loops.

  Step 5 (reduce_dead_ends): repeatedly pick a random dead end (an open cell
  with exactly one open neighbor) and open one of its blocked neighbors, until
  the number of dead ends is at most half of what it was. This adds loops.

This module must stay self-contained (no imports from fire.py, sim.py, bots/)
because it is reused in later projects.
"""

import random

import numpy as np

Cell = tuple[int, int]


class RandomPickSet:
    """A set of cells that supports O(1) add, remove, membership and uniform pick.

    Cells live in a list so we can pick a random index in O(1). A dict maps each
    cell to its index in that list. To remove a cell without shifting the list,
    we move the last cell into its slot and pop the end ("swap-remove").
    """

    def __init__(self) -> None:
        self.items: list[Cell] = []
        self.index: dict[Cell, int] = {}

    def __len__(self) -> int:
        return len(self.items)

    def __contains__(self, cell: Cell) -> bool:
        return cell in self.index

    def add(self, cell: Cell) -> None:
        if cell in self.index:
            return
        self.index[cell] = len(self.items)
        self.items.append(cell)

    def remove(self, cell: Cell) -> None:
        if cell not in self.index:
            return
        i = self.index.pop(cell)
        last = self.items.pop()
        # If the removed cell was not the last one, the last cell fills its slot.
        if i < len(self.items):
            self.items[i] = last
            self.index[last] = i

    def pick(self, rng: random.Random) -> Cell:
        return self.items[rng.randrange(len(self.items))]


class Ship:
    """An immutable ship layout.

    Attributes:
        D: side length of the grid.
        open: bool array of shape (D, D), True = open.
        open_cells: all open cells in row-major order.
        neighbors: for each open cell, its open up/down/left/right neighbors.
        initial_dead_ends: dead-end count after step 3 (None if not generated).
        final_dead_ends: dead-end count after step 5 (None if not generated).
    """

    def __init__(
        self,
        open_grid: np.ndarray,
        initial_dead_ends: int | None = None,
        final_dead_ends: int | None = None,
    ) -> None:
        """Build a Ship from a square boolean grid (True = open)."""
        grid = np.array(open_grid, dtype=bool)

        self.D: int = grid.shape[0]
        self.open: np.ndarray = grid
        self.initial_dead_ends = initial_dead_ends
        self.final_dead_ends = final_dead_ends

        self.open_cells: list[Cell] = [
            (int(r), int(c)) for r, c in zip(*np.nonzero(grid))
        ]
        # The layout never changes, and bots/fire ask for neighbors constantly,
        # so compute them once here.
        self.neighbors: dict[Cell, tuple[Cell, ...]] = {}
        for cell in self.open_cells:
            self.neighbors[cell] = tuple(
                n for n in grid_neighbors(self.D, cell) if grid[n]
            )


def grid_neighbors(D: int, cell: Cell) -> list[Cell]:
    """The up/down/left/right neighbors of cell that lie inside a D x D grid."""
    r, c = cell
    result = []
    for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
        if 0 <= nr < D and 0 <= nc < D:
            result.append((nr, nc))
    return result


def _grow_maze(D: int, rng: random.Random) -> tuple[np.ndarray, np.ndarray]:
    """Steps 1-3: open a random interior cell, then grow until no candidates remain.

    Returns (open_grid, open_neighbor_count). The count array holds, for every
    cell (open or blocked), how many of its neighbors are open. It is returned
    so step 5 can keep updating it instead of recounting.
    """
    is_open = np.zeros((D, D), dtype=bool)
    count = np.zeros((D, D), dtype=np.int8)
    # Candidates: blocked cells with exactly one open neighbor.
    candidates = RandomPickSet()

    def open_cell(x: Cell) -> None:
        is_open[x] = True
        candidates.remove(x)
        for y in grid_neighbors(D, x):
            count[y] += 1
            if is_open[y]:
                continue
            # y just gained an open neighbor. At 1 it becomes a candidate; at 2
            # it stops being one (opening it would now create a loop). Above 2
            # it was already excluded, so nothing changes.
            if count[y] == 1:
                candidates.add(y)
            elif count[y] == 2:
                candidates.remove(y)

    start = (rng.randint(1, D - 2), rng.randint(1, D - 2))
    open_cell(start)
    while len(candidates) > 0:
        open_cell(candidates.pick(rng))

    return is_open, count


def _reduce_dead_ends(
    is_open: np.ndarray, count: np.ndarray, rng: random.Random
) -> tuple[int, int]:
    """Steps 4-5: open neighbors of random dead ends until at most half remain.

    Modifies is_open and count in place. Returns (N0, final_dead_end_count).
    """
    D = is_open.shape[0]

    # Step 4 is the only full scan; after this the dead-end set is kept up to date.
    dead_ends = RandomPickSet()
    for r in range(D):
        for c in range(D):
            if is_open[r, c] and count[r, c] == 1:
                dead_ends.add((r, c))
    n0 = len(dead_ends)

    # "Cut by at least half": stop once current <= N0 / 2, done in integers.
    while 2 * len(dead_ends) > n0:
        d = dead_ends.pick(rng)
        # A dead end has exactly one open neighbor and at least two in-grid
        # neighbors (even in a corner), so this list is never empty.
        blocked = [y for y in grid_neighbors(D, d) if not is_open[y]]
        y = blocked[rng.randrange(len(blocked))]

        is_open[y] = True
        # y is adjacent to d, so it has at least one open neighbor. If d is its
        # only one, y is now a dead end itself (the dead end moved forward).
        if count[y] == 1:
            dead_ends.add(y)
        # Every open neighbor of y gains an open neighbor. d is one of them, but
        # y can touch other dead ends too, and all of them stop being dead ends.
        for z in grid_neighbors(D, y):
            count[z] += 1
            if is_open[z]:
                if count[z] == 1:
                    dead_ends.add(z)
                elif count[z] == 2:
                    dead_ends.remove(z)

    return n0, len(dead_ends)


def generate_ship(D: int, seed: int | None = None) -> Ship:
    """Generate a D x D ship using the assignment's procedure.

    Args:
        D: grid side length.
        seed: the same seed always gives the same ship. None means unseeded.
    """
    rng = random.Random(seed)
    is_open, count = _grow_maze(D, rng)
    n0, final = _reduce_dead_ends(is_open, count, rng)
    return Ship(is_open, initial_dead_ends=n0, final_dead_ends=final)
