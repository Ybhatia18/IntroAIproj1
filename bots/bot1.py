"""Bot 1: plan the shortest path once, avoiding only the initial fire cell, then follow it."""

from bots.pathfinding import bfs_path
from ship import Cell
from sim import SimState


class Bot1:
    def start(self, state: SimState) -> None:
        # At t = 0 the only burning cell is the initial fire cell.
        self.path = bfs_path(state.ship, state.bot, state.button, avoid=set(state.burning))
        self.step = 0

    def next_move(self, state: SimState) -> Cell | None:
        if self.path is None:
            return None  # the button was unreachable from the start
        # The fire is ignored, so just take the next cell of the original plan.
        self.step += 1
        return self.path[self.step]
