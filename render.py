"""ASCII and PNG rendering of ships, fire, bot and button."""

from collections.abc import Iterable

import numpy as np
from matplotlib.figure import Figure
from matplotlib.patches import Patch

from ship import Cell, Ship

# colors for the image, picked so fire/bot/button are still easy to tell
# apart if ur colorblind
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
    title: str | None = None,
) -> None:
    """Write a PNG of the ship with fire, bot, button and an optional bot path."""
    D = ship.D
    # turn it into a list since we loop over it twice
    burning = list(burning)
    image = np.empty((D, D, 3))
    image[:] = BLOCKED_COLOR
    image[ship.open] = OPEN_COLOR
    for r, c in burning:
        image[r, c] = FIRE_COLOR

    # using Figure directly instead of pyplot so it doesnt try to open a window
    size = max(4.0, min(12.0, D * 0.16))
    fig = Figure(figsize=(size, size + 0.6), dpi=150)
    ax = fig.add_subplot()
    ax.imshow(image, interpolation="nearest", origin="upper")
    # marker size is in points so scale it off the cell size, otherwise the
    # bot/button dots look tiny on bigger grids
    cell_points = size * 72 * 0.85 / D
    marker_size = max(3.0, 0.95 * cell_points)

    # grid lines help at D=40 but are just noise on really big grids
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
        # hollow circle where the bot started
        ax.plot(cols[0], rows[0], marker="o", markersize=marker_size * 0.8, markerfacecolor="white",
                markeredgecolor=PATH_COLOR, markeredgewidth=1.5, linestyle="none")
        handles.append(Patch(facecolor=PATH_COLOR, alpha=0.75, label="bot path"))
    if button is not None:
        # if the button burned, show it as fire with a green outline so that's obvious
        burned = button in burning
        ax.plot(button[1], button[0], marker="s", markersize=marker_size,
                color=FIRE_COLOR if burned else BUTTON_COLOR,
                markeredgecolor=BUTTON_COLOR if burned else "white",
                markeredgewidth=2 if burned else 1, linestyle="none")
        handles.append(Patch(facecolor=BUTTON_COLOR, label="button"))
    if bot is not None:
        # a bit smaller than the button so you can still see the button under it
        ax.plot(bot[1], bot[0], marker="o", markersize=marker_size * 0.7,
                color=BOT_COLOR, markeredgecolor="white", linestyle="none")
        handles.append(Patch(facecolor=BOT_COLOR, label="bot"))

    if title:
        ax.set_title(title, fontsize=10)
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.01),
              ncol=len(handles), frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(path)
