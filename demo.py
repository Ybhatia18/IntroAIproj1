"""Print a generated ship and a few steps of fire spreading through it.

Example:
    python demo.py --D 20 --seed 1 --q 0.4
"""

import argparse
import random

from fire import Fire
from render import render_ascii
from ship import generate_ship
from sim import place_entities


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--D", type=int, default=20)
    parser.add_argument("--q", type=float, default=0.4)
    parser.add_argument("--seed", type=int, default=1)
    args = parser.parse_args()

    ship = generate_ship(args.D, seed=args.seed)
    print(render_ascii(ship))
    print(f"open fraction: {len(ship.open_cells) / ship.D**2:.1%}")
    print(f"dead ends: {ship.initial_dead_ends} before step 5, {ship.final_dead_ends} after")

    # same seed for placement + fire so the demo is the same every run
    rng = random.Random(args.seed)
    bot, button, fire_start = place_entities(ship, rng)
    fire = Fire(ship, fire_start, args.q, rng)
    for _ in range(4):
        print(f"\nt = {fire.t}")
        print(render_ascii(ship, bot, button, fire.burning))
        fire.step()


if __name__ == "__main__":
    main()
