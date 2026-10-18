"""Turning and mirroring a whole canonical world (layer 1), timeline and annotations too.

``transform(canon, turns, mirror)`` moves every block above the floor (with its block
entity), the pending engine state of the build (scheduled ticks, piston block events and
their directions, ticker positions), the recorded actions and the sections, labels and
groups. Block states turn with the simulator's own rules (``redsim.world.rotation``: the
game's ``BlockState.rotate`` / ``mirror``). The floor stays as it is.

Used by ``symmetry``: a contraption is direction-independent if every one of its eight
orientations does the same thing, turned the same way.
"""

from __future__ import annotations

import copy
from collections.abc import Callable
from typing import Any

from redsim.core.direction import Direction
from redsim.world import blocks
from redsim.world.rotation import (
    default_pivot2,
    mirror_state,
    rotate_about,
    rotate_direction,
    rotate_state,
)

Pos = tuple[int, int, int]


class Symmetry:
    """A horizontal symmetry about a contraption: an optional east-west mirror, then
    ``turns`` clockwise quarter turns (seen from above) about the box's center, then a
    shift by ``shift`` (dx, dz)."""

    def __init__(
        self, low: Pos, high: Pos, turns: int, mirror: bool, shift: tuple[int, int] = (0, 0)
    ) -> None:
        self.turns = turns % 4
        self.mirror = mirror
        self.shift = shift
        self.pivot2 = default_pivot2(low, high)
        self.mirror_x2 = low[0] + high[0]

    @property
    def name(self) -> str:
        moved = f", shifted {self.shift[0]} {self.shift[1]}" if any(self.shift) else ""
        return f"{'mirror, ' if self.mirror else ''}{self.turns * 90}°{moved}"

    def pos(self, p: Pos) -> Pos:
        x, y, z = p
        if self.mirror:
            x = self.mirror_x2 - x
        x, y, z = rotate_about((x, y, z), self.pivot2, self.turns)
        return (x + self.shift[0], y, z + self.shift[1])

    def direction(self, d: Direction) -> Direction:
        if self.mirror and d in (Direction.EAST, Direction.WEST):
            d = d.opposite
        return rotate_direction(d, self.turns)

    def state(self, text: str) -> str:
        st = blocks.parse_state(text)
        if self.mirror:
            st = mirror_state(st, "x")
        return repr(rotate_state(st, self.turns))


def contraption_box(canon: dict[str, Any], floor_y: int) -> tuple[Pos, Pos]:
    cells = [tuple(b[:3]) for b in canon["blocks"] if b[1] > floor_y]
    low = tuple(min(c[i] for c in cells) for i in range(3))
    high = tuple(max(c[i] for c in cells) for i in range(3))
    return low, high  # type: ignore[return-value]


def floor_of(canon: dict[str, Any]) -> int:
    """``interactions.floor_top`` on canonical data."""
    from collections import Counter

    layers: dict[int, Counter[str]] = {}
    for _x, y, _z, state in canon["blocks"]:
        if not state.endswith(":air"):
            layers.setdefault(y, Counter())[state.split("[")[0]] += 1
    found = min(layers) - 1
    for y in sorted(layers):
        counts = layers[y]
        total = sum(counts.values())
        if total >= 256 and counts.most_common(1)[0][1] >= 0.9 * total:
            found = y
    return found


def transform(
    canon: dict[str, Any], turns: int, mirror: bool, shift: tuple[int, int] = (0, 0)
) -> tuple[dict[str, Any], Symmetry]:
    """Turn / mirror the contraption about its center and shift it. With a shift, the
    floor moves along (the whole world is translated); without, it stays."""
    floor_y = floor_of(canon)
    low, high = contraption_box(canon, floor_y)
    sym = Symmetry(low, high, turns, mirror, shift)
    out = copy.deepcopy(canon)
    if any(shift):
        floor_y = -(10**9)  # everything moves, the floor too

    def moved(p: Any) -> Pos:
        return tuple(p) if p[1] <= floor_y else sym.pos(tuple(p))

    out["blocks"] = sorted(
        ([*moved(b[:3]), b[3] if b[1] <= floor_y else sym.state(b[3])] for b in canon["blocks"]),
        key=lambda b: (b[1], b[2], b[0]),
    )
    for entry in out["block_entities"]:
        if entry["pos"][1] > floor_y:
            entry["pos"] = list(sym.pos(tuple(entry["pos"])))
            entry["state"] = sym.state(entry["state"])
    runtime = out["engine_runtime"]
    for tick in runtime.get("scheduled_ticks", []) + runtime.get("ticks_to_run", []):
        tick["pos"] = list(moved(tick["pos"]))
    events = []
    for pos, block_id, b0, b1 in runtime.get("block_events", []):
        if "piston" in block_id:
            b1 = sym.direction(Direction.from_data3d(b1)).data3d
        events.append([list(moved(pos)), block_id, b0, b1])
    runtime["block_events"] = events
    runtime["tickers_by_pos"] = {
        ",".join(map(str, moved(tuple(int(v) for v in key.split(","))))): value
        for key, value in runtime.get("tickers_by_pos", {}).items()
    }
    for action in out["timeline"]["actions"]:
        if action.get("pos") is not None:
            action["pos"] = list(moved(action["pos"]))
        if action.get("state"):
            action["state"] = sym.state(action["state"])
        if action.get("payload"):
            raise NotImplementedError(f"cannot turn an action with a payload: {action}")
    _annotations(out["annotations"], moved)
    return out, sym


def _annotations(notes: dict[str, Any], moved: Callable[[Any], Pos]) -> None:
    for section in notes.get("sections", {}).values():
        section["positions"] = [list(moved(p)) for p in section.get("positions", [])]
    for label in notes.get("labels", {}).values():
        label["pos"] = list(moved(label["pos"]))
    for group in notes.get("groups", []):
        a, b = moved(group["low"]), moved(group["high"])
        group["low"] = [min(a[i], b[i]) for i in range(3)]
        group["high"] = [max(a[i], b[i]) for i in range(3)]
        for port in group.get("ports", []):
            if "pos" in port:
                port["pos"] = list(moved(port["pos"]))
    notes["monitors"] = [list(moved(p)) for p in notes.get("monitors", [])]
