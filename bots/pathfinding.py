"""Shortest-path search shared by the bots."""

from collections import deque

from ship import Cell, Ship


def bfs_path(ship: Ship, start: Cell, goal: Cell, avoid: set[Cell]) -> list[Cell] | None:
    """Shortest path from start to goal that never enters a cell in avoid.

    Every move costs the same, so breadth-first search finds a shortest path.
    Returns the path as [start, ..., goal], or None if no such path exists.
    The start cell is allowed even if it is in avoid (the bot is already there).
    """
    parent = {start: None}  # also serves as the visited set
    queue = deque([start])
    while queue:
        cell = queue.popleft()
        if cell == goal:
            # Walk the parent links back to the start, then flip the order.
            path = []
            while cell is not None:
                path.append(cell)
                cell = parent[cell]
            return path[::-1]
        for n in ship.neighbors[cell]:
            if n not in parent and n not in avoid:
                parent[n] = cell
                queue.append(n)
    return None
