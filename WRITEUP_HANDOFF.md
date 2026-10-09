# Handoff: CS 440 Project 1 writeup ("This Ship is on Fiiiiire!")

## Your job

Help a two-person group (Person A and Person B) write the PDF writeup for Rutgers CS 440 (01:198:440) Fall 2026, Project 1. The code and experiments are finished. Everything you need is in this document and the `figures/`, `results/` and `tuning/` folders of the repo.

The writeup is graded largely on **communicating ideas and results clearly**. The professor's words: "a significant part of your grade will be based on your ability to communicate your ideas and results."

## Hard rules

1. **Do not invent numbers.** Every number in the writeup must come from this document or from the CSVs in `results/` and `tuning/results/`. If something is missing, leave a visible placeholder like `[TODO]`. Do not estimate or fill it in.
2. **Follow the assignment's rules exactly** (section 2 below). Don't describe the simulation differently from how it works.
3. **Do not include the bonus** (designing a ship layout deliberately). The group chose not to do it. Don't mention it.
4. **Mark who wrote what.** The assignment requires the writeup to "clearly indicate what each person worked on", with shared responsibility for both code and writeup. Use the split in section 9.
5. **Write like students, not marketing.** Plain, direct sentences. No hype words ("robust", "leverage", "cutting-edge", "seamlessly"). Explain *why* things happen, backed by the data.
6. **Each person must review and edit their own sections** so they can explain every claim in their own words if asked. Treat your output as a draft for them.
7. **Bots 1-3 are specified by the assignment.** Describe them exactly as given and don't credit them with extra cleverness.

## 1. Deliverable

A PDF containing "all data, graphs, and discussion and analysis of what you did", plus a section saying what each person worked on. The code is submitted separately.

Required content, from section 7 of the assignment:

1. **Bot 4 design**: what it does, how it uses the available information, and the steps taken to make the code efficient.
2. **Success vs. q**: for each bot, the success rate across many q values in [0, 1]. Repeat enough times for accurate results, identify the "interesting" range of q, get lots of data there, and be clear about the experiments run. For high q the bots should stop differing, because it comes down to whether the bot started closer to the button than the fire did.
3. **Why bots fail**: when each bot fails, why? Was there a better decision available? Support the conclusions. This is partly diagnostic: if Bot 4 underperforms, analyze why.
4. **The ideal bot**: what information it would use and compute, and how. How to balance computation time against decision quality (the fire spreads while you think). When is it smart to just make a break for it?

## 2. The assignment's rules (must be described accurately)

**Ship generation** (D×D grid, neighbors are up/down/left/right only, never diagonal):
1. Start with all cells blocked.
2. Open one random cell in the interior (not on the border).
3. Repeat: pick a random blocked cell with **exactly one** open neighbor and open it, until no such cell exists.
4. Find all dead ends (open cells with exactly one open neighbor). Call the count N0.
5. Repeat: pick a random dead end, pick a random blocked neighbor of it, open it, until the number of dead ends is cut by at least half.

**Fire:** starts in one random open cell. Each timestep, a non-burning open cell catches fire with probability `1 - (1 - q)^K`, where K is its number of currently burning neighbors and q in [0, 1] is the ship's flammability. Fire never enters blocked cells. Burning cells burn forever.

**Task:** at t = 0, the bot, the button and the initial fire are placed on three distinct random open cells. Then at each timestep t = 1, 2, 3, …, in this order:
1. The bot decides where to move (an adjacent open cell, or stay in place).
2. The bot moves.
3. If the bot is on the button, the fire is put out: **success**.
4. Otherwise the fire spreads one step.
5. If the bot and fire ever share a cell: **failure**.

The button check happens *before* the fire spreads.

**Bots:**
- **Bot 1:** plans the shortest path to the button once, avoiding only the initial fire cell, then follows it, ignoring the fire's spread.
- **Bot 2:** every timestep, replans the shortest path avoiding the cells currently on fire, and takes the next step.
- **Bot 3:** every timestep, replans the shortest path avoiding current fire cells *and cells adjacent to fire*, if possible. If no such path exists, it falls back to Bot 2's plan (avoiding only fire cells). It takes the next step.
- **Bot 4:** the group's own design. The assignment forbids it from being "Bot 3 with a wider buffer".

