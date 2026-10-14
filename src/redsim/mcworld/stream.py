"""Loading a Minecraft world chunk by chunk around the camera, like the game
(doc/world-import.md, phase 3).

Every loaded section is kept compactly: a section of one block as its state text, any
other as a palette and a 16³ index array (a few kB). Only blocks that matter enter the
document: every non-terrain block, and terrain that is exposed (a face towards air),
touches a non-terrain block (a face, edge or corner), or lies within piston reach of a
block mover. Because sections are kept, this is decided exactly across chunk borders: a
block at the edge of the loaded area waits until its neighbor chunk is known, and loading
a chunk re-checks the chunks around it. The decision is made per section with numpy on
the section and a one-block rim from its 26 neighbors.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np

from redsim.mcworld.chunk import AIR, palette_entry, state_text
from redsim.mcworld.region import RegionFile, region_of

if TYPE_CHECKING:
    from redsim.mcworld.importer import SaveInfo

Pos = tuple[int, int, int]
Section = tuple[int, int, int]  # chunk x, section y, chunk z
Box = tuple[Pos, Pos]
MIN_SECTION = -4  # the overworld's lowest section (y -64)

#: Plain full cubes that make up terrain: redstone cannot change them, so buried ones far
#: from builds are left out.
TERRAIN = frozenset(
    "minecraft:" + name
    for name in (
        "stone", "bedrock", "dirt", "grass_block", "deepslate", "tuff", "granite", "diorite",
        "andesite", "sand", "sandstone", "red_sand", "gravel", "clay", "netherrack",
        "end_stone", "quartz_block", "smooth_stone", "cobblestone", "coarse_dirt", "podzol",
        "mycelium", "calcite", "terracotta", "snow_block", "packed_ice", "blackstone",
        "basalt", "smooth_sandstone", "coal_ore", "iron_ore", "copper_ore", "deepslate_iron_ore",
    )
)  # fmt: skip
#: Blocks that move others: terrain within piston reach of them is always kept.
MOVERS = frozenset(
    {
        "minecraft:piston",
        "minecraft:sticky_piston",
        "minecraft:piston_head",
        "minecraft:moving_piston",
    }
)
PISTON_REACH = 13  # the push limit (12) plus the block it moves into

# What a block is, for deciding which terrain matters.
AIR_KIND, TERRAIN_KIND, BUILD_KIND, UNKNOWN_KIND = 0, 1, 2, 3
_CHUNK_AROUND = tuple((dx, dz) for dx in (-1, 0, 1) for dz in (-1, 0, 1) if dx or dz)
# Per offset -1/0/1: where a neighbor's slice goes in the 18-wide rim grid, and which
# slice of the neighbor it is.
_RIM_DST = {-1: slice(0, 1), 0: slice(1, 17), 1: slice(17, 18)}
_RIM_SRC = {-1: slice(15, 16), 0: slice(0, 16), 1: slice(0, 1)}
_FILLED = [np.full((16, 16, 16), kind, np.int8) for kind in range(4)]  # never written to


def chunks_around(center: tuple[int, int], radius: int) -> list[tuple[int, int]]:
    """Chunks within ``radius`` (a circle, like the game's view distance), nearest first."""
    cx, cz = center
    cells = [
        (cx + dx, cz + dz)
        for dx in range(-radius, radius + 1)
        for dz in range(-radius, radius + 1)
        if dx * dx + dz * dz <= radius * radius + radius
    ]
    return sorted(cells, key=lambda c: (c[0] - cx) ** 2 + (c[1] - cz) ** 2)


def _boxes(points: list[Pos], margin: int) -> list[tuple[Pos, Pos]]:
    """Boxes around clusters of ``points`` grown by ``margin`` (merged when they touch)."""
    boxes: list[tuple[Pos, Pos]] = []
    for x, y, z in points:
        lo, hi = (x - margin, y - margin, z - margin), (x + margin, y + margin, z + margin)
        merged = True
        while merged:
            merged = False
            for i, (blo, bhi) in enumerate(boxes):
                if all(lo[a] <= bhi[a] + 1 and blo[a] <= hi[a] + 1 for a in range(3)):
                    lo = (min(lo[0], blo[0]), min(lo[1], blo[1]), min(lo[2], blo[2]))
                    hi = (max(hi[0], bhi[0]), max(hi[1], bhi[1]), max(hi[2], bhi[2]))
                    del boxes[i]
                    merged = True
                    break
        boxes.append((lo, hi))
    return boxes


def _kind(text: str) -> int:
    if text in AIR:
        return AIR_KIND
    return TERRAIN_KIND if text.split("[", 1)[0] in TERRAIN else BUILD_KIND


@dataclass
class _Section:
    palette: list[str]
    index: np.ndarray | None  # (16, 16, 16) uint16 [y, z, x]; None: all palette[0]
    table: np.ndarray  # int8: the kind of each palette entry
    done: np.ndarray  # (16, 16, 16) bool: given to the document
    _kinds: np.ndarray | None = None

    @property
    def kinds(self) -> np.ndarray:
        """The kind of every block (16³; read-only)."""
        if self.index is None:
            return _FILLED[int(self.table[0])]
        if self._kinds is None:
            self._kinds = self.table[self.index]
        return self._kinds

    def text(self, y: int, z: int, x: int) -> str:
        return self.palette[0 if self.index is None else self.index[y, z, x]]


@dataclass
class ChunkLoad:
    """What loading chunks adds to the document."""

    blocks: dict[Pos, str] = field(default_factory=dict)
    block_entities: dict[Pos, dict[str, Any]] = field(default_factory=dict)
    block_ticks: list[dict[str, Any]] = field(default_factory=list)
    chunks: list[tuple[int, int]] = field(default_factory=list)

    def merge(self, other: ChunkLoad) -> None:
        self.blocks.update(other.blocks)
        self.block_entities.update(other.block_entities)
        self.block_ticks.extend(other.block_ticks)
        self.chunks.extend(other.chunks)


def unpack_array(data: Iterable[int], palette_size: int) -> np.ndarray:
    """The 4096 palette indices packed in a section's ``data`` longs, as [y, z, x]."""
    bits = max(4, (palette_size - 1).bit_length())
    per_long = 64 // bits
    longs = np.array([v & 0xFFFFFFFFFFFFFFFF for v in data], dtype=np.uint64)
    shifts = np.arange(per_long, dtype=np.uint64) * np.uint64(bits)
    values = (longs[:, None] >> shifts[None, :]) & np.uint64((1 << bits) - 1)
    return values.reshape(-1)[:4096].astype(np.uint16).reshape(16, 16, 16)


class WorldStream:
    def __init__(self, info: SaveInfo) -> None:
        self.info = info
        self.loaded: set[tuple[int, int]] = set()
        self.missing: set[tuple[int, int]] = set()  # chunks the save does not have
        self.sections: dict[Section, _Section] = {}
        self.movers: list[Pos] = []
        self.reach: list[Box] = []
        self._regions: dict[tuple[int, int], RegionFile | None] = {}
        #: The save's builds (``mcworld.index.scan_builds``), once asked for.
        self.builds: list[Any] | None = None
        #: Chunks whose saved data has pending block ticks (rewritten on saving, so ticks
        #: that ran in the simulation do not run again in the game).
        self.ticked: set[tuple[int, int]] = set()
        #: Chunks a reopened document already holds: read again (to know their sections)
        #: without giving their blocks to the document a second time.
        self.reload: list[tuple[int, int]] = []

    # ------------------------------------------------------------------ queries
    def wanted(self, center: tuple[int, int], radius: int) -> list[tuple[int, int]]:
        """Chunks within ``radius`` of ``center`` not loaded yet, nearest first."""
        return [
            c
            for c in chunks_around(center, radius)
            if c not in self.loaded and c not in self.missing
        ]

    def block_at(self, pos: Pos) -> str | None:
        """State text of a loaded block; None for air or a block not loaded."""
        x, y, z = pos
        section = self.sections.get((x >> 4, y >> 4, z >> 4))
        if section is None:
            return None
        text = section.text(y & 15, z & 15, x & 15)
        return None if text in AIR else text

    def skipped(self) -> int:
        """Loaded non-air blocks not given to the document (buried terrain)."""
        total = 0
        for section in self.sections.values():
            total += int(((section.kinds != AIR_KIND) & ~section.done).sum())
        return total

    # ------------------------------------------------------------------ loading
    def load(self, chunks: Iterable[tuple[int, int]]) -> ChunkLoad:
        """Load these chunks (loaded and missing ones are skipped)."""
        result = ChunkLoad()
        for cx, cz in chunks:
            if (cx, cz) not in self.loaded and (cx, cz) not in self.missing:
                result.merge(self._load_one(cx, cz))
        return result

    def reload_some(self, budget: float) -> int:
        """Read chunks of ``reload`` for up to ``budget`` seconds; their blocks are not
        handed out (the document has them, edits included). Returns how many."""
        import time

        deadline = time.perf_counter() + budget
        count = 0
        while self.reload and time.perf_counter() < deadline:
            self.load([self.reload.pop(0)])
            count += 1
        return count

    def _region(self, cx: int, cz: int) -> RegionFile | None:
        key = region_of(cx, cz)
        if key not in self._regions:
            path = self.info.regions / f"r.{key[0]}.{key[1]}.mca"
            self._regions[key] = RegionFile(path) if path.exists() else None
        return self._regions[key]

    def _load_one(self, cx: int, cz: int) -> ChunkLoad:
        region = self._region(cx, cz)
        return self.add_chunk(cx, cz, region.read_chunk(cx, cz) if region is not None else None)

    def add_chunk(self, cx: int, cz: int, chunk: dict[str, Any] | None) -> ChunkLoad:
        """Take in a chunk's NBT (None: the save does not have it)."""
        out = ChunkLoad()
        if chunk is None:
            self.missing.add((cx, cz))
            return out
        self.loaded.add((cx, cz))
        out.chunks.append((cx, cz))
        new_movers: list[Pos] = []
        for raw in chunk.get("sections", []):
            sy = int(raw["Y"])
            states = raw.get("block_states", {})
            palette = [state_text(*palette_entry(e)) for e in states.get("palette", [])]
            if not palette or (len(palette) == 1 and palette[0] in AIR):
                continue
            done = np.zeros((16, 16, 16), bool)
            table = np.array([_kind(t) for t in palette], np.int8)
            moving = [i for i, t in enumerate(palette) if t.split("[", 1)[0] in MOVERS]
            if len(palette) == 1:
                self.sections[(cx, sy, cz)] = _Section(palette, None, table, done)
                cells: Any = np.argwhere(np.ones((16, 16, 16), bool)) if moving else []
            else:
                index = unpack_array(states.get("data", []), len(palette))
                self.sections[(cx, sy, cz)] = _Section(palette, index, table, done)
                cells = np.argwhere(np.isin(index, moving)) if moving else []
            for y, z, x in cells:
                new_movers.append((cx * 16 + int(x), sy * 16 + int(y), cz * 16 + int(z)))
        for entity in chunk.get("block_entities", []):
            out.block_entities[(int(entity["x"]), int(entity["y"]), int(entity["z"]))] = entity
        out.block_ticks.extend(chunk.get("block_ticks", []))
        if chunk.get("block_ticks"):
            self.ticked.add((cx, cz))
        if new_movers:
            self.movers.extend(new_movers)
            self.reach = _boxes(self.movers, PISTON_REACH)
        # This chunk and the chunks around it (they now know what lies beyond them);
        # with new movers also every section within their reach.
        columns = {(cx, cz)} | {(cx + dx, cz + dz) for dx, dz in _CHUNK_AROUND}
        for key in list(self.sections):
            if (key[0], key[2]) in columns or (new_movers and self._in_reach(key)):
                self._emit_section(key, out)
        return out

    # ------------------------------------------------------------------ deciding
    def _kinds(self, key: Section) -> np.ndarray:
        """The kinds of a section's blocks (16³; read-only)."""
        section = self.sections.get(key)
        if section is not None:
            return section.kinds
        cx, sy, cz = key
        open_ = (cx, cz) in self.loaded and sy >= MIN_SECTION
        return _FILLED[AIR_KIND if open_ else UNKNOWN_KIND]

    def _in_reach(self, key: Section) -> bool:
        lo = (key[0] * 16, key[1] * 16, key[2] * 16)
        return any(
            all(blo[a] <= lo[a] + 15 and lo[a] <= bhi[a] for a in range(3))
            for blo, bhi in self.reach
        )

    def _emit_section(self, key: Section, out: ChunkLoad) -> None:
        section = self.sections[key]
        if section.done.all():
            return
        cx, sy, cz = key
        grid = np.empty((18, 18, 18), np.int8)  # the section and its rim, [y, z, x]
        for dy in (-1, 0, 1):
            for dz in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    kinds = self._kinds((cx + dx, sy + dy, cz + dz))
                    grid[_RIM_DST[dy], _RIM_DST[dz], _RIM_DST[dx]] = kinds[
                        _RIM_SRC[dy], _RIM_SRC[dz], _RIM_SRC[dx]
                    ]
        core = grid[1:17, 1:17, 1:17]
        face_air = np.zeros((16, 16, 16), bool)
        near_build = np.zeros((16, 16, 16), bool)
        for dy in (-1, 0, 1):
            for dz in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if not (dx or dy or dz):
                        continue
                    shifted = grid[1 + dy : 17 + dy, 1 + dz : 17 + dz, 1 + dx : 17 + dx]
                    near_build |= shifted == BUILD_KIND
                    if abs(dx) + abs(dy) + abs(dz) == 1:
                        face_air |= shifted == AIR_KIND
        wanted = (core == BUILD_KIND) | ((core == TERRAIN_KIND) & (face_air | near_build))
        lo = (cx * 16, sy * 16, cz * 16)
        for blo, bhi in self.reach:
            a = [max(lo[i], blo[i]) - lo[i] for i in range(3)]
            b = [min(lo[i] + 15, bhi[i]) - lo[i] + 1 for i in range(3)]
            if all(a[i] < b[i] for i in range(3)):
                part = (slice(a[1], b[1]), slice(a[2], b[2]), slice(a[0], b[0]))
                wanted[part] |= core[part] != AIR_KIND
        new = wanted & ~section.done
        if not new.any():
            return
        section.done |= new
        for y, z, x in np.argwhere(new):
            text = section.text(y, z, x)
            out.blocks[(lo[0] + int(x), lo[1] + int(y), lo[2] + int(z))] = text
