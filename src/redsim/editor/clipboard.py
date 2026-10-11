"""Regions, captured block structures ("prefabs") and their placement payloads.

A prefab stores every position of a box (air included), relative to the box's minimum
corner, in ``/clone`` source order (z outer, then y, then x), with block-entity data. It is
placed with ``Action("clone")``, which ports ``CloneCommands.clone`` (replace mode).

Rotation has no ``/clone`` equivalent. A rotated prefab is treated as if it had been
captured from a rotated copy of the region: offsets and states are rotated, then put back
into z/y/x order. Scheduled ticks are never copied; a pasted circuit starts from its block
states only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from redsim.core.pos import Pos
from redsim.sim.level import Level
from redsim.world import blocks
from redsim.world.rotation import mirror_state, rotate_offset, rotate_state

FORMAT = "redsim-prefab"


@dataclass(frozen=True)
class Region:
    low: Pos
    high: Pos

    @staticmethod
    def from_corners(a: Pos, b: Pos) -> Region:
        low = (min(a[0], b[0]), min(a[1], b[1]), min(a[2], b[2]))
        high = (max(a[0], b[0]), max(a[1], b[1]), max(a[2], b[2]))
        return Region(low, high)

    @property
    def size(self) -> tuple[int, int, int]:
        return (
            self.high[0] - self.low[0] + 1,
            self.high[1] - self.low[1] + 1,
            self.high[2] - self.low[2] + 1,
        )

    def positions(self) -> list[Pos]:
        """``/clone`` and ``/fill`` order: z outer, then y, then x."""
        return [
            (x, y, z)
            for z in range(self.low[2], self.high[2] + 1)
            for y in range(self.low[1], self.high[1] + 1)
            for x in range(self.low[0], self.high[0] + 1)
        ]

    def contains(self, pos: Pos) -> bool:
        return all(self.low[i] <= pos[i] <= self.high[i] for i in range(3))


@dataclass
class Prefab:
    name: str
    size: tuple[int, int, int]
    blocks: list[tuple[int, int, int, str, dict[str, Any] | None]]

    @staticmethod
    def capture(level: Level, region: Region, name: str = "clipboard") -> Prefab:
        entries: list[tuple[int, int, int, str, dict[str, Any] | None]] = []
        for pos in region.positions():
            state = level.get_block_state(pos)
            entity = level.get_block_entity(pos, create=False) if state.has_block_entity else None
            data = entity.to_json() if entity is not None else None
            low = region.low
            entries.append((pos[0] - low[0], pos[1] - low[1], pos[2] - low[2], repr(state), data))
        return Prefab(name, region.size, entries)

    @property
    def non_air_count(self) -> int:
        return sum(1 for entry in self.blocks if entry[3] != "minecraft:air")

    def rotated(self, quarter_turns: int = 1) -> Prefab:
        turned = []
        for dx, dy, dz, text, data in self.blocks:
            offset = rotate_offset((dx, dy, dz), quarter_turns)
            state = rotate_state(blocks.parse_state(text), quarter_turns)
            turned.append((offset, repr(state), data))
        low = tuple(min(entry[0][i] for entry in turned) for i in range(3))
        normalized = [
            (o[0] - low[0], o[1] - low[1], o[2] - low[2], text, data) for o, text, data in turned
        ]
        normalized.sort(key=lambda entry: (entry[2], entry[1], entry[0]))
        sx, sy, sz = self.size
        size = (sz, sy, sx) if quarter_turns % 2 else (sx, sy, sz)
        return Prefab(self.name, size, normalized)

    def mirrored(self, axis: str) -> Prefab:
        """Mirror the prefab: ``"x"`` swaps east and west, ``"z"`` north and south."""
        flipped = []
        for dx, dy, dz, text, data in self.blocks:
            if axis == "x":
                dx = self.size[0] - 1 - dx
            else:
                dz = self.size[2] - 1 - dz
            state = mirror_state(blocks.parse_state(text), axis)
            flipped.append((dx, dy, dz, repr(state), data))
        flipped.sort(key=lambda entry: (entry[2], entry[1], entry[0]))
        return Prefab(self.name, self.size, flipped)

    def payload(self) -> dict[str, Any]:
        return {"blocks": [list(entry) for entry in self.blocks]}

    def to_json(self) -> dict[str, Any]:
        return {"format": FORMAT, "name": self.name, "size": list(self.size), **self.payload()}

    @staticmethod
    def from_json(data: dict[str, Any]) -> Prefab:
        if data.get("format", FORMAT) != FORMAT:
            raise ValueError("not a redsim prefab")
        entries = [(int(e[0]), int(e[1]), int(e[2]), str(e[3]), e[4]) for e in data["blocks"]]
        sx, sy, sz = data["size"]
        return Prefab(str(data["name"]), (int(sx), int(sy), int(sz)), entries)
