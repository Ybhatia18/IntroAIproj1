"""Simulation loop for CS 440 Project 1: placement, the per-timestep loop, the bot interface."""

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol

from fire import Fire
from ship import Cell, Ship


class Outcome(Enum):
    SUCCESS = "success"
    BURNED = "burned"  # bot and fire shared a cell
    BUTTON_BURNED = "button_burned"  # button caught fire, the task can no longer succeed
    GAVE_UP = "gave_up"  # bot returned None
    TIMEOUT = "timeout"  # hit max_steps


@dataclass
class SimState:
    """What a bot is allowed to see.

    Attributes:
        ship: the (immutable) ship.
        bot: the bot's current cell.
        button: the button cell.
        burning: the real fire's burning set. This is a live view that changes
            as the fire spreads; bots must treat it as read-only.
        q: flammability.
        t: number of timesteps completed so far. The move a bot returns from
            next_move is made at timestep t + 1.
    """

    ship: Ship
    bot: Cell
    button: Cell
    burning: set[Cell]
    q: float
    t: int
    # the real fire. bots shouldnt touch this, use fork_fire instead, since
    # the real rng would basically let a bot see the future
    _fire: Fire = field(repr=False, compare=False)

    def fork_fire(self, rng: random.Random) -> Fire:
        """A copy of the real fire's current state, driven by rng, for look-ahead."""
        return self._fire.clone(rng)


class Bot(Protocol):
    def start(self, state: SimState) -> None:
        """Called once at t = 0, before the first move."""
        ...

    def next_move(self, state: SimState) -> Cell | None:
        """Return the current cell (stay), an adjacent open cell, or None to give up."""
        ...


@dataclass
class TrialResult:
    outcome: Outcome
    steps: int  # timesteps completed
    bot_path: list[Cell]  # bot position at every timestep, starting at t = 0
    ignition_time: dict[Cell, int]


def place_entities(ship: Ship, rng: random.Random) -> tuple[Cell, Cell, Cell]:
    """Pick three distinct open cells uniformly at random.

    Returns (bot_start, button, fire_start).
    """
    # sample picks 3 different cells, so they can never overlap
    bot_start, button, fire_start = rng.sample(ship.open_cells, 3)
    return bot_start, button, fire_start


def run_trial(
    ship: Ship,
    bot: Bot,
    bot_start: Cell,
    button: Cell,
    fire_start: Cell,
    q: float,
    fire_seed: int,
    max_steps: int | None = None,
) -> TrialResult:
    """Run one trial of bot on ship and return how it ended.

    The fire is driven only by random.Random(fire_seed), so the same
    (ship, fire_start, q, fire_seed) gives the same fire for every bot.

    Raises:
        ValueError: if the bot returns an illegal move.
    """
    if max_steps is None:
        # big enough for any real path, but makes sure a bot that just sits
        # there at q = 0 doesnt run forever
        max_steps = 4 * ship.D * ship.D

    fire = Fire(ship, fire_start, q, random.Random(fire_seed))
    state = SimState(
        ship=ship, bot=bot_start, button=button, burning=fire.burning, q=q, t=0, _fire=fire
    )
    bot_path = [bot_start]

    # every way the trial can end goes through here so the result is built the same way
    def finish(outcome: Outcome) -> TrialResult:
        return TrialResult(outcome, state.t, bot_path, dict(fire.ignition_time))

    bot.start(state)

    while state.t < max_steps:
        # 1. bot picks a move
        move = bot.next_move(state)
        if move is None:
            return finish(Outcome.GAVE_UP)
        # only allowed to stay or move to an open neighbor, anything else is a bug
        if move != state.bot and move not in ship.neighbors[state.bot]:
            raise ValueError(
                f"illegal move from {state.bot} to {move} at t={state.t + 1}"
            )

        # 2. bot moves (and dies if it walked into fire)
        state.t += 1
        state.bot = move
        bot_path.append(move)
        if move in fire.burning:
            return finish(Outcome.BURNED)

        # 3. button check has to happen BEFORE the fire spreads
        if move == button:
            return finish(Outcome.SUCCESS)

        # 4. fire spreads
        fire.step()

        # 5. did the fire get the bot? check this before the button so if both
        # burn on the same step it counts as the bot burning
        if state.bot in fire.burning:
            return finish(Outcome.BURNED)
        if button in fire.burning:
            return finish(Outcome.BUTTON_BURNED)

    return finish(Outcome.TIMEOUT)
