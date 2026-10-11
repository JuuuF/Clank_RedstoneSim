"""Signal sources: a comparator input of a chosen strength, backed by a real block.

The editor offers one "signal source" concept whose value comes from a real game block, so
the simulation stays exact (owner request, doc/ui-direction.md). The backing block can be
swapped in place; each kind differs in ways that matter for circuits (see ``SourceKind``).
Every change is a ``/setblock`` with block-entity data (game-verified: EXP-024, EXP-025);
turning a lectern page like a player is a separate action (``Document.turn_page``).
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from typing import Any

from redsim.core.direction import HORIZONTAL, Direction
from redsim.core.pos import Pos
from redsim.sim.level import Level
from redsim.world import blocks
from redsim.world.block import BlockState
from redsim.world.blocks.container import BarrelBlockEntity, container_signal
from redsim.world.properties import BITES, FACING, HAS_BOOK, HORIZONTAL_FACING

#: Item used to fill barrels (stacks to 64).
FILL_ITEM = "minecraft:redstone"
#: Lectern sources hold a 15-page book: page p (0-based) gives signal p + 1.
BOOK_PAGES = 15


@dataclass(frozen=True)
class SourceKind:
    id: str
    block_id: str
    title: str
    strengths: tuple[int, ...]
    tooltip: str


KINDS: dict[str, SourceKind] = {
    "barrel": SourceKind(
        "barrel",
        "minecraft:barrel",
        "Barrel (container)",
        tuple(range(16)),
        "Barrel: 27 slots; the signal follows the fill level (1 item gives 1, 1 728 items "
        "give 15). Full solid block: it conducts redstone and blocks wires. Pistons cannot "
        "move it (block entity). Comparators update when the contents change "
        "(setChanged). The editor fills it with the fewest redstone dust for the strength.",
    ),
    "lectern": SourceKind(
        "lectern",
        "minecraft:lectern",
        "Lectern (book page)",
        tuple(range(16)),
        "Lectern: the signal follows the open page, floor(page / (pages - 1) * 14) + 1, and "
        "is 0 without a book. Not a full block: it does not conduct. Pistons cannot move "
        "it. Turning a page as a player also sends a 2-tick pulse (strong power into the "
        "block below). The editor uses a 15-page book.",
    ),
    "cake": SourceKind(
        "cake",
        "minecraft:cake",
        "Cake (bites)",
        tuple(range(2, 15, 2)),
        "Cake: signal (7 - bites) * 2, so only even strengths 2-14. Needs a solid block "
        "below; pistons break it. Right click (NORMAL mode) eats a slice.",
    ),
}
SOURCE_BLOCKS = {kind.block_id: kind.id for kind in KINDS.values()}


def kind_of(state: BlockState) -> str | None:
    return SOURCE_BLOCKS.get(state.block.id)


def strength_at(level: Level, pos: Pos) -> int | None:
    """The comparator reading of a source block (None if ``pos`` holds no source)."""
    state = level.get_block_state(pos)
    if kind_of(state) is None:
        return None
    return state.block.get_analog_output_signal(state, level, pos, Direction.NORTH)


def nearest_strength(kind: str, strength: int) -> int:
    """The closest strength this kind can produce (cakes only make even values)."""
    return min(KINDS[kind].strengths, key=lambda s: (abs(s - strength), s))


@cache
def barrel_total(strength: int) -> int:
    """Fewest items (in 64-stacks) for a barrel signal of ``strength``."""
    if strength <= 0:
        return 0
    for total in range(1, BarrelBlockEntity.SIZE * 64 + 1):
        if container_signal(_stacks(total), BarrelBlockEntity.SIZE) >= strength:
            return total
    raise ValueError(f"no barrel fill gives {strength}")


def _stacks(total: int) -> list[tuple[str, int]]:
    stacks = [(FILL_ITEM, 64)] * (total // 64)
    if total % 64:
        stacks.append((FILL_ITEM, total % 64))
    return stacks


def source_setblock(
    kind: str, strength: int, oriented: BlockState | None = None
) -> tuple[str, dict[str, Any] | None]:
    """``/setblock`` state text and block-entity data for a source of ``strength``.

    ``oriented`` supplies the facing (from placement or the block being replaced)."""
    strength = nearest_strength(kind, strength)
    block = blocks.get(KINDS[kind].block_id)
    state = block.default_state
    facing = _facing_of(oriented)
    if kind == "barrel":
        state = state.with_(FACING, facing or Direction.UP)
        items = [
            {"Slot": slot, "id": item, "count": count}
            for slot, (item, count) in enumerate(_stacks(barrel_total(strength)))
        ]
        return repr(state), {"Items": items}
    if kind == "lectern":
        horizontal = facing if facing in HORIZONTAL else Direction.NORTH
        state = state.with_(HORIZONTAL_FACING, horizontal).with_(HAS_BOOK, strength > 0)
        if strength == 0:
            return repr(state), {}
        book = {"id": "minecraft:writable_book", "count": 1, "pages": BOOK_PAGES}
        return repr(state), {"Book": book, "Page": strength - 1}
    state = state.with_(BITES, 7 - strength // 2)
    return repr(state), None


def _facing_of(state: BlockState | None) -> Direction | None:
    if state is None:
        return None
    for prop in (FACING, HORIZONTAL_FACING):
        if state.has(prop):
            value = state.get(prop)
            return value if isinstance(value, Direction) else None
    return None
