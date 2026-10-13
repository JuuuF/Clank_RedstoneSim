"""Constants and small helpers shared by the main window's modules (file filter, run-loop
and streaming timings, history labels)."""

from __future__ import annotations

from redsim.ui.names import block_name
from redsim.world import blocks

FILE_FILTER = "Redstone simulator worlds (*.redsim.json *.json)"


#: Run loop: timer period, the longest it may simulate in one go (keeps the UI responsive),
#: and how often the side panels refresh while running.
PLAY_INTERVAL_MS = 5


RUN_BUDGET_SECONDS = 0.035


PANEL_REFRESH_SECONDS = 0.1


TIMELINE_EXTRA = 40  # pixels beyond the timeline's lines (room for a few more)


#: Running at a set speed: the longest one call may simulate before a frame is drawn
#: (a heavy tick then takes several calls).
STEP_BUDGET_SECONDS = 0.008


#: Streaming an opened Minecraft world: how often, and the longest one call may read.
STREAM_INTERVAL_MS = 60


STREAM_BUDGET_S = 0.025


def _plain_cube(block_id: str) -> bool:
    """A foreign block that behaves like any full cube (quartz, bricks, …): nothing to warn
    about."""
    from redsim.world.blocks.foreign import foreign_block

    name = block_id.split(":", 1)[-1]
    block = foreign_block(block_id, {})
    plain_names = ("_block", "bricks", "planks", "wool", "concrete", "terracotta", "stone")
    components = ("note_block", "target", "observer", "dispenser", "dropper", "crafter", "bulb")
    return (
        block.full
        and block.conductor.value == "default"
        and name.endswith(plain_names)
        and not any(part in name for part in components)
    )


#: Steps listed under Edit → Undo History.
HISTORY_MENU_SIZE = 25


def history_label(label: str) -> str:
    """An edit label for people: "place redstone_wire" → "Place Redstone Dust"."""
    verb, _, rest = (label or "edit").partition(" ")
    if rest and " " not in rest and f"minecraft:{rest}" in blocks.REGISTRY:
        rest = block_name(f"minecraft:{rest}")
    else:
        rest = rest.replace("_", " ")
    return f"{verb[:1].upper()}{verb[1:]} {rest}".strip()
