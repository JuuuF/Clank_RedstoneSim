"""An index of the builds in a Minecraft save, for "go to the builds" (doc/world-import.md).

Every chunk's section palettes are read (no blocks are imported): sections holding
anything but air, terrain and natural blocks (plants, trees, water, …) are decoded to find
those blocks. Chunks with such blocks that touch (also diagonally) form one build, with
its box, its number of blocks and of redstone parts, and its most common parts. Builds
are listed with the most redstone first. The example save (4 675 chunks) takes about 2 s.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from redsim.mcworld.chunk import AIR, palette_entry, state_text
from redsim.mcworld.region import RegionFile
from redsim.mcworld.stream import TERRAIN, unpack_array

Pos = tuple[int, int, int]

#: Name parts of natural blocks (not builds): plants, trees, fluids, snow and the like.
NATURE = (
    "grass", "fern", "flower", "leaves", "_log", "_wood", "water", "lava", "snow", "vine",
    "kelp", "seagrass", "dandelion", "poppy", "tulip", "orchid", "allium", "bluet", "daisy",
    "cornflower", "lily", "bush", "mushroom", "sugar_cane", "cactus", "pumpkin", "melon",
    "bamboo", "roots", "moss", "dripleaf", "azalea", "dripstone", "lichen", "sculk", "ice",
    "_ore", "sapling", "propagule", "spore", "petals", "pickle", "coral", "amethyst",
    "cobweb", "dead_bush", "hanging_moss", "firefly",
)  # fmt: skip
#: Name parts of redstone parts (what makes a build interesting here).
REDSTONE = (
    "redstone", "repeater", "comparator", "piston", "observer", "lever", "button",
    "pressure_plate", "lamp", "hopper", "dropper", "dispenser", "target", "note_block",
    "rail", "copper_bulb", "daylight_detector", "tripwire", "trapped_chest", "slime_block",
    "honey_block", "sculk_sensor", "crafter",
)  # fmt: skip


def is_build_block(block_id: str) -> bool:
    """Not air, terrain or nature: something a player placed."""
    if block_id in AIR or block_id in TERRAIN:
        return False
    name = block_id.removeprefix("minecraft:")
    return not any(part in name for part in NATURE)


def is_redstone(block_id: str) -> bool:
    name = block_id.removeprefix("minecraft:")
    return any(part in name for part in REDSTONE)


@dataclass
class Build:
    """Touching chunks with placed blocks."""

    low: Pos
    high: Pos
    blocks: int
    redstone: int
    parts: Counter[str] = field(default_factory=Counter)  # block id → count (all placed)
    chunks: int = 0

    @property
    def center(self) -> tuple[float, float, float]:
        return (
            (self.low[0] + self.high[0] + 1) / 2,
            (self.low[1] + self.high[1] + 1) / 2,
            (self.low[2] + self.high[2] + 1) / 2,
        )

    @property
    def size(self) -> Pos:
        return (
            self.high[0] - self.low[0] + 1,
            self.high[1] - self.low[1] + 1,
            self.high[2] - self.low[2] + 1,
        )

    def top_parts(self, count: int = 4) -> list[tuple[str, int]]:
        """The most common parts, redstone parts first."""
        ranked = sorted(self.parts.items(), key=lambda item: (not is_redstone(item[0]), -item[1]))
        return ranked[:count]


@dataclass
class _ChunkBuild:
    low: list[int]
    high: list[int]
    parts: Counter[str]


def _scan_chunk(cx: int, cz: int, chunk: dict[str, Any]) -> _ChunkBuild | None:
    found: _ChunkBuild | None = None
    for raw in chunk.get("sections", []):
        sy = int(raw["Y"])
        states = raw.get("block_states", {})
        palette = [state_text(*palette_entry(e)) for e in states.get("palette", [])]
        ids = [text.split("[", 1)[0] for text in palette]
        wanted = [i for i, block_id in enumerate(ids) if is_build_block(block_id)]
        if not wanted:
            continue
        if len(palette) == 1:
            counts = {0: 4096}
            cells = np.array([[0, 0, 0], [15, 15, 15]])
        else:
            index = unpack_array(states.get("data", []), len(palette))
            mask = np.isin(index, wanted)
            cells = np.argwhere(mask)
            values, numbers = np.unique(index[mask], return_counts=True)
            counts = {int(v): int(n) for v, n in zip(values, numbers, strict=True)}
        if not len(cells):
            continue
        y0, z0, x0 = cells.min(axis=0)
        y1, z1, x1 = cells.max(axis=0)
        low = [cx * 16 + int(x0), sy * 16 + int(y0), cz * 16 + int(z0)]
        high = [cx * 16 + int(x1), sy * 16 + int(y1), cz * 16 + int(z1)]
        parts = Counter({ids[i]: n for i, n in counts.items()})
        if found is None:
            found = _ChunkBuild(low, high, parts)
        else:
            found.low = [min(a, b) for a, b in zip(found.low, low, strict=True)]
            found.high = [max(a, b) for a, b in zip(found.high, high, strict=True)]
            found.parts.update(parts)
    return found


def scan_builds(
    regions: Any, progress: Callable[[int, int], None] | None = None, min_blocks: int = 4
) -> list[Build]:
    """The builds of the region files in the folder ``regions``, most redstone first.
    ``progress(done, total)`` is called per region file. Builds with fewer than
    ``min_blocks`` placed blocks and no redstone are left out."""
    files = sorted(regions.glob("r.*.*.mca"))
    chunks: dict[tuple[int, int], _ChunkBuild] = {}
    for done, path in enumerate(files):
        region = RegionFile(path)
        for cx, cz in region.chunks():
            chunk = region.read_chunk(cx, cz)
            if chunk is not None:
                found = _scan_chunk(cx, cz, chunk)
                if found is not None:
                    chunks[(cx, cz)] = found
        if progress is not None:
            progress(done + 1, len(files))
    builds: list[Build] = []
    seen: set[tuple[int, int]] = set()
    for start in chunks:
        if start in seen:
            continue
        seen.add(start)
        todo, members = [start], []
        while todo:  # flood fill over touching chunks
            cx, cz = todo.pop()
            members.append(chunks[(cx, cz)])
            for dx in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    near = (cx + dx, cz + dz)
                    if near in chunks and near not in seen:
                        seen.add(near)
                        todo.append(near)
        parts: Counter[str] = Counter()
        for member in members:
            parts.update(member.parts)
        low = tuple(min(m.low[i] for m in members) for i in range(3))
        high = tuple(max(m.high[i] for m in members) for i in range(3))
        total = sum(parts.values())
        redstone = sum(n for block_id, n in parts.items() if is_redstone(block_id))
        if redstone or total >= min_blocks:
            builds.append(Build(low, high, total, redstone, parts, len(members)))  # type: ignore[arg-type]
    builds.sort(key=lambda b: (-b.redstone, -b.blocks))
    return builds
