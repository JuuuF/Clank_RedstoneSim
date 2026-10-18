"""Layer 2: what the blocks of a world can do to each other, derived from layer 1.

Everything here is computed by the simulator's own code on the build, never guessed from
block names alone:

- ``role``: what kind of part a block is (piston, wire, diode, power source, input, door
  block, structure …), from its id;
- ``block_facts``: whether it conducts redstone (``isRedstoneConductor``), how a piston
  treats it (``getPistonPushReaction`` and ``PistonBaseBlock.isPushable``: movable,
  breaks, blocks), whether it sticks (slime, honey);
- ``pistons``: every piston with its facing, head cell, and what it would move now
  (``PistonStructureResolver`` run on the build: the push of a retracted piston, the pull
  of an extended sticky one) and the positions whose signal can switch it, including the
  quasi-connected ones (``PistonBaseBlock.getNeighborSignal``);
- ``doorway``: the output section as a door: its plane, grid and cells.

The dynamic part of layer 2 (what actually powered and moved what, tick by tick) is in
``replay`` (piston events, power notes, causal links).
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any

from redsim.cli.views import state_text
from redsim.core.direction import ALL, Direction
from redsim.core.pos import Pos, above, offset
from redsim.world.block import PushReaction
from redsim.world.blocks import piston as piston_mod
from redsim.world.blocks.foreign import ForeignBlock

#: Roles by block id (without ``minecraft:``); a block not listed is "structure".
_ROLES = {
    "piston": "piston",
    "sticky_piston": "piston",
    "piston_head": "piston_head",
    "moving_piston": "moving",
    "redstone_wire": "wire",
    "repeater": "repeater",
    "comparator": "comparator",
    "observer": "observer",
    "redstone_torch": "torch",
    "redstone_wall_torch": "torch",
    "redstone_block": "redstone_block",
    "target": "target",
    "lever": "lever",
    "tripwire_hook": "tripwire",
    "tripwire": "tripwire",
    "slime_block": "sticky_block",
    "honey_block": "sticky_block",
    "note_block": "bud",
    "redstone_lamp": "lamp",
    "dropper": "dropper",
    "dispenser": "dispenser",
    "hopper": "hopper",
    "crafter": "crafter",
    "activator_rail": "rail",
    "detector_rail": "rail",
    "powered_rail": "rail",
}
_SUFFIX_ROLES = (
    ("_button", "button"),
    ("_pressure_plate", "plate"),
    ("_trapdoor", "trapdoor"),
    ("_door", "door"),
    ("_fence_gate", "gate"),
    ("copper_bulb", "copper_bulb"),
    ("lightning_rod", "lightning_rod"),
)
#: Blocks read by comparators (analog sources) that appear in the corpus.
_ANALOG = {
    "barrel",
    "furnace",
    "jukebox",
    "composter",
    "water_cauldron",
    "cauldron",
    "chest",
    "lectern",
    "cake",
    "enchanting_table",
    "bookshelf",
}

INPUT_ROLES = {"lever", "button", "plate", "tripwire"}
LOGIC_ROLES = {
    "wire",
    "repeater",
    "comparator",
    "observer",
    "torch",
    "redstone_block",
    "target",
    "bud",
    "lamp",
    "copper_bulb",
    "rail",
    "crafter",
    "lightning_rod",
}


def block_id(state_or_text: Any) -> str:
    text = state_or_text if isinstance(state_or_text, str) else repr(state_or_text)
    return text.split("[", 1)[0].removeprefix("minecraft:")


def role(state_or_text: Any) -> str:
    name = block_id(state_or_text)
    if name in _ROLES:
        return _ROLES[name]
    for suffix, value in _SUFFIX_ROLES:
        if name.endswith(suffix):
            return value
    if name in _ANALOG:
        return "analog"
    if name == "air":
        return "air"
    return "structure"


@dataclass(frozen=True)
class Facts:
    conductor: bool  # a solid block that redstone can power (and that powers through)
    push: str  # how a piston treats it here: move / break / blocks / ignore / push_only
    sticks: bool  # slime or honey
    foreign: bool  # not simulated (the simulator keeps it but it does nothing)


def block_facts(level: Any, pos: Pos, direction: Direction = Direction.UP) -> Facts:
    """The simulator's view of the block at ``pos`` (pushed in ``direction``)."""
    state = level.get_block_state(pos)
    if state.is_air:
        return Facts(False, "ignore", False, False)
    reaction = state.get_piston_push_reaction()
    if reaction is PushReaction.POPPED:
        push = "break"
    elif reaction is PushReaction.IMMOVEABLE:
        push = "blocks"
    elif reaction is PushReaction.IGNORE_ENTITY:
        push = "ignore"
    else:
        movable = piston_mod.is_pushable(state, level, pos, direction, False, direction)
        push = ("push_only" if reaction is PushReaction.PUSH else "move") if movable else "blocks"
    return Facts(
        conductor=bool(state.is_redstone_conductor(level, pos)),
        push=push,
        sticks=block_id(state) in ("slime_block", "honey_block"),
        foreign=isinstance(state.block, ForeignBlock),
    )


