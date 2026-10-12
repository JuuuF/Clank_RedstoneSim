"""Import an area of a Minecraft world into an editor document (doc/world-import.md).

The chunks within a radius of a point (default: the player) are read; every non-terrain
block is kept, terrain only where it matters: next to non-terrain blocks, within piston
reach (13 blocks) of anything that moves blocks, and where it shows (an exposed face).
Blocks the simulator does not model come in as foreign blocks; their ids are reported.
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from redsim.mcworld import nbt
from redsim.mcworld.chunk import AIR, palette_entry, section_blocks, state_text
from redsim.mcworld.region import RegionFile, region_of

Pos = tuple[int, int, int]

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


@dataclass
class SaveInfo:
    """What a save tells about itself (``level.dat``, the player, the seed)."""

    path: Path
    name: str
    data_version: int
    seed: int | None
    player_pos: tuple[float, float, float] | None
    player_rotation: tuple[float, float]  # yaw, pitch (the game's)
    spawn: tuple[int, int, int]
    game_time: int

    @property
    def regions(self) -> Path:
        """The overworld's region folder (26.x: under ``dimensions``; older: top level)."""
        modern = self.path / "dimensions" / "minecraft" / "overworld" / "region"
        return modern if modern.exists() else self.path / "region"


def read_save(path: Path) -> SaveInfo:
    data = nbt.read_file(path / "level.dat")["Data"]
    seed = None
    gen = path / "data" / "minecraft" / "world_gen_settings.dat"
    if gen.exists():
        seed = int(nbt.read_file(gen).get("data", {}).get("seed", 0))
    elif "WorldGenSettings" in data:
        seed = int(data["WorldGenSettings"].get("seed", 0))
    spawn_data = data.get("spawn", {})
    if "pos" in spawn_data:
        spawn = tuple(int(v) for v in spawn_data["pos"])
    else:
        spawn = (
            int(data.get("SpawnX", 0)),
            int(data.get("SpawnY", 64)),
            int(data.get("SpawnZ", 0)),
        )
    player_pos, rotation = None, (0.0, 0.0)
    player = data.get("Player")
    if player is None:
        files = sorted((path / "players" / "data").glob("*.dat")) or sorted(
            (path / "playerdata").glob("*.dat")
        )
        player = nbt.read_file(files[0]) if files else None
    if player is not None and "Pos" in player:
        player_pos = (float(player["Pos"][0]), float(player["Pos"][1]), float(player["Pos"][2]))
        rot = player.get("Rotation", [0.0, 0.0])
        rotation = (float(rot[0]), float(rot[1]))
    return SaveInfo(
        path=path,
        name=str(data.get("LevelName", path.name)),
        data_version=int(data.get("DataVersion", 0)),
        seed=seed,
        player_pos=player_pos,
        player_rotation=rotation,
        spawn=spawn,  # type: ignore[arg-type]
        game_time=int(data.get("Time", 0)),
    )


@dataclass
class ImportedArea:
    """Blocks (state text), block entities (NBT) and pending ticks of an area."""

    info: SaveInfo
    center: tuple[int, int]  # chunk
    radius: int  # chunks
    blocks: dict[Pos, str] = field(default_factory=dict)
    block_entities: dict[Pos, dict[str, Any]] = field(default_factory=dict)
    block_ticks: list[dict[str, Any]] = field(default_factory=list)
    skipped_terrain: int = 0
    chunks: int = 0
    #: Sections of one terrain block that were not decoded (they count as solid).
    solid_sections: set[tuple[int, int, int]] = field(default_factory=set)

    def foreign_ids(self, known: Iterable[str]) -> Counter[str]:
        """How often each block id the simulator does not know occurs."""
        known_ids = set(known)
        return Counter(
            text.split("[", 1)[0]
            for text in self.blocks.values()
            if text.split("[", 1)[0] not in known_ids
        )


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


