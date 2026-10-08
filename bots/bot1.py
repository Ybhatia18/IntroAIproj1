"""Bot 1: plan the shortest path once, avoiding only the initial fire cell, then follow it."""

from bots.pathfinding import bfs_path
from ship import Cell
from sim import SimState


class Bot1:
    def start(self, state: SimState) -> None:
        # plan once at t = 0. only thing burning right now is the first fire cell
        self.path = bfs_path(state.ship, state.bot, state.button, avoid=set(state.burning))
        self.step = 0

    def next_move(self, state: SimState) -> Cell | None:
        if self.path is None:
            return None  # couldnt reach the button at all
        # bot 1 ignores the fire spreading, just keep following the original plan
        self.step += 1
        return self.path[self.step]
