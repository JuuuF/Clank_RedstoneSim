"""Constants and small helpers of the document's modules (timeline rows, the floor size,
placement variations)."""

from __future__ import annotations

from collections.abc import Callable

from redsim.sim.engine import Action
from redsim.world.block import BlockState

FLOOR_HALF_SIZE = 16


#: Timeline rows for recorded edits (color-coded in the UI).
EDIT_ROWS = ("build", "remove", "edit", "interact", "power")


def edit_row(action: Action) -> str:
    """Which timeline row an edit belongs to: placing blocks, removing them, changing
    placed blocks (inspector, selections), or interacting like a player."""
    kind = action.kind
    if kind == "power_pulse":
        return "power"
    if kind in (
        "use",
        "lectern_page",
        "projectile_hit",
        "lightning_strike",
        "container_item",
        "sign_text",
    ):
        return "interact"
    if kind == "break":
        return "remove"
    if kind in ("fill", "setblock", "set_block"):
        if (action.state or "").split("[")[0] in ("minecraft:air", "air"):
            return "remove"
        return "build" if kind == "fill" or action.label.startswith("place") else "edit"
    if kind in ("place", "clone", "stack_region"):
        return "build"
    if kind == "transform_regions" and (action.payload or {}).get("copy"):
        return "build"
    return "edit"


#: An editor choice applied to a block state before it is placed (turned, mirrored, …).
Vary = Callable[[BlockState], BlockState] | None
