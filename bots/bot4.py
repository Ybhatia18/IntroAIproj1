"""Bot 4 ("Travis Scott Bot"): risk-aware routing with a FE!N Mode fallback.

Every step the bot:
  1. estimates how likely each cell is to be on fire a few steps from now,
     using the fire rule P = 1 - (1 - q)^K pushed forward step by step,
  2. finds the path that best trades off length against that risk (Dijkstra),
  3. compares it with the plain shortest path that only avoids current fire,
     and if the careful route isn't worth it anymore, switches to FE!N Mode
     and just runs the shortest path from then on.
"""

import heapq
import math
from dataclasses import dataclass, field

from bots.pathfinding import bfs_path
from ship import Cell, Ship
from sim import SimState

RISK_AWARE = "RISK_AWARE"
FEIN = "FEIN"


@dataclass
class Bot4Config:
    """The knobs to experiment with. Nothing else in the algorithm is hard-coded."""

    # how much risk costs compared to just taking an extra step. needs to be big,
    # at like 3 the bot thought a 33% chance of dying was only worth 1 extra step lol
    risk_weight: float = 30.0
    # how far ahead to predict the fire. anything past this just uses the last prediction
    horizon: int = 20
    # if the careful path isnt at least this much safer than the short one, just run
    fein_margin: float = 0.02
    # if the careful path is this many times longer than the short one, also just run
    max_detour_ratio: float = 2.0


@dataclass
class StepLog:
    t: int
    mode: str
    path_length: int  # how many moves left on the path we picked
    risk_score: float  # guess at the chance that path gets us killed


@dataclass
class Bot4:
    config: Bot4Config = field(default_factory=Bot4Config)

    def start(self, state: SimState) -> None:
        self.mode = RISK_AWARE
        self.fein_activated_at: int | None = None  # when FE!N mode turned on (None if it never did)
        self.log: list[StepLog] = []

    def next_move(self, state: SimState) -> Cell | None:
        return bot4_next_move(self, state)


def calculate_fire_risk(
    ship: Ship, burning: set[Cell], q: float, horizon: int
) -> list[dict[Cell, float]]:
    """Estimate risk[s][cell] = chance the cell is burning after s more fire steps.

    risk[0] is just the current fire (1.0 for burning cells). Cells missing from a
    dict have risk 0. Each step uses the assignment's rule 1 - (1 - q)^K, except
    neighbors only count as "maybe burning", so each one contributes q * p(neighbor).
    When every neighbor is either surely burning or surely not, this is exactly
    1 - (1 - q)^K.
    """
    # stuff thats already burning is 100% burning
    current = {cell: 1.0 for cell in burning}
    risk = [current]
    for _ in range(horizon):
        # only cells touching something risky can pick up risk this step, so dont loop the whole grid
        candidates = set()
        for cell in current:
            candidates.update(ship.neighbors[cell])
        nxt = dict(current)  # copy so this step only uses last step's numbers (same idea as the real fire)
        for cell in candidates:
            p_now = current.get(cell, 0.0)
            if p_now == 1.0:
                continue  # already definitely burning
            # chance none of the neighbors spread to this cell. a neighbor thats
            # p% likely burning spreads with q * p, so if everything is 0 or 1
            # this turns back into the normal (1 - q)^K
            no_spread = 1.0
            for n in ship.neighbors[cell]:
                no_spread *= 1.0 - q * current.get(n, 0.0)
            # either it was already burning or it catches now
            nxt[cell] = p_now + (1.0 - p_now) * (1.0 - no_spread)
        risk.append(nxt)
        current = nxt
    return risk


def risk_at(risk: list[dict[Cell, float]], cell: Cell, steps: int) -> float:
    """Risk of cell after `steps` fire steps, reusing the last prediction past the horizon."""
    return risk[min(steps, len(risk) - 1)].get(cell, 0.0)


def danger_on_arrival(risk: list[dict[Cell, float]], cell: Cell, move: int, button: Cell) -> float:
    """Chance that arriving at cell on our `move`-th move goes wrong.

    The bot dies if the cell is already burning when it steps in, or catches
    during that same timestep, so that's `move` fire steps from now. The button
    only has to survive until we step on it, which is one fire step earlier.
    """
    # the button just has to still be there when we step on it, 1 fire step earlier
    if cell == button:
        return risk_at(risk, cell, move - 1)
    return risk_at(risk, cell, move)


def path_success_chance(path: list[Cell], risk: list[dict[Cell, float]], button: Cell) -> float:
    """Estimated chance of making it along path, treating each cell as independent."""
    # skip path[0] since thats where the bot already is
    chance = 1.0
    for move, cell in enumerate(path[1:], start=1):
        chance *= 1.0 - danger_on_arrival(risk, cell, move, button)
    return chance