## 3. Implementation details to mention

### Ship (`ship.py`) — Person A
- Follows the rules above. Steps 3 and 5 are separate functions (`_grow_maze`, `_reduce_dead_ends`).
- **Efficiency:**
  - The grid is never rescanned in the loop. An `open_neighbor_count` array is updated incrementally each time a cell opens.
  - The candidate set (step 3) and the dead-end set (step 5) are kept up to date as cells open. Opening one cell in step 5 can remove several dead ends at once, so every affected neighbor is updated.
  - Random selection is O(1): each set is a list plus a cell→index dict, with swap-remove.
- **Measured:**
  - A D = 100 ship generates in about **20 ms**.
  - At D = 40 (average over 50 ships): about **65.5% open**, with dead ends going from about **290** after step 3 to about **144** after step 5.
- Step 3 alone produces a tree (no loops). Step 5 adds loops.
- Open neighbors of every cell are computed once after generation, since the ship never changes.
- Ships are seeded and reproducible.

### Fire (`fire.py`) — Person B
- **Synchronous update:** each step first decides every ignition from the state *before* the step, then applies them all at once. A cell that ignites this step doesn't count toward any other cell's K until the next step.
- **Efficiency:** only cells next to the fire can ignite, so the fire keeps a "frontier" (each non-burning cell with K ≥ 1, mapped to its K) and updates it incrementally. A step costs time proportional to the frontier, not the whole grid.
- **Determinism:** the frontier is processed in sorted order with exactly one random draw per frontier cell. The same (ship, start, q, seed) always gives exactly the same fire, so **every bot faces the identical fire** in a given trial. This makes the bot comparisons paired, which is much more precise than comparing independent runs.
- `clone()` makes an independent copy of the fire for look-ahead without affecting the real fire.

### Simulation (`sim.py`) — Person B
- Implements the timestep order above exactly, including the button check before the fire spreads.
- **Outcomes:**
  - `SUCCESS`
  - `BURNED`: the bot and fire shared a cell
  - `BUTTON_BURNED`: see assumption 3 in section 4
  - `GAVE_UP`: the bot has no path left
  - `TIMEOUT`: the step limit (4·D²) was hit; never happened in our experiments
- An illegal move raises an error instead of being silently fixed.
- Bots see the current fire but never the real fire's random generator, so they can't see the future.

### Bots 1-3 (`bots/`) — Bots 1-2: Person A; Bot 3: Person B
- One shared **BFS** (`bots/pathfinding.py`). Every move costs the same, so breadth-first search finds a shortest path.
- Neighbors are checked in a fixed order (up, down, left, right), so ties between equal-length paths are broken the same way for every bot.
- When there is no path at all, the bot gives up (`GAVE_UP`). This is safe because fire never goes out: once every route to the button is blocked, none will ever reopen, so the trial is already lost.

### Bot 4 (`bots/bot4.py`), "Travis Scott Bot" — risk model: Person A; decision layer: Person B

**Idea:** Bot 3 uses a yes/no rule (next to fire = avoid). Bot 4 instead estimates *how likely* each cell is to be burning *at the time the bot would get there*, using the fire's own probability model. It then picks the path with the best trade-off between length and risk. When being careful is no longer worth it, it switches to **FE!N Mode** and runs the shortest path.

**Risk model (Person A), `calculate_fire_risk`:**
- Predicts `risk[s][cell]`: the chance a cell is burning after s more fire steps, for s = 0 … horizon (default 20). Cells further than the horizon reuse the last prediction.
- `risk[0]` is the current fire (1.0 for burning cells).
- Each step applies the assignment's rule, treating neighbors as "maybe burning": a cell's chance of catching is `1 − ∏ over neighbors (1 − q · p_neighbor)`. When every neighbor is certainly burning or certainly not, this is **exactly** `1 − (1 − q)^K`. That's tested.
- This is an approximation: it treats cells as independent and ignores correlations between them. Say so as a limitation.
- Only cells next to cells that already have risk are updated each step, so the cost grows with the fire region, not the whole grid.

