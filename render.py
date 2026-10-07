"""ASCII and PNG rendering of ships, fire, bot and button."""

from collections.abc import Iterable

import numpy as np
from matplotlib.figure import Figure
from matplotlib.patches import Patch

from ship import Cell, Ship

# RGB colors for the image. Fire and bot/button use hues that stay distinct
# under the common forms of color blindness.
BLOCKED_COLOR = (0.20, 0.22, 0.25)
OPEN_COLOR = (1.0, 1.0, 1.0)
FIRE_COLOR = (0.93, 0.42, 0.13)
BOT_COLOR = (0.13, 0.40, 0.80)
BUTTON_COLOR = (0.10, 0.62, 0.35)
PATH_COLOR = (0.13, 0.40, 0.80)


def render_ascii(
    ship: Ship,
    bot: Cell | None = None,
    button: Cell | None = None,
    burning: Iterable[Cell] = (),
) -> str:
    """Return the ship as text: '#' blocked, '.' open, '*' fire, 'B' bot, 'X' button.

    If two things share a cell, the bot wins over the button, which wins over fire.
    """
    rows = [["." if ship.open[r, c] else "#" for c in range(ship.D)] for r in range(ship.D)]
    for r, c in burning:
        rows[r][c] = "*"
    if button is not None:
        rows[button[0]][button[1]] = "X"
    if bot is not None:
        rows[bot[0]][bot[1]] = "B"
    return "\n".join("".join(row) for row in rows)


def save_image(
    path: str,
    ship: Ship,
    bot: Cell | None = None,
    button: Cell | None = None,
    burning: Iterable[Cell] = (),
    bot_path: list[Cell] | None = None,
) -> None:
    """Write a PNG of the ship with fire, bot, button and an optional bot path."""
    D = ship.D
    # burning may be a one-shot iterable; it is read twice below.
    burning = list(burning)
    image = np.empty((D, D, 3))
    image[:] = BLOCKED_COLOR
    image[ship.open] = OPEN_COLOR
    for r, c in burning:
        image[r, c] = FIRE_COLOR

    # Uses Figure directly instead of pyplot so no global matplotlib state or
    # GUI backend is involved.
    size = max(4.0, min(12.0, D * 0.16))
    fig = Figure(figsize=(size, size + 0.6), dpi=150)
    ax = fig.add_subplot()
    ax.imshow(image, interpolation="nearest", origin="upper")
    # Markers are sized in points, so derive them from the on-page cell size
    # to keep them close to a full cell at any D.
    cell_points = size * 72 * 0.85 / D
    marker_size = max(3.0, 0.95 * cell_points)

    # Thin cell grid lines help when reading paths at D around 40; they get
    # too dense to be useful on much larger grids.
    if D <= 60:
        ax.set_xticks(np.arange(-0.5, D, 1), minor=True)
        ax.set_yticks(np.arange(-0.5, D, 1), minor=True)
        ax.grid(which="minor", color=(0.85, 0.86, 0.88), linewidth=0.4)
        ax.tick_params(which="minor", length=0)
    ax.set_xticks([])
    ax.set_yticks([])

    handles = [
        Patch(facecolor=BLOCKED_COLOR, label="blocked"),
        Patch(facecolor=OPEN_COLOR, edgecolor=(0.7, 0.7, 0.7), label="open"),
    ]
    if burning:
        handles.append(Patch(facecolor=FIRE_COLOR, label="fire"))

    if bot_path:
        rows = [r for r, _ in bot_path]
        cols = [c for _, c in bot_path]
        ax.plot(cols, rows, color=PATH_COLOR, linewidth=1.8, alpha=0.75, label="bot path")
        handles.append(Patch(facecolor=PATH_COLOR, alpha=0.75, label="bot path"))
    if button is not None:
        ax.plot(button[1], button[0], marker="s", markersize=marker_size,
                color=BUTTON_COLOR, markeredgecolor="white", linestyle="none")
        handles.append(Patch(facecolor=BUTTON_COLOR, label="button"))
    if bot is not None:
        ax.plot(bot[1], bot[0], marker="o", markersize=marker_size,
                color=BOT_COLOR, markeredgecolor="white", linestyle="none")
        handles.append(Patch(facecolor=BOT_COLOR, label="bot"))

    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.01),
              ncol=len(handles), frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(path)