def read_area(info: SaveInfo, center: tuple[int, int], radius: int) -> ImportedArea:
    """Read the chunks around ``center``. Sections made of one terrain block, surrounded by
    such sections and away from builds, are skipped without decoding (most of a flat or
    natural world); the rest is decoded and then pruned (``prune_terrain``)."""
    area = ImportedArea(info, center, radius)
    regions: dict[tuple[int, int], RegionFile | None] = {}
    solid: dict[tuple[int, int, int], str] = {}  # section → its one terrain block
    pending: list[tuple[int, int, dict[str, Any]]] = []  # sections to decode
    for cx, cz in chunks_around(center, radius):
        key = region_of(cx, cz)
        if key not in regions:
            path = info.regions / f"r.{key[0]}.{key[1]}.mca"
            regions[key] = RegionFile(path) if path.exists() else None
        region = regions[key]
        chunk = region.read_chunk(cx, cz) if region is not None else None
        if chunk is None:
            continue
        area.chunks += 1
        for section in chunk.get("sections", []):
            palette = section.get("block_states", {}).get("palette", [])
            if len(palette) == 1:
                text = state_text(*palette_entry(palette[0]))
                if text in AIR:
                    continue
                if text in TERRAIN:
                    solid[(cx, int(section["Y"]), cz)] = text
                    continue
            pending.append((cx, cz, section))
        for entity in chunk.get("block_entities", []):
            pos = (int(entity["x"]), int(entity["y"]), int(entity["z"]))
            area.block_entities[pos] = entity
        area.block_ticks.extend(chunk.get("block_ticks", []))
    for cx, cz, section in pending:
        for pos, text in section_blocks(section, cx, cz):
            area.blocks[pos] = text
    # Solid terrain sections matter only at a surface, near builds or in piston reach.
    special = [p for p, t in area.blocks.items() if t.split("[", 1)[0] not in TERRAIN]
    reach = _boxes([p for p in special if area.blocks[p].split("[", 1)[0] in MOVERS], PISTON_REACH)
    reach += _boxes(special, 1)
    skipped = 0
    for (cx, sy, cz), text in solid.items():
        area.solid_sections.add((cx, sy, cz))
        lo = (cx * 16, sy * 16, cz * 16)
        hi = (lo[0] + 15, lo[1] + 15, lo[2] + 15)
        touches = any(
            all(blo[a] <= hi[a] and lo[a] <= bhi[a] for a in range(3)) for blo, bhi in reach
        )
        neighbors = (
            (cx + 1, sy, cz),
            (cx - 1, sy, cz),
            (cx, sy + 1, cz),
            (cx, sy - 1, cz),
            (cx, sy, cz + 1),
            (cx, sy, cz - 1),
        )
        exposed = any(
            n not in solid and _loaded(area, (n[0] * 16, n[2] * 16))
            for n in neighbors
            if n[1] >= info_min_section(area)
        )
        if not touches and not exposed:
            skipped += 4096
            continue
        area.solid_sections.discard((cx, sy, cz))  # decoded: its blocks speak for it
        for i in range(4096):
            area.blocks[(lo[0] + (i & 15), lo[1] + (i >> 8), lo[2] + ((i >> 4) & 15))] = text
    prune_terrain(area)
    area.skipped_terrain += skipped
    return area


def info_min_section(area: ImportedArea) -> int:
    """The lowest section of the overworld (y = -64): nothing below it is ever air."""
    return -4


def prune_terrain(area: ImportedArea) -> None:
    """Drop terrain that cannot matter: buried (no exposed face), not next to a non-terrain
    block, and not within piston reach of a block mover."""
    blocks = area.blocks
    special = [pos for pos, text in blocks.items() if text.split("[", 1)[0] not in TERRAIN]
    near: set[Pos] = set()
    for x, y, z in special:  # neighbors of builds (support, conduction, observers)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    near.add((x + dx, y + dy, z + dz))
    movers = [pos for pos in special if blocks[pos].split("[", 1)[0] in MOVERS]
    reach = _boxes(movers, PISTON_REACH)
    keep: dict[Pos, str] = {}
    for pos, text in blocks.items():
        if text.split("[", 1)[0] not in TERRAIN or pos in near or _inside(pos, reach):
            keep[pos] = text
            continue
        x, y, z = pos
        for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            n = (x + dx, y + dy, z + dz)
            neighbor = blocks.get(n)
            if neighbor is None:
                if (n[0] >> 4, n[1] >> 4, n[2] >> 4) in area.solid_sections:
                    continue  # a skipped solid section: not air
                if _loaded(area, (x + dx, z + dz)):  # air (not just outside the area)
                    keep[pos] = text
                    break
            elif neighbor.split("[", 1)[0] not in TERRAIN:
                keep[pos] = text
                break
    area.skipped_terrain = len(blocks) - len(keep)
    area.blocks = keep