**Danger on arrival:**
- If the bot reaches a cell on its m-th move, it dies if that cell is burning after m fire steps. That covers stepping into fire and the fire reaching the bot on that step.
- The **button** only has to survive m − 1 fire steps, because the button check happens before the fire spreads.
- A path's success chance is the product of `(1 − danger)` over its cells. Because the button is the last cell, the chance the button burns before the bot arrives is included automatically. **That's why long detours are penalized: they give the button more time to burn.**

**Risk-weighted path, `calculate_risk_weighted_path`:**
- Dijkstra with a heap. Entering a cell costs `1 + risk_weight · (−log(1 − danger))`, with danger capped at 0.999 so log never sees 0.
- Summing `−log(1 − danger)` along a path equals `−log(chance of surviving the path)`, so Dijkstra minimizes **path length + risk_weight × path risk**.
- It tracks the number of moves to each cell, because danger depends on *when* the bot arrives.
- Never enters burning cells.
- Limitation: costs depend on arrival time, so keeping only the cheapest label per cell makes this a heuristic, not a guaranteed optimum.

**FE!N trigger (Person B), `should_enter_fein_mode`.** FE!N Mode turns on when:
- there is no careful path, **or**
- the careful path is a real detour (longer than the shortest path that avoids burning cells) **and** either:
  - its estimated success chance beats the shortest path's by less than `fein_margin` (default 0.02), or
  - it's more than `max_detour_ratio` (default 2.0) times as long as the shortest path.

If the careful path is no longer than the shortest path, being careful costs nothing, so the bot stays in Risk-Aware Mode. Once FE!N Mode turns on, it stays on.

**FE!N Mode:** follow the shortest path that avoids burning cells (the same BFS Bot 2 uses), recomputed every step.

**Settings** are all in `Bot4Config`, changeable without touching the algorithm:

| Setting | Default |
|---|---|
| `risk_weight` | 30 |
| `horizon` | 20 |
| `fein_margin` | 0.02 |
| `max_detour_ratio` | 2.0 |

`risk_weight` started at 3. At that value a 33% chance of death was worth only about one extra step, so the bot never detoured; that's why it was raised.

**Logging:** each step records the timestep, mode (`RISK_AWARE` or `FEIN`), the chosen path's length and its risk score (estimated chance of failing), plus when FE!N Mode turned on.

