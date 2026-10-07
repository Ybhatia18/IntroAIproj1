"""Bot 2: every step, replan the shortest path avoiding the current fire cells."""

from bots.pathfinding import bfs_path
from ship import Cell
from sim import SimState


class Bot2:
    def start(self, state: SimState) -> None:
        pass

    def next_move(self, state: SimState) -> Cell | None:
        path = bfs_path(state.ship, state.bot, state.button, avoid=state.burning)
        if path is None:
            # The fire only grows, so once it cuts off the button it stays cut off.
            return None
        return path[1]
