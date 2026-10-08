"""Bot 3: every step, replan avoiding fire cells and their neighbors if possible;
otherwise fall back to avoiding only the fire cells (Bot 2's plan)."""

from bots.pathfinding import bfs_path
from ship import Cell
from sim import SimState


class Bot3:
    def start(self, state: SimState) -> None:
        pass

    def next_move(self, state: SimState) -> Cell | None:
        # fire cells + every cell touching one
        near_fire = set(state.burning)
        for cell in state.burning:
            near_fire.update(state.ship.neighbors[cell])

        # try to keep a 1 cell gap from the fire first
        path = bfs_path(state.ship, state.bot, state.button, avoid=near_fire)
        if path is None:
            # no safe path so fall back to just avoiding the fire (same as bot 2)
            path = bfs_path(state.ship, state.bot, state.button, avoid=state.burning)
        if path is None:
            return None  # totally cut off
        return path[1]
