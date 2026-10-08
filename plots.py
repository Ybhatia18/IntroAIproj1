"""Make the writeup charts from the CSVs that experiments.py saves.

Examples:
    python plots.py success --csv results/coarse.csv --out figures/success_full.png
    python plots.py success --csv results/dense.csv --out figures/success_dense.png
    python plots.py outcomes --csv results/dense.csv --out figures/outcomes.png
    python plots.py head2head --csv results/dense.csv --out figures/bot4_vs_bot3.png
    python plots.py tuning --csv results/tune_risk_weight.csv --out figures/tune_risk_weight.png
    python plots.py riskmap --out figures/risk_map.png
    python plots.py examples --csv results/dense.csv --out figures/examples
"""

import argparse
import csv
import os
import random
from collections import defaultdict

import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.figure import Figure

from bots.bot4 import calculate_fire_risk
from fire import Fire
from experiments import BOTS, make_trial
from render import BLOCKED_COLOR, BOT_COLOR, BUTTON_COLOR, save_image
from ship import generate_ship
from sim import place_entities, run_trial

# colorblind-checked palette, always in this order. lines also get different
# marker shapes so they still work printed in black and white
SERIES_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
MARKERS = ["o", "s", "^", "D"]
BOT_LABELS = {"bot1": "Bot 1", "bot2": "Bot 2", "bot3": "Bot 3", "bot4": "Bot 4"}
OUTCOMES = ["SUCCESS", "BURNED", "BUTTON_BURNED", "GAVE_UP"]
OUTCOME_LABELS = {"SUCCESS": "success", "BURNED": "bot burned",
                  "BUTTON_BURNED": "button burned", "GAVE_UP": "gave up (cut off)"}
TEXT = "#2b2b2b"
MUTED = "#6b6b6b"
GRID = "#e4e4e1"


def load(path: str) -> list[dict]:
    with open(path) as f:
        return list(csv.DictReader(f))


def new_figure(width=7.0, height=4.2, ncols=1, nrows=1, sharey=False):
    fig = Figure(figsize=(width, height), dpi=200, layout="constrained")
    axes = fig.subplots(nrows, ncols, sharey=sharey, squeeze=False)
    for ax in axes.flat:
        # keep the grid and axes quiet so the data stands out
        ax.grid(color=GRID, linewidth=0.6)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color(MUTED)
        ax.tick_params(colors=MUTED, labelsize=8)
        ax.xaxis.label.set_color(TEXT)
        ax.yaxis.label.set_color(TEXT)
    return fig, axes


def success_rates(rows: list[dict], key: str) -> dict:
    """{(series, q): (rate, n)} where series is the value of rows[key]."""
    counts = defaultdict(lambda: [0, 0])
    for r in rows:
        c = counts[(r[key], float(r["q"]))]
        c[0] += r["outcome"] == "SUCCESS"
        c[1] += 1
    return {k: (wins / n, n) for k, (wins, n) in counts.items()}


def plot_lines(ax, rates: dict, series: list[str], labels: dict):
    for i, s in enumerate(series):
        qs = sorted(q for (name, q) in rates if name == s)
        p = np.array([rates[(s, q)][0] for q in qs])
        n = np.array([rates[(s, q)][1] for q in qs])
        # 95% confidence band (normal approximation)
        err = 1.96 * np.sqrt(p * (1 - p) / n)
        color = SERIES_COLORS[i]
        ax.fill_between(qs, p - err, p + err, color=color, alpha=0.12, linewidth=0)
        ax.plot(qs, p, color=color, linewidth=1.6, marker=MARKERS[i], markersize=4,
                markeredgecolor="white", markeredgewidth=0.6, label=labels[s])


def cmd_success(args):
    rows = load(args.csv)
    rates = success_rates(rows, "bot")
    n = max(n for _, n in rates.values())
    fig, axes = new_figure()
    ax = axes[0, 0]
    plot_lines(ax, rates, list(BOTS), BOT_LABELS)
    ax.set_xlabel("flammability q")
    ax.set_ylabel("success rate")
    ax.set_title(args.title or f"Success rate vs. q ({n} trials per point, shaded = 95% CI)",
                 fontsize=10, color=TEXT, loc="left")
    ax.legend(frameon=False, fontsize=8, labelcolor=TEXT)
    save(fig, args.out)


