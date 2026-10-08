"""Run all the bots on lots of random ships and save the results to a CSV.

Examples:
    # coarse sweep over q = 0, 0.05, ..., 1
    python experiments.py sweep --trials 200 --out results/coarse.csv
    # dense sweep over the interesting range
    python experiments.py sweep --q-start 0.2 --q-stop 0.6 --q-step 0.02 --trials 1000 --out results/dense.csv
    # try different values of one Bot 4 setting
    python experiments.py tune --param risk_weight --values 5 15 30 60 --out results/tune_risk_weight.csv
"""

import argparse
import csv
import os
import random
from dataclasses import replace
from multiprocessing import Pool

from bots.bot1 import Bot1
from bots.bot2 import Bot2
from bots.bot3 import Bot3
from bots.bot4 import Bot4, Bot4Config
from bots.pathfinding import bfs_path
from ship import generate_ship
from sim import place_entities, run_trial

BOTS = {"bot1": Bot1, "bot2": Bot2, "bot3": Bot3, "bot4": Bot4}
FIELDS = ["q", "trial", "bot", "param", "value", "outcome", "steps",
          "bot_to_button", "fire_to_button", "fein_activated_at"]


def make_trial(D: int, base_seed: int, trial: int):
    """Ship + placement + fire seed for trial number `trial`.

    Only depends on the trial number (not q), so trial 7 is the same ship and
    starting spots at every q. That way the curves are compared on the same setups.
    """
    rng = random.Random(base_seed * 1_000_003 + trial)
    ship = generate_ship(D, seed=rng.randrange(2**32))
    bot_start, button, fire_start = place_entities(ship, rng)
    fire_seed = rng.randrange(2**32)
    return ship, bot_start, button, fire_start, fire_seed


def path_length(ship, start, goal):
    path = bfs_path(ship, start, goal, avoid=set())
    return len(path) - 1


def run_job(job: dict) -> list[dict]:
    """Run every requested bot on one (q, trial) setup. Returns one row per bot."""
    ship, bot_start, button, fire_start, fire_seed = make_trial(job["D"], job["base_seed"], job["trial"])
    rows = []
    for name, make_bot in job["bots"]:
        bot = make_bot()
        result = run_trial(ship, bot, bot_start, button, fire_start, job["q"], fire_seed)
        rows.append({
            "q": job["q"],
            "trial": job["trial"],
            "bot": name,
            "param": job.get("param", ""),
            "value": job.get("value", ""),
            "outcome": result.outcome.name,
            "steps": result.steps,
            # how far the bot and the fire start from the button, handy for failure analysis
            "bot_to_button": path_length(ship, bot_start, button),
            "fire_to_button": path_length(ship, fire_start, button),
            "fein_activated_at": getattr(bot, "fein_activated_at", ""),
        })
    return rows


class MakeBot4:
    """A picklable "make a Bot 4 with this config" (lambdas can't go to worker processes)."""

    def __init__(self, config: Bot4Config):
        self.config = config

    def __call__(self):
        return Bot4(self.config)


def q_values(start: float, stop: float, step: float) -> list[float]:
    count = round((stop - start) / step)
    return [round(start + i * step, 4) for i in range(count + 1)]


def run_jobs(jobs: list[dict], out: str, workers: int) -> None:
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        with Pool(workers) as pool:
            for i, rows in enumerate(pool.imap_unordered(run_job, jobs, chunksize=4), start=1):
                writer.writerows(rows)
                if i % 200 == 0 or i == len(jobs):
                    print(f"  {i}/{len(jobs)} setups done", flush=True)
    print(f"saved {out}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["sweep", "tune"])
    parser.add_argument("--D", type=int, default=40)
    parser.add_argument("--q-start", type=float, default=0.0)
    parser.add_argument("--q-stop", type=float, default=1.0)
    parser.add_argument("--q-step", type=float, default=0.05)
    parser.add_argument("--trials", type=int, default=200, help="setups per q")
    parser.add_argument("--seed", type=int, default=440)
    parser.add_argument("--workers", type=int, default=os.cpu_count())
    parser.add_argument("--param", help="tune mode: which Bot4Config field to vary")
    parser.add_argument("--values", type=float, nargs="+", help="tune mode: values to try")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    qs = q_values(args.q_start, args.q_stop, args.q_step)
    base = {"D": args.D, "base_seed": args.seed}
    jobs = []
    if args.mode == "sweep":
        bots = list(BOTS.items())
        for q in qs:
            for trial in range(args.trials):
                jobs.append({**base, "q": q, "trial": trial, "bots": bots})
    else:
        if not args.param or not args.values:
            parser.error("tune needs --param and --values")
        for value in args.values:
            if args.param == "horizon":
                value = int(value)
            config = replace(Bot4Config(), **{args.param: value})
            bots = [("bot4", MakeBot4(config))]
            for q in qs:
                for trial in range(args.trials):
                    jobs.append({**base, "q": q, "trial": trial, "bots": bots,
                                 "param": args.param, "value": value})

    print(f"{len(jobs)} setups, D={args.D}, {args.workers} workers")
    run_jobs(jobs, args.out, args.workers)


if __name__ == "__main__":
    main()
