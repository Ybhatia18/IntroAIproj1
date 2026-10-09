"""Fire simulation for CS 440 Project 1.

Each step, every open non-burning cell with K burning neighbors catches fire
with probability 1 - (1 - q)^K. Burning cells burn forever, and the update is
synchronous: all ignitions in a step are decided from the state before it.
"""

import random

from ship import Cell, Ship


class Fire:
    """The state of a spreading fire on a fixed ship.

    Attributes:
        burning: cells currently on fire.
        ignition_time: step at which each burning cell caught fire (start = 0).
        frontier: each open, non-burning cell with K >= 1 burning neighbors,
            mapped to its K. Only these cells can ignite. Treat as read-only.
        t: number of steps taken so far.
    """

    def __init__(self, ship: Ship, start: Cell, q: float, rng: random.Random) -> None:
        self.ship = ship
        self.q = q
        self.rng = rng
        self.t = 0
        self.burning: set[Cell] = set()
        self.ignition_time: dict[Cell, int] = {}
        self.frontier: dict[Cell, int] = {}
        # K can only be 0-4 so just precompute 1 - (1 - q)^K for each
        self._ignite_prob = [1.0 - (1.0 - q) ** k for k in range(5)]
        self._ignite(start)

    def _ignite(self, cell: Cell) -> None:
        # update the frontier here so step() never has to scan the whole grid
        self.burning.add(cell)
        self.ignition_time[cell] = self.t
        self.frontier.pop(cell, None)
        for n in self.ship.neighbors[cell]:
            if n not in self.burning:
                self.frontier[n] = self.frontier.get(n, 0) + 1

    def step(self) -> set[Cell]:
        """Advance the fire one step. Returns the cells that ignited this step."""
        self.t += 1
        # first decide who catches fire using the state from BEFORE this step.
        # dont change anything yet, otherwise a cell that just caught fire would
        # count toward its neighbors K in the same step (not synchronous)
        # sorted + one random() per cell every time so the same seed always
        # gives the exact same fire no matter what the bot does
        newly_ignited = []
        for cell in sorted(self.frontier):
            if self.rng.random() < self._ignite_prob[self.frontier[cell]]:
                newly_ignited.append(cell)
        # now actually light them all at once
        for cell in newly_ignited:
            self._ignite(cell)
        return set(newly_ignited)

    def clone(self, rng: random.Random) -> "Fire":
        """An independent copy of the current state, driven by rng from now on.

        The ship is shared (it is immutable); the mutable state is copied, so
        stepping the clone never touches this fire or its random stream.
        """
        copy = Fire.__new__(Fire)
        copy.ship = self.ship
        copy.q = self.q
        copy.rng = rng
        copy.t = self.t
        # copy the sets/dicts (not just point to them) so the clone and the real fire dont share state
        copy.burning = set(self.burning)
        copy.ignition_time = dict(self.ignition_time)
        copy.frontier = dict(self.frontier)
        copy._ignite_prob = self._ignite_prob
        return copy


def fire_timeline(
    ship: Ship, start: Cell, q: float, seed: int, max_steps: int
) -> dict[Cell, int]:
    """Run a fire until it can no longer spread (or max_steps) and return ignition times.

    Uses random.Random(seed) exactly the way sim.run_trial does with its
    fire_seed, so the result agrees with any trial using the same arguments on
    every step that trial ran.
    """
    fire = Fire(ship, start, q, random.Random(seed))
    while fire.t < max_steps and fire.frontier:
        fire.step()
    return dict(fire.ignition_time)
