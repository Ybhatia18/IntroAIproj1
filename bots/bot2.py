"""Bot 2: every step, replan the shortest path avoiding the current fire cells."""

from bots.pathfinding import bfs_path
from ship import Cell
from sim import SimState


class Bot2:
    def start(self, state: SimState) -> None:
        pass

    def next_move(self, state: SimState) -> Cell | None:
        # replan every step around whatever is burning right now
        path = bfs_path(state.ship, state.bot, state.button, avoid=state.burning)
        if path is None:
            # fire never goes out so if theres no path now there never will be
            return None
        return path[1]  # path[0] is where we already are
