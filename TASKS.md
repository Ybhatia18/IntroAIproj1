# Project 1 task split

Two people: **Person A** and **Person B** (put your names here).

"Owns" means: you can explain every line to a grader, you keep its tests passing, you make any changes it needs, and you write the writeup part about it. Both of us should still be able to explain all of Bot 4 at a high level.

## 1. Infrastructure (low priority, already built)

| Person A | Person B |
|---|---|
| `ship.py` + `tests/test_ship.py` | `fire.py` + `tests/test_fire.py` |
| `render.py`, `demo.py` | `sim.py` + `tests/test_sim.py` |

## 2. Bots 1-3 (low priority, already built)

| Person A | Person B |
|---|---|
| `bots/pathfinding.py` (BFS) | `bots/bot3.py` |
| `bots/bot1.py`, `bots/bot2.py` | `tests/test_bots.py` |

## 3. Bot 4 (high priority, split down the middle)

Bot 4 has two halves: a **risk model** (how dangerous is each cell and path) and a **decision layer** (when to be careful vs. go FE!N).

| Person A: risk model | Person B: decision layer |
|---|---|
| `calculate_fire_risk`: the multi-step fire prediction | `should_enter_fein_mode`: the FE!N trigger |
| `risk_at`, `danger_on_arrival`, `path_success_chance` | `bot4_next_move`: mode switching, FE!N being permanent |
| `calculate_risk_weighted_path`: Dijkstra + the `-log(1 - danger)` cost | `calculate_shortest_safe_path`, `Bot4Config`, `StepLog`, `bot4_summary` |
| Tests: risk matches the fire rule, risk only grows, detour test | Tests: FE!N test, never steps into fire, logging |
| **Tuning:** `risk_weight` and `horizon` | **Tuning:** `fein_margin` and `max_detour_ratio` |

## 4. Experiments and charts

| Person A | Person B |
|---|---|
| Pick the q values: coarse sweep, then the dense "interesting" range | Failure breakdown chart (burned / button burned / gave up, per bot) |
| **Main chart:** success rate vs. q for all 4 bots, with error bars | Bot 4 vs. Bot 3 head-to-head chart (trials one wins and the other loses) |
| Tuning chart for `risk_weight` / `horizon` | Tuning chart for `fein_margin` / `max_detour_ratio` |
| Bot 4 risk map picture (for the Bot 4 section) | Example failure pictures (ship + bot path) for question 3 |

## 5. Writeup (PDF)

| Section | Person A | Person B |
|---|---|---|
| Setup: how the ship, fire and sim work + our assumptions (`NOTES.md`) | Ship generation | Fire + simulation rules |
| **Q1: Bot 4 design** | Risk model, Dijkstra cost, efficiency | FE!N Mode, trigger, tuning results |
| **Q2: Success vs. q** | All of it: the graph, number of trials, the interesting range | |
| **Q3: Why bots fail** | Bots 1 and 2 | Bots 3 and 4 (uses the failure pictures + head-to-head chart) |
| **Q4: Ideal bot** | What info it uses and computes (e.g. simulating fires with `fork_fire`) | Compute vs. intelligence; when to just make a break for it |
| Who-did-what section | Both | Both |
| Final pass | Assembles the PDF | Proofreads, checks every claim matches the data |

Q2 is one big section for A, and B has the larger share of Q3 and Q4, so the writing evens out.

## Order

1. Everyone reads their owned code until they can explain it.
2. Run the experiments (`experiments.py`), then the charts (`plots.py`).
3. Tune Bot 4 (each person tunes their own two settings).
4. Write your sections, then swap and review each other's.

## Commands

All results are reproducible: trial `i` is the same ship, placement and fire at every q and for every bot (base seed 440, D = 40).

```bash
# data
python experiments.py sweep --trials 200 --out results/coarse.csv
python experiments.py sweep --q-start 0.04 --q-stop 0.66 --q-step 0.02 --trials 1000 --out results/dense.csv
python experiments.py tune --param risk_weight --values 5 15 30 60 --q-start 0.1 --q-stop 0.6 --q-step 0.1 --trials 500 --out tuning/results/tune_risk_weight.csv
python experiments.py tune --param horizon --values 5 10 20 40 --q-start 0.1 --q-stop 0.6 --q-step 0.1 --trials 500 --out tuning/results/tune_horizon.csv
python experiments.py tune --param fein_margin --values 0 0.02 0.05 0.1 --q-start 0.1 --q-stop 0.6 --q-step 0.1 --trials 500 --out tuning/results/tune_fein_margin.csv
python experiments.py tune --param max_detour_ratio --values 1.5 2 3 5 --q-start 0.1 --q-stop 0.6 --q-step 0.1 --trials 500 --out tuning/results/tune_max_detour_ratio.csv

# charts
python plots.py success --csv results/coarse.csv --out figures/success_full.png
python plots.py success --csv results/dense.csv --out figures/success_dense.png
python plots.py outcomes --csv results/coarse.csv --out figures/outcomes.png
python plots.py head2head --csv results/dense.csv --out figures/bot4_vs_bot3.png
python plots.py tuning --csv tuning/results/tune_risk_weight.csv --out tuning/figures/tune_risk_weight.png   # same for the other 3
python plots.py riskmap --out figures/risk_map.png
python plots.py examples --csv results/dense.csv --out figures/examples
```