def cmd_outcomes(args):
    rows = load(args.csv)
    counts = defaultdict(lambda: defaultdict(int))
    for r in rows:
        counts[(r["bot"], float(r["q"]))][r["outcome"]] += 1
    fig, axes = new_figure(width=9, height=5.2, ncols=2, nrows=2, sharey=True)
    for ax, bot in zip(axes.flat, BOTS):
        qs = sorted(q for (b, q) in counts if b == bot)
        stacks = []
        for outcome in OUTCOMES:
            stacks.append([counts[(bot, q)][outcome] / sum(counts[(bot, q)].values()) for q in qs])
        ax.stackplot(qs, stacks, colors=SERIES_COLORS, edgecolor="white", linewidth=0.8,
                     labels=[OUTCOME_LABELS[o] for o in OUTCOMES])
        ax.set_title(BOT_LABELS[bot], fontsize=10, color=TEXT, loc="left")
        ax.set_ylim(0, 1)
        ax.set_xlim(min(qs), max(qs))
    for ax in axes[1]:
        ax.set_xlabel("flammability q")
    for ax in axes[:, 0]:
        ax.set_ylabel("fraction of trials")
    fig.suptitle(args.title or "How each trial ends", fontsize=11, color=TEXT)
    # one shared legend on top instead of covering a panel
    fig.legend(*axes[0, 0].get_legend_handles_labels(), loc="outside lower center",
               ncol=len(OUTCOMES), frameon=False, fontsize=8, labelcolor=TEXT)
    save(fig, args.out)


def cmd_head2head(args):
    rows = load(args.csv)
    won = {}  # (q, trial, bot) -> did it succeed
    for r in rows:
        won[(float(r["q"]), r["trial"], r["bot"])] = r["outcome"] == "SUCCESS"
    only = defaultdict(lambda: [0, 0, 0])  # q -> [only bot4, only bot3, total]
    for (q, trial, bot), ok in won.items():
        if bot != "bot4":
            continue
        other = won[(q, trial, "bot3")]
        only[q][0] += ok and not other
        only[q][1] += other and not ok
        only[q][2] += 1
    qs = sorted(only)
    fig, axes = new_figure()
    ax = axes[0, 0]
    width = (qs[1] - qs[0]) * 0.38 if len(qs) > 1 else 0.02
    a = [100 * only[q][0] / only[q][2] for q in qs]
    b = [100 * only[q][1] / only[q][2] for q in qs]
    ax.bar([q - width / 2 for q in qs], a, width, color=SERIES_COLORS[3], label="Bot 4 wins, Bot 3 fails")
    ax.bar([q + width / 2 for q in qs], b, width, color=SERIES_COLORS[2], label="Bot 3 wins, Bot 4 fails")
    ax.set_xlabel("flammability q")
    ax.set_ylabel("% of trials")
    ax.set_title(args.title or "Bot 4 vs. Bot 3 on the exact same ship and fire",
                 fontsize=10, color=TEXT, loc="left")
    ax.legend(frameon=False, fontsize=8, labelcolor=TEXT)
    save(fig, args.out)


def cmd_tuning(args):
    rows = load(args.csv)
    param = rows[0]["param"]
    rates = success_rates(rows, "value")
    values = sorted({r["value"] for r in rows}, key=float)
    if len(values) > len(SERIES_COLORS):
        raise SystemExit(f"plot at most {len(SERIES_COLORS)} values at once so the colors stay distinct")
    fig, axes = new_figure()
    ax = axes[0, 0]
    plot_lines(ax, rates, values, {v: f"{param} = {v}" for v in values})
    ax.set_xlabel("flammability q")
    ax.set_ylabel("Bot 4 success rate")
    ax.set_title(args.title or f"Bot 4 with different {param}", fontsize=10, color=TEXT, loc="left")
    ax.legend(frameon=False, fontsize=8, labelcolor=TEXT)
    save(fig, args.out)


