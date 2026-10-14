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
from redsim.world.blocks.composter import LEVEL
from redsim.world.blocks.container import BarrelBlockEntity, container_signal
from redsim.world.properties import BITES, FACING, FACING_HOPPER, HAS_BOOK, HORIZONTAL_FACING

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
    "hopper": SourceKind(
        "hopper",
        "minecraft:hopper",
        "Hopper (container)",
        tuple(range(16)),
        "Hopper: 5 slots; the signal follows the fill level like a barrel's (1 item gives "
        "1, 320 give 15). It moves items: into a container it points at and out of one "
        "above, unless powered (locked). Not a full block. Pistons cannot move it.",
    ),
    "chest": SourceKind(
        "chest",
        "minecraft:chest",
        "Chest (container)",
        tuple(range(16)),
        "Chest: 27 slots, read like a barrel; a chest next to it of the same kind joins it "
        "into a double chest (54 slots, both halves read the whole). A block on top stops "
        "comparators reading it (0). Not a full block: it does not conduct. Pistons "
        "cannot move it.",
    ),
    "composter": SourceKind(
        "composter",
        "minecraft:composter",
        "Composter (level)",
        tuple(range(9)),
        "Composter: the signal is its level, 0-8. Level 7 becomes 8 after 20 ticks; a "
        "player (right click) or a hopper below empties a full one. Solid but hollow: it "
        "does not conduct. Pistons can move it (no block entity).",
    ),
}
SOURCE_BLOCKS = {kind.block_id: kind.id for kind in KINDS.values()}
#: Blocks placed as a signal source of the chosen strength (BUILD mode, the inventory's
#: Signal sources folder). Hoppers and chests are placed empty, like any container; the
#: inspector still offers them as source kinds.
PLACED_AS_SOURCE = {
    block_id: kind for block_id, kind in SOURCE_BLOCKS.items() if kind not in ("hopper", "chest")
}


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
def barrel_total(strength: int, size: int = BarrelBlockEntity.SIZE) -> int:
    """Fewest items (in 64-stacks) for a signal of ``strength`` from a container of
    ``size`` slots (a barrel by default)."""
    if strength <= 0:
        return 0
    for total in range(1, size * 64 + 1):
        if container_signal(_stacks(total), size) >= strength:
            return total
    raise ValueError(f"no fill of {size} slots gives {strength}")


#: Slots of the containers offered as sources.
CONTAINER_SIZES = {"barrel": 27, "hopper": 5, "chest": 27}


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
    if kind in CONTAINER_SIZES:
        if kind == "barrel":
            state = state.with_(FACING, facing or Direction.UP)
        elif kind == "hopper":  # down or sideways, never up
            state = state.with_(
                FACING_HOPPER, facing if facing in FACING_HOPPER.values else Direction.DOWN
            )
        else:
            horizontal = facing if facing in HORIZONTAL else Direction.NORTH
            state = state.with_(HORIZONTAL_FACING, horizontal)
        total = barrel_total(strength, CONTAINER_SIZES[kind])
        items = [
            {"Slot": slot, "id": item, "count": count}
            for slot, (item, count) in enumerate(_stacks(total))
        ]
        return repr(state), {"Items": items}
    if kind == "composter":
        return repr(state.with_(LEVEL, strength)), None
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
    for prop in (FACING, HORIZONTAL_FACING, FACING_HOPPER):
        if state.has(prop):
            value = state.get(prop)
            return value if isinstance(value, Direction) else None
    return None