**Bug found and fixed (worth including in Q1 or Q3; it's what the assignment means by "analyze why").** The first FE!N trigger fired whenever the careful path wasn't at least 0.02 safer. When the fire starts far away, the careful and shortest paths are identical (0 gain), so FE!N Mode turned on at t = 1 and stayed on. In the first full experiment, **28,041 of 32,000 Bot 4 trials (88%)** entered FE!N at t = 1, so Bot 4 mostly behaved exactly like Bot 2. The fix: only consider FE!N when the careful path is an actual detour. After the fix, FE!N triggers in **4,242 of 32,000 trials (13%)**, and Bot 4's paired advantage over Bot 3 grew. **All results below are from the fixed version.**

**Efficiency / cost** (D = 40, q = 0.3, 200 trials, one core):

| Bot | Per trial | Per step |
|---|---|---|
| Bot 1 | 3.6 ms | 0.12 ms |
| Bot 2 | 5.8 ms | 0.19 ms |
| Bot 3 | 6.2 ms | 0.20 ms |
| Bot 4 | 53.7 ms | 1.73 ms |

Bot 4 costs about 9× Bot 3 per step because each step runs the risk prediction plus Dijkstra plus BFS. This is a direct example for Q4's "computation vs. intelligence" trade-off.

## 4. Assumptions (state these; the assignment leaves them open)

1. Only the first opened cell must be in the interior. Border cells can open later.
2. "Cut by at least half" means stop once `2 × current dead ends ≤ N0`.
3. The button is an ordinary open cell and can burn. If it does, the trial ends as `BUTTON_BURNED`, because success is no longer possible.
4. The bot may stay in place (the assignment lists "stay in place" as an action).
5. The bot knows q.
6. If one fire step burns both the bot's cell and the button, it counts as `BURNED`.
7. A bot with no path to the button gives up. Fire never goes out, so this can't cost a success.
8. Bot 3's buffer also applies to the button. If the button is next to fire, Bot 3 uses Bot 2's plan.
9. BFS ties are broken in a fixed neighbor order for all bots.
10. Bot 4's independence approximation and permanent FE!N Mode (above).

## 5. Experimental setup (Q2 must state this clearly)

- **Ship size:** D = 40 for all experiments. The assignment says to aim as large as feasible. Generation scales easily (D = 100 in about 20 ms); D = 40 was chosen to afford 1,000 trials per q with Bot 4 at about 54 ms per trial. Mention this trade-off honestly. *(If the group reruns at a larger D, update this.)*
- **Paired design:** trial i uses the same ship, the same bot/button/fire placement and the same fire random seed for all four bots and for every q. Base seed 440. The bots therefore face identical fires, and differences between them come from their decisions, not luck.
- **Coarse sweep** (`results/coarse.csv`): q = 0.00, 0.05, …, 1.00 (21 values), 200 trials each, 4 bots, so 16,800 runs. Purpose: find the interesting range.
- **Dense sweep** (`results/dense.csv`): q = 0.04, 0.06, …, 0.66 (32 values), 1,000 trials each, 4 bots, so 128,000 runs. Purpose: precise results where the bots actually differ.
- **Error bars:** 95% confidence interval using the normal approximation, `±1.96·√(p(1−p)/n)`. At n = 1,000 and p near 0.8 that's about ±2.5 percentage points.
- **Hardware:** runs were parallelized across 8 CPU cores with Python `multiprocessing`. The coarse sweep took about 40 s; the dense sweep took about 5–7 min.
- **Reproducible:** every command is in `TASKS.md`.

## 6. Results (use these exact numbers)

### Success rate, coarse sweep (200 trials per q)

| q | Bot 1 | Bot 2 | Bot 3 | Bot 4 |
|---|---|---|---|---|
| 0.00 | 1.000 | 1.000 | 1.000 | 1.000 |
| 0.05 | 0.965 | 0.985 | 0.995 | 0.995 |
| 0.10 | 0.935 | 0.965 | 0.955 | 0.965 |
| 0.15 | 0.900 | 0.940 | 0.935 | 0.935 |
| 0.20 | 0.880 | 0.900 | 0.910 | 0.915 |
| 0.25 | 0.860 | 0.885 | 0.880 | 0.880 |
| 0.30 | 0.815 | 0.845 | 0.850 | 0.855 |
| 0.35 | 0.790 | 0.810 | 0.810 | 0.830 |
| 0.40 | 0.775 | 0.780 | 0.780 | 0.820 |
| 0.45 | 0.730 | 0.740 | 0.760 | 0.785 |
| 0.50 | 0.710 | 0.715 | 0.730 | 0.720 |
| 0.55 | 0.665 | 0.675 | 0.695 | 0.690 |
| 0.60 | 0.640 | 0.645 | 0.665 | 0.655 |
| 0.65 | 0.615 | 0.615 | 0.625 | 0.625 |
| 0.70 | 0.600 | 0.600 | 0.605 | 0.610 |
| 0.75 | 0.585 | 0.585 | 0.585 | 0.590 |
| 0.80 | 0.565 | 0.565 | 0.565 | 0.560 |
| 0.85 | 0.530 | 0.530 | 0.530 | 0.525 |
| 0.90 | 0.520 | 0.520 | 0.520 | 0.520 |
| 0.95 | 0.490 | 0.490 | 0.490 | 0.490 |
| 1.00 | 0.485 | 0.485 | 0.485 | 0.485 |

**Interesting range:** roughly q = 0.05 to 0.65. Above about 0.7 all four bots are essentially identical.

### Success rate, dense sweep (1,000 trials per q)

| q | Bot 1 | Bot 2 | Bot 3 | Bot 4 |
|---|---|---|---|---|
| 0.04 | 0.974 | 0.992 | 0.993 | 0.993 |
| 0.06 | 0.966 | 0.988 | 0.988 | 0.990 |
| 0.08 | 0.952 | 0.983 | 0.981 | 0.986 |
| 0.10 | 0.943 | 0.971 | 0.969 | 0.974 |
| 0.12 | 0.928 | 0.962 | 0.962 | 0.967 |
| 0.14 | 0.927 | 0.960 | 0.958 | 0.963 |
| 0.16 | 0.916 | 0.942 | 0.946 | 0.949 |
| 0.18 | 0.909 | 0.937 | 0.940 | 0.946 |
| 0.20 | 0.895 | 0.922 | 0.932 | 0.934 |
| 0.22 | 0.882 | 0.912 | 0.917 | 0.922 |
| 0.24 | 0.865 | 0.897 | 0.901 | 0.906 |
| 0.26 | 0.852 | 0.883 | 0.886 | 0.894 |
| 0.28 | 0.848 | 0.878 | 0.884 | 0.893 |
| 0.30 | 0.837 | 0.861 | 0.869 | 0.879 |
| 0.32 | 0.824 | 0.848 | 0.852 | 0.862 |
| 0.34 | 0.821 | 0.846 | 0.852 | 0.861 |
| 0.36 | 0.809 | 0.832 | 0.837 | 0.849 |
| 0.38 | 0.806 | 0.822 | 0.827 | 0.834 |
| 0.40 | 0.786 | 0.799 | 0.803 | 0.821 |
| 0.42 | 0.774 | 0.789 | 0.792 | 0.807 |
| 0.44 | 0.763 | 0.779 | 0.782 | 0.794 |
| 0.46 | 0.746 | 0.761 | 0.763 | 0.772 |
| 0.48 | 0.738 | 0.753 | 0.755 | 0.763 |
| 0.50 | 0.727 | 0.734 | 0.737 | 0.737 |
| 0.52 | 0.705 | 0.713 | 0.720 | 0.727 |
| 0.54 | 0.695 | 0.701 | 0.702 | 0.707 |
| 0.56 | 0.695 | 0.701 | 0.705 | 0.706 |
| 0.58 | 0.679 | 0.684 | 0.691 | 0.691 |
| 0.60 | 0.663 | 0.667 | 0.670 | 0.669 |
| 0.62 | 0.667 | 0.670 | 0.666 | 0.673 |
| 0.64 | 0.648 | 0.651 | 0.655 | 0.657 |
| 0.66 | 0.637 | 0.638 | 0.638 | 0.638 |

Bot 4 is at or above every other bot at almost every q in the dense range. The largest gains are around q = 0.3–0.5. For example, at q = 0.40: Bot 4 0.821, Bot 3 0.803, Bot 2 0.799, Bot 1 0.786.

### How trials end (dense sweep, all 32,000 trials per bot)

| Bot | Success | Bot burned | Button burned | Gave up (cut off) |
|---|---|---|---|---|
| Bot 1 | 80.87% | 12.21% | 6.73% | 0.20% |
| Bot 2 | 82.74% | 2.54% | 6.93% | 7.80% |
| Bot 3 | 83.04% | 0.74% | 7.58% | 8.63% |
| Bot 4 | 83.64% | 1.53% | 7.21% | 7.63% |

Coarse sweep, all 4,200 trials per bot:

| Bot | Success | Bot burned | Button burned | Gave up |
|---|---|---|---|---|
| Bot 1 | 71.69% | 16.55% | 11.76% | 0% |
| Bot 2 | 72.74% | 4.24% | 9.74% | 13.29% |
| Bot 3 | 73.19% | 1.67% | 10.36% | 14.79% |
| Bot 4 | 73.57% | 3.00% | 10.48% | 12.95% |

Bot 1's 0.20% "gave up" in the dense sweep are trials where the only route to the button went through the initial fire cell.

### Paired head-to-head (dense sweep, same 32,000 setups)

"X wins" = X succeeded and Y failed on the identical ship and fire.

| Comparison | X wins | Y wins |
|---|---|---|
| Bot 4 vs. Bot 3 | **357** | 166 |
| Bot 4 vs. Bot 2 | **427** | 139 |
| Bot 4 vs. Bot 1 | **1,005** | 118 |
| Bot 3 vs. Bot 2 | **236** | 139 |
| Bot 3 vs. Bot 1 | **803** | 107 |
| Bot 2 vs. Bot 1 | **599** | **0** |

- These discordant-pair counts are the strongest evidence. With McNemar's test (χ² with continuity correction = (|b − c| − 1)² / (b + c)):
  - Bot 4 vs. Bot 3: χ² ≈ 69
  - Bot 4 vs. Bot 2: χ² ≈ 146
  - Bot 3 vs. Bot 2: χ² ≈ 25
  - All have p < 0.001.
- Individual points on the success curves overlap within their CIs, but the paired comparison shows the differences are real.
- **Bot 2 never failed where Bot 1 succeeded** (0 of 32,000).

### Key observation for Q2/Q3 (verified in the data)

- In **every** failed trial, for every bot, in both sweeps, the fire started at least as close to the button as the bot. Distance is the shortest path through open cells, ignoring fire.
- No bot ever failed when it started strictly closer to the button than the fire. That makes sense: the fire spreads at most one cell per step, the bot moves one cell per step, and the button check happens before the fire spreads.
- The fire started at least as close in **2,163 of 4,200** coarse setups (51.5%). At q = 1 every bot's success rate is **0.485 = 1 − 2163/4200**, exactly the share of setups where the bot started strictly closer. This confirms the assignment's note that at high q "the problem really reduces to whether or not the bot started closer to the button than the fire".
- In the dense sweep it was 16,224 of 32,000 (50.7%).

### Bot 4 tuning (`tuning/results/tune_*.csv`, `tuning/figures/tune_*.png`)

**Setup:**
- One setting is varied at a time; the other three stay at their defaults.
- q = 0.1, 0.2, …, 0.6, with 500 paired setups per q (the same trials 0–499 as the main sweeps).
- That's 3,000 Bot 4 runs per value.

| Owner | Setting | Values tried |
|---|---|---|
| Person A | `risk_weight` | 5, 15, **30**, 60 |
| Person A | `horizon` | 5, 10, **20**, 40 |
| Person B | `fein_margin` | 0, **0.02**, 0.05, 0.1 |
| Person B | `max_detour_ratio` | 1.5, **2**, 3, 5 |

Defaults are in bold.

**Overall success rate per value** (all 3,000 runs):

| Setting | Values → success |
|---|---|
| `risk_weight` | 5 → 0.8407, 15 → 0.8397, **30 → 0.8400**, 60 → 0.8387 |
| `horizon` | 5 → 0.8413, 10 → 0.8417, **20 → 0.8400**, 40 → 0.8383 |
| `fein_margin` | 0 → 0.8420, **0.02 → 0.8400**, 0.05 → 0.8397, 0.1 → 0.8397 |
| `max_detour_ratio` | 1.5 → 0.8403, **2 → 0.8400**, 3 → 0.8383, 5 → 0.8377 |

**Paired comparison against the default** (same setups; "a vs b" = trials only the new value won vs. trials only the default won):

| Setting | Value | a vs b | χ² |
|---|---|---|---|
| `risk_weight` | 5 | 10 vs 8 | 0.1 |
| `risk_weight` | 15 | 2 vs 3 | 0.0 |
| `risk_weight` | 60 | 0 vs 4 | 2.2 |
| `horizon` | 5 | 23 vs 19 | 0.2 |
| `horizon` | 10 | 18 vs 13 | 0.5 |
| `horizon` | 40 | 13 vs 18 | 0.5 |
| `fein_margin` | 0 | 7 vs 1 | 3.1 |
| `fein_margin` | 0.05 | 0 vs 1 | 0.0 |
| `fein_margin` | 0.1 | 0 vs 1 | 0.0 |
| `max_detour_ratio` | 1.5 | 5 vs 4 | 0.0 |
| `max_detour_ratio` | 3 | 0 vs 5 | 3.2 |
| `max_detour_ratio` | 5 | 0 vs 7 | 5.1 (p ≈ 0.02) |

**What this means (state these conclusions; don't overclaim):**
- **Bot 4 is insensitive to all four settings in these ranges.**
  - Every value lands within 0.4 percentage points of the default overall.
  - Changing a setting changes the outcome in at most about 1.4% of trials (42 of 3,000 at most).
- Only one comparison is borderline significant: a *looser* detour limit (`max_detour_ratio` = 5) is slightly worse than 2. That fits the idea that long detours give the button time to burn.
- `fein_margin` = 0 (go FE!N only when careful is no better at all) is slightly better than 0.02, but not significantly (p ≈ 0.08).
- **Interpretation:** most of Bot 4's advantage comes from the *structure* of the algorithm, not the exact numbers:
  - risk predicted at the time the bot would arrive
  - the button's own risk included
  - a switch to running when detours stop paying off
- Most trials are decided by geometry: whether the bot starts closer to the button than the fire (see the key observation above). Only a small share of trials has a real careful-vs.-rush decision for these settings to affect.
- A small trend worth one sentence, with the caveat that it's small: a longer `horizon` raised "bot burned" (1.33% at horizon 5 → 2.17% at 40) and lowered "button burned" (7.13% → 6.57%).
- **The group kept the defaults** (no setting was clearly better). Optionally, mention `fein_margin = 0` and `max_detour_ratio = 1.5–2` as the slightly better region.

## 7. Figures (in `figures/`, tuning charts in `tuning/figures/`)

| File | What it shows | Use in |
|---|---|---|
| `success_full.png` | Success vs. q, full range 0–1, 200 trials per point, shaded 95% CI | Q2 |
| `success_dense.png` | Success vs. q, 0.04–0.66, 1,000 trials per point, shaded 95% CI | Q2 (main figure) |
| `outcomes.png` | One panel per bot: fraction of trials ending in success / bot burned / button burned / gave up, vs. q (coarse sweep) | Q3 |
| `bot4_vs_bot3.png` | Per q: % of trials where Bot 4 succeeded and Bot 3 failed, and vice versa | Q1 / Q3 |
| `risk_map.png` | Bot 4's predicted burn chance 3 and 10 steps ahead on an example ship (q = 0.3, after 6 fire steps), with the bot and button marked | Q1 |
| `examples/bot1_vs_bot2_*.png` | Same setup: Bot 1 failed, Bot 2 succeeded | Q3 |
| `examples/bot3_vs_bot4_*.png` | Same setup: Bot 3 failed, Bot 4 succeeded | Q3 |
| `examples/bot4_vs_bot3_*.png` | Same setup: Bot 4 failed, Bot 3 succeeded | Q3 (shows Bot 4's weakness honestly) |
| `tuning/figures/tune_risk_weight.png`, `tuning/figures/tune_horizon.png` | Bot 4 success vs. q for each value (Person A's settings); lines nearly overlap | Q1 |
| `tuning/figures/tune_fein_margin.png`, `tuning/figures/tune_max_detour_ratio.png` | Same, for Person B's settings | Q1 |

Each example image's title gives the bot, outcome, time, q and trial number. In those images:
- orange = fire
- blue line = path
- hollow circle = start
- filled blue dot = final position
- green square = button (a burned button is drawn as an orange square with a green outline)

Look at each image before describing it, and describe only what it actually shows.

Charts use a colorblind-checked palette with distinct marker shapes, so they also work in grayscale. Number every figure and refer to it in the text.

## 8. What each section should say

### Introduction / setup (A: ship; B: fire + simulation)
A short description of the ship generation, fire and timestep rules (section 2), the efficiency points from section 3, and the assumptions (section 4).

### Q1: Bot 4 design (A: risk model, Dijkstra, efficiency; B: FE!N Mode, trigger, settings, bug fix, tuning)
Must cover:
- How it differs from Bot 3: probabilities instead of a yes/no buffer.
- The risk prediction and why it matches the fire rule for one step.
- Danger depends on arrival time, and the button gets one step less.
- The −log trick, and why that makes Dijkstra minimize "length + weighted risk".
- Why detours are penalized automatically (the button can burn).
- The FE!N trigger and its settings.
- The bug and the fix.
- Efficiency (frontier-limited prediction, heap Dijkstra, the cost table).
- Limitations (independence approximation, heuristic Dijkstra).
- `risk_map.png`.

### Q2: Success vs. q (A)
Must cover:
- The experimental setup (section 5).
- Both success figures.
- The interesting range and why it was chosen (coarse sweep first).
- Bot 1 is clearly worst at low and moderate q.
- Bots 2, 3 and 4 are close on the curves, but the paired results separate them.
- All bots converge above about q = 0.7, matching the bot-vs-fire distance observation.
- Error bars and the number of trials.

### Q3: Why bots fail (A: Bots 1 and 2; B: Bots 3 and 4)
- **Bot 1:** mostly *walks into fire* (12.2% burned in the dense sweep), because it never replans. A better decision usually existed: Bot 2 rescued 599 of Bot 1's failures, and Bot 1 never beat Bot 2.
- **Bot 2:**
  - Mostly gets *cut off* (7.8% gave up) or the *button burns* (6.9%).
  - It still occasionally burns (2.5%) because it happily walks right next to the fire, and the cell it steps into ignites on that same step.
- **Bot 3:**
  - Lowest "bot burned" rate (0.74%), thanks to the buffer.
  - But the most "gave up" (8.6%) and "button burned" (7.6%). Its buffer causes detours or hesitation, which give the fire time to cut it off or reach the button.
  - See `examples/bot3_vs_bot4_bot3.png`.
- **Bot 4:**
  - Fewer cut-offs (7.6%) and button burns (7.2%) than Bot 3.
  - But about twice Bot 3's "bot burned" rate (1.53% vs. 0.74%). It knowingly accepts some risk when the numbers say rushing is better, and sometimes loses that bet.
  - See `examples/bot4_vs_bot3_*.png`.
  - Also discuss the FE!N bug as a diagnostic finding.
- **All bots:**
  - Every failure had the fire starting at least as close to the button.
  - Many failures were likely unavoidable for *any* strategy. Be careful: we did not measure exactly how many were avoidable. Say "likely" or "some" unless backed by data.

### Q4: The ideal bot (A: what information it uses and computes; B: compute vs. intelligence, when to make a break for it)
This is speculative discussion; no new numbers. Points the group can build on:
- Simulating many possible fires with the fire's `clone()` to estimate success chances directly (Monte Carlo look-ahead), instead of Bot 4's independence approximation.
- Using the knowledge that a bot strictly closer than the fire can always win by running.
- Planning over space and time together.
- Bot 4 costs about 9× Bot 3 per step for a few points of improvement. In real time, slow thinking lets the fire spread.
- "Make a break for it" when the bot is clearly closer than the fire, when every detour gives the button time to burn, or when predictions far ahead are unreliable. FE!N Mode is an example of that rule.

### Who did what (both)
Use section 9.

## 9. Who did what (fill in names)

| Area | Person A | Person B |
|---|---|---|
| Infrastructure | `ship.py`, `render.py`, `demo.py` | `fire.py`, `sim.py` |
| Bots 1-3 | BFS pathfinding, Bot 1, Bot 2 | Bot 3, bot tests |
| Bot 4 | Risk model (`calculate_fire_risk`, danger on arrival, path success, risk-weighted Dijkstra), tuning `risk_weight` and `horizon` | Decision layer (FE!N trigger, mode switching, `Bot4Config`, logging), FE!N bug fix, tuning `fein_margin` and `max_detour_ratio` |
| Charts | Success vs. q, risk map, own tuning chart | Outcome breakdown, Bot 4 vs. Bot 3, example failures, own tuning chart |
| Writeup | Ship setup, Q1 risk model, Q2, Q3 Bots 1-2, Q4 information | Fire/sim setup, Q1 FE!N, Q3 Bots 3-4, Q4 compute trade-off |
| Final pass | Assembles the PDF | Proofreads and checks every claim against the data |

## 10. Don't

- Don't claim Bot 4 is "optimal" or "always better". It loses 166 paired trials to Bot 3.
- Don't claim tiny single-q differences between Bots 2, 3 and 4 are meaningful on their own. Point to the paired counts instead.
- Don't describe the fire as spreading to diagonal cells, or as asynchronous.
- Don't say the bot moves after the fire spreads. The bot moves first.
- Don't mention the bonus.
- Don't present `TIMEOUT` as something that happened; it never did.
- Don't paste large code listings. Short snippets or pseudocode for Bot 4 are fine.