def floor_top(level: Any) -> int:
    """The top layer of the ground: the highest y holding at least 256 blocks, 90 % of
    one kind (a new world's floor at y=0, an imported superflat's grass at y=-61). Below
    the lowest block if there is no such layer."""
    layers: dict[int, Counter[str]] = {}
    for pos, state in level.blocks.items():
        if not state.is_air:
            layers.setdefault(pos[1], Counter())[block_id(state)] += 1
    if not layers:
        return 0
    found = min(layers) - 1
    for y in sorted(layers):
        counts = layers[y]
        total = sum(counts.values())
        if total >= 256 and counts.most_common(1)[0][1] >= 0.9 * total:
            found = y
    return found


def census(level: Any, floor_y: int | None = None) -> dict[str, Any]:
    """Counts of block kinds and roles above the floor, and the box they fill."""
    if floor_y is None:
        floor_y = floor_top(level)
    names: Counter[str] = Counter()
    roles: Counter[str] = Counter()
    foreign: Counter[str] = Counter()
    low = [None, None, None]
    high = [None, None, None]
    for pos, state in level.blocks.items():
        if state.is_air or pos[1] <= floor_y:
            continue
        name = block_id(state)
        names[name] += 1
        roles[role(state)] += 1
        if isinstance(state.block, ForeignBlock):
            foreign[name] += 1
        for i in range(3):
            low[i] = pos[i] if low[i] is None else min(low[i], pos[i])
            high[i] = pos[i] if high[i] is None else max(high[i], pos[i])
    size = [h - lo + 1 for lo, h in zip(low, high, strict=True)] if low[0] is not None else [0] * 3
    return {
        "blocks": sum(names.values()),
        "box": [low, high],
        "size": size,
        "volume": size[0] * size[1] * size[2],
        "kinds": dict(names.most_common()),
        "roles": dict(roles.most_common()),
        "foreign": dict(foreign),
        "floor_top": floor_y,
    }


# --------------------------------------------------------------------------- pistons
def piston_facing(state: Any) -> Direction:
    return piston_mod.piston_facing(state)


def power_positions(pos: Pos, facing: Direction) -> list[tuple[Pos, Direction, bool]]:
    """The positions ``getNeighborSignal`` asks, in its order: (position, direction asked,
    reached through the block above = quasi-connectivity)."""
    out = [(offset(pos, d), d, False) for d in ALL if d is not facing]
    out.append((pos, Direction.DOWN, False))  # the block's own signal downwards (L127)
    up = above(pos)
    out.extend((offset(up, d), d, True) for d in ALL if d is not Direction.DOWN)
    return out


@dataclass
class Piston:
    pos: Pos
    sticky: bool
    facing: str
    extended: bool
    head: Pos
    #: What it would move if it fired now: pushed on extension, pulled on retraction.
    would_move: list[Pos]
    would_break: list[Pos]
    movable_now: bool  # the resolver accepts the move
    #: Positions that can switch it, with the part there now (empty positions left out).
    neighbors: list[dict[str, Any]]

    def to_json(self) -> dict[str, Any]:
        return {
            "pos": list(self.pos),
            "sticky": self.sticky,
            "facing": self.facing,
            "extended": self.extended,
            "head": list(self.head),
            "would_move": [list(p) for p in self.would_move],
            "would_break": [list(p) for p in self.would_break],
            "movable_now": self.movable_now,
            "neighbors": self.neighbors,
        }