def cmd_riskmap(args):
    # pick a ship + fire, let the real fire burn a bit, then show what Bot 4 predicts
    ship = generate_ship(args.D, seed=args.seed)
    bot, button, fire_start = place_entities(ship, random.Random(args.seed))
    fire = Fire(ship, fire_start, args.q, random.Random(args.seed))
    for _ in range(6):
        fire.step()
    risk = calculate_fire_risk(ship, fire.burning, args.q, horizon=max(args.ahead))

    # one hue, light to dark = low to high risk
    cmap = LinearSegmentedColormap.from_list("risk", ["#ffffff", "#f6c9a8", "#eb6834", "#8a2c08"])
    fig, axes = new_figure(width=4.0 * len(args.ahead) + 0.6, height=4.3, ncols=len(args.ahead))
    for ax, s in zip(axes[0], args.ahead):
        grid = np.full((ship.D, ship.D), np.nan)
        for cell in ship.open_cells:
            grid[cell] = risk[s].get(cell, 0.0)
        ax.imshow(np.where(ship.open, np.nan, 1.0), cmap=LinearSegmentedColormap.from_list(
            "walls", [BLOCKED_COLOR, BLOCKED_COLOR]), interpolation="nearest")
        image = ax.imshow(grid, cmap=cmap, vmin=0, vmax=1, interpolation="nearest")
        ax.plot(bot[1], bot[0], "o", color=BOT_COLOR, markeredgecolor="white", markersize=7)
        ax.plot(button[1], button[0], "s", color=BUTTON_COLOR, markeredgecolor="white", markersize=7)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.grid(False)
        # thin frame so you can see where the ship ends
        for spine in ax.spines.values():
            spine.set_visible(True)
            spine.set_color(MUTED)
            spine.set_linewidth(0.6)
        ax.set_title(f"predicted burn chance {s} steps ahead", fontsize=9, color=TEXT)
    cbar = fig.colorbar(image, ax=list(axes[0]), shrink=0.85)
    cbar.ax.tick_params(labelsize=7, colors=MUTED)
    fig.suptitle(f"Bot 4 risk map (q = {args.q}, blue dot = bot, green square = button)",
                 fontsize=10, color=TEXT)
    save(fig, args.out)


def cmd_examples(args):
    # find trials where one bot failed and another made it, then draw them
    rows = load(args.csv)
    by_setup = defaultdict(dict)
    for r in rows:
        by_setup[(float(r["q"]), int(r["trial"]))][r["bot"]] = r["outcome"]
    wanted = [
        ("bot1", "bot2", "Bot 1 burned, Bot 2 made it"),
        ("bot3", "bot4", "Bot 3 failed, Bot 4 made it"),
        ("bot4", "bot3", "Bot 4 failed, Bot 3 made it"),
    ]
    rng = random.Random(0)
    os.makedirs(args.out, exist_ok=True)
    for loser, winner, caption in wanted:
        matches = [k for k, o in by_setup.items()
                   if args.q_min <= k[0] <= args.q_max
                   and o.get(loser) != "SUCCESS" and o.get(winner) == "SUCCESS"]
        if not matches:
            print(f"no example for: {caption}")
            continue
        q, trial = rng.choice(sorted(matches))
        ship, bot_start, button, fire_start, fire_seed = make_trial(args.D, args.seed, trial)
        for name in (loser, winner):
            result = run_trial(ship, BOTS[name](), bot_start, button, fire_start, q, fire_seed)
            title = f"{BOT_LABELS[name]}: {result.outcome.name.lower()} at t={result.steps} (q={q}, trial {trial})"
            path = os.path.join(args.out, f"{loser}_vs_{winner}_{name}.png")
            save_image(path, ship, result.bot_path[-1], button, result.ignition_time, result.bot_path, title=title)
            print(f"saved {path}")


def save(fig, out):
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    fig.savefig(out, bbox_inches="tight", facecolor="white")
    print(f"saved {out}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("chart", choices=["success", "outcomes", "head2head", "tuning", "riskmap", "examples"])
    parser.add_argument("--csv")
    parser.add_argument("--out", required=True)
    parser.add_argument("--title")
    # riskmap / examples settings (examples must match the D/seed used in experiments.py)
    parser.add_argument("--D", type=int, default=40)
    parser.add_argument("--seed", type=int, default=440)
    parser.add_argument("--q", type=float, default=0.3)
    parser.add_argument("--ahead", type=int, nargs="+", default=[3, 10])
    parser.add_argument("--q-min", type=float, default=0.25)
    parser.add_argument("--q-max", type=float, default=0.5)
    args = parser.parse_args()
    commands = {"success": cmd_success, "outcomes": cmd_outcomes, "head2head": cmd_head2head,
                "tuning": cmd_tuning, "riskmap": cmd_riskmap, "examples": cmd_examples}
    commands[args.chart](args)


if __name__ == "__main__":
    main()