def calculate_risk_weighted_path(
    ship: Ship, start: Cell, button: Cell, burning: set[Cell],
    risk: list[dict[Cell, float]], risk_weight: float,
) -> list[Cell] | None:
    """Dijkstra where entering a cell costs 1 + risk_weight * -log(1 - danger).

    Adding up -log(1 - danger) along a path is the same as -log(chance of
    surviving the path), so this really minimizes
    path length + risk_weight * (how risky the whole path is).
    """
    # heap holds (cost so far, moves so far, cell). need moves to know WHEN we'd
    # get to a cell, since cells get more dangerous the longer we take
    heap = [(0.0, 0, start)]
    best_cost = {start: 0.0}
    parent: dict[Cell, Cell | None] = {start: None}
    while heap:
        cost, moves, cell = heapq.heappop(heap)
        if cost > best_cost[cell]:
            continue  # old heap entry, already found a cheaper way here
        if cell == button:
            # same as bfs, follow parents back and flip it
            path = []
            while cell is not None:
                path.append(cell)
                cell = parent[cell]
            return path[::-1]
        for n in ship.neighbors[cell]:
            if n in burning:
                continue  # obviously dont walk into fire
            # cap it at 0.999 so log(0) doesnt blow up on cells that are basically gonna burn
            danger = min(danger_on_arrival(risk, n, moves + 1, button), 0.999)
            # 1 for the step + the risk part. summing -log(1 - danger) is the same as
            # -log(chance we survive the whole path) so dijkstra is minimizing length + risk
            new_cost = cost + 1.0 + risk_weight * -math.log(1.0 - danger)
            if new_cost < best_cost.get(n, math.inf):
                best_cost[n] = new_cost
                parent[n] = cell
                heapq.heappush(heap, (new_cost, moves + 1, n))
    return None


def calculate_shortest_safe_path(ship: Ship, start: Cell, button: Cell, burning: set[Cell]) -> list[Cell] | None:
    """Plain shortest path that only avoids cells already on fire (same as Bot 2)."""
    return bfs_path(ship, start, button, avoid=burning)


def should_enter_fein_mode(
    careful_path: list[Cell] | None, short_path: list[Cell],
    risk: list[dict[Cell, float]], button: Cell, config: Bot4Config,
) -> bool:
    """True when the careful route isn't worth it anymore and we should just run."""
    if careful_path is None:
        return True  # no careful path at all so might as well run
    # careful path isnt a detour (same length as the shortest one), so being careful
    # costs nothing right now. stay careful, otherwise we'd lock into FE!N at t=1
    # every time the fire starts far away
    if len(careful_path) <= len(short_path):
        return False
    careful_chance = path_success_chance(careful_path, risk, button)
    short_chance = path_success_chance(short_path, risk, button)
    # detour barely helps (or makes it worse since the button could burn while we walk around)
    if careful_chance - short_chance < config.fein_margin:
        return True
    # detour is way too long, and the predictions that far out arent that reliable anyway
    if len(careful_path) - 1 > config.max_detour_ratio * (len(short_path) - 1):
        return True
    return False


def bot4_next_move(bot: Bot4, state: SimState) -> Cell | None:
    """One decision for Bot 4. Recomputes everything from the current fire every step."""
    short_path = calculate_shortest_safe_path(state.ship, state.bot, state.button, state.burning)
    if short_path is None:
        return None  # fire never goes out so if were cut off now were cut off forever

    # redo the whole risk map every step since the fire just moved
    risk = calculate_fire_risk(state.ship, state.burning, state.q, bot.config.horizon)

    if bot.mode == RISK_AWARE:
        careful_path = calculate_risk_weighted_path(
            state.ship, state.bot, state.button, state.burning, risk, bot.config.risk_weight
        )
        if should_enter_fein_mode(careful_path, short_path, risk, state.button, bot.config):
            # once we commit to running we dont go back to being careful
            bot.mode = FEIN
            bot.fein_activated_at = state.t + 1
        else:
            path = careful_path
    if bot.mode == FEIN:
        path = short_path  # FE!N mode, just send it

    # save what happened this step for debugging / the writeup
    bot.log.append(StepLog(
        t=state.t + 1,
        mode=bot.mode,
        path_length=len(path) - 1,
        risk_score=1.0 - path_success_chance(path, risk, state.button),
    ))
    return path[1]  # path[0] is where we already are


def bot4_summary(bot: Bot4, result) -> dict:
    """Everything worth recording about one Bot 4 trial (pass in run_trial's result)."""
    return {
        "outcome": result.outcome.name,
        "success": result.outcome.name == "SUCCESS",
        "steps": result.steps,
        "fein_activated_at": bot.fein_activated_at,
        "log": bot.log,
    }