def pistons(level: Any) -> list[Piston]:
    out = []
    for pos, state in sorted(level.blocks.items()):
        name = block_id(state)
        if name not in ("piston", "sticky_piston"):
            continue
        facing = piston_facing(state)
        extended = bool(state.get(piston_mod.EXTENDED))
        sticky = name == "sticky_piston"
        move: list[Pos] = []
        broken: list[Pos] = []
        ok = True
        if not extended or sticky:
            # A retraction removes the head before resolving (moveBlocks L229): so here.
            head = offset(pos, facing)
            kept = level.blocks.get(head) if extended else None
            if extended:
                level.blocks.pop(head, None)
            try:
                resolver = piston_mod.PistonStructureResolver(level, pos, facing, not extended)
                ok = resolver.resolve()
                move, broken = list(resolver.to_push), list(resolver.to_destroy)
            finally:
                if kept is not None:
                    level.blocks[head] = kept
        neighbors = []
        for where, _direction, quasi in power_positions(pos, facing):
            if where == pos:
                continue
            there = level.get_block_state(where)
            if there.is_air:
                continue
            kind = role(there)
            if kind in ("structure", "analog") and not there.is_redstone_conductor(level, where):
                continue
            neighbors.append(
                {"pos": list(where), "part": state_text(there), "role": kind, "quasi": quasi}
            )
        out.append(
            Piston(
                pos,
                sticky,
                facing.name.lower(),
                extended,
                offset(pos, facing),
                move,
                broken,
                ok,
                neighbors,
            )
        )
    return out


# --------------------------------------------------------------------------- the doorway
@dataclass
class Doorway:
    """The output section read as a door: its cells and the plane they lie in."""

    cells: list[Pos]
    normal: str | None  # the axis across the door (x or z), None if not flat
    plane: int | None  # the coordinate of that axis
    width: int
    height: int
    columns: list[int]  # the in-plane horizontal coordinates, west/north first
    rows: list[int]  # y, top first
    extra_cells: list[Pos]  # outputs outside the plane (stairs, tables …)

    def grid(self, filled: dict[Pos, str]) -> list[str]:
        """The doorway seen from the low side of its normal, one string per row."""
        lines = []
        for y in self.rows:
            line = ""
            for c in self.columns:
                p = (self.plane, y, c) if self.normal == "x" else (c, y, self.plane)
                line += filled.get(p, " ") if p in self.cells else " "
            lines.append(line)
        return lines

    def to_json(self) -> dict[str, Any]:
        return {
            "normal": self.normal,
            "plane": self.plane,
            "width": self.width,
            "height": self.height,
            "cells": [list(c) for c in self.cells],
            "extra_cells": [list(c) for c in self.extra_cells],
        }


def doorway(cells: list[Pos]) -> Doorway:
    """The plane holding most of the cells (x = const or z = const)."""
    if not cells:
        return Doorway([], None, None, 0, 0, [], [], [])
    best: tuple[int, str, int] | None = None
    for axis, index in (("x", 0), ("z", 2)):
        counts = Counter(c[index] for c in cells)
        value, count = counts.most_common(1)[0]
        if best is None or count > best[0]:
            best = (count, axis, value)
    assert best is not None
    _, axis, value = best
    index = 0 if axis == "x" else 2
    inside = [c for c in cells if c[index] == value]
    extra = [c for c in cells if c[index] != value]
    other = 2 if axis == "x" else 0
    columns = sorted({c[other] for c in inside})
    rows = sorted({c[1] for c in inside}, reverse=True)
    return Doorway(
        cells=sorted(inside, key=lambda c: (-c[1], c[other])),
        normal=axis,
        plane=value,
        width=max(columns) - min(columns) + 1,
        height=max(rows) - min(rows) + 1,
        columns=list(range(min(columns), max(columns) + 1)),
        rows=list(range(max(rows), min(rows) - 1, -1)),
        extra_cells=sorted(extra),
    )