def _loaded(area: ImportedArea, column: tuple[int, int]) -> bool:
    cx, cz = column[0] >> 4, column[1] >> 4
    dx, dz = cx - area.center[0], cz - area.center[1]
    return dx * dx + dz * dz <= area.radius * area.radius + area.radius


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


def _inside(pos: Pos, boxes: list[tuple[Pos, Pos]]) -> bool:
    return any(all(lo[a] <= pos[a] <= hi[a] for a in range(3)) for lo, hi in boxes)


def player_chunk(info: SaveInfo) -> tuple[int, int]:
    x, _, z = info.player_pos if info.player_pos is not None else info.spawn
    return (math.floor(x) >> 4, math.floor(z) >> 4)


def known_texts(blocks: Iterable[str]) -> list[str]:
    """Palette entries as state texts (helper for tests)."""
    return [state_text(*palette_entry(entry)) for entry in blocks if entry not in AIR]


@dataclass
class OpenedWorld:
    """An imported area as an editor document, plus what the import found."""

    document: Any  # redsim.editor.document.Document
    area: ImportedArea
    foreign: Counter[str]
    ticks_imported: int


def open_world(path: Path, radius: int = 4, center: tuple[int, int] | None = None) -> OpenedWorld:
    """Import the chunks within ``radius`` of ``center`` (a chunk; default: the player's)
    as a document: blocks as they are (no updates, like the game loading a chunk), block
    entities from their NBT, pending scheduled ticks, and the camera at the player."""
    from redsim.editor.document import Document
    from redsim.sim.engine import Engine
    from redsim.world import blocks
    from redsim.world.tick_priority import TickPriority

    info = read_save(path)
    area = read_area(info, center if center is not None else player_chunk(info), radius)
    engine = Engine()
    level = engine.level
    states: dict[str, Any] = {}
    for pos, text in area.blocks.items():
        state = states.get(text)
        if state is None:
            state = states[text] = _state(text)
        level.blocks[pos] = state
    for pos, data in area.block_entities.items():
        state = level.blocks.get(pos)
        if state is None or not state.has_block_entity:
            continue
        entity = state.block.new_block_entity(pos, state)
        if entity is not None:
            entity.load_json(_plain(data))
            level.set_block_entity(entity)
    ticks = 0
    for tick in area.block_ticks:
        pos = (int(tick["x"]), int(tick["y"]), int(tick["z"]))
        state = level.blocks.get(pos)
        if (
            state is None
            or state.block.id != str(tick["i"])
            or state.block.id not in blocks.REGISTRY
        ):
            continue
        priority = TickPriority(max(-3, min(3, int(tick.get("p", 0)))))
        level.schedule_tick(pos, state.block, max(0, int(tick["t"])), priority)
        ticks += 1
    document = Document(engine=engine)
    x, y, z = info.player_pos if info.player_pos is not None else info.spawn
    yaw, pitch = info.player_rotation
    document.extra["camera"] = {
        "pivot": [x, y + 1.62, z],  # the player's eyes
        "distance": 10.0,
        "yaw": yaw,
        "pitch": max(15.0, pitch),
    }
    document.extra["minecraft_world"] = {
        "path": str(path),
        "name": info.name,
        "seed": info.seed,
        "center": list(area.center),
        "radius": radius,
    }
    document.dirty = False
    return OpenedWorld(document, area, area.foreign_ids(blocks.REGISTRY), ticks)


def _state(text: str) -> Any:
    """A block state from save text. Properties the simulator does not model for a known
    block (e.g. ``waterlogged``) are dropped; anything unreadable becomes foreign."""
    from redsim.world import blocks
    from redsim.world.blocks.foreign import foreign_block

    name, _, rest = text.partition("[")
    block = blocks.REGISTRY.get(name)
    if block is None:
        return blocks.parse_state(text)  # a foreign block
    props = dict(part.split("=", 1) for part in rest.rstrip("]").split(",") if "=" in part)
    known = {p.name for p in block.properties}
    kept = ",".join(f"{k}={v}" for k, v in props.items() if k in known)
    try:
        return blocks.parse_state(f"{name}[{kept}]" if kept else name)
    except (ValueError, StopIteration):
        return foreign_block(name, props).default_state


def _plain(value: Any) -> Any:
    """NBT values as plain JSON-like Python (what ``BlockEntity.load_json`` reads)."""
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_plain(v) for v in value]
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float):
        return float(value)
    return value
