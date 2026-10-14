"""Saving an opened world back in Minecraft's format, as a copy of the save
(doc/world-import.md, phase 4, first version).

The save folder is copied (the original is never touched). Then every block the document
changed in a loaded chunk is written into its section (palette and packed indices, in the
forms 26.x writes itself: a bare id, or ``{id, properties}``), the block entities of the
chunk are written from the document (container contents, comparator outputs, …; other
keys of an entity the game stored are kept), and the chunk is marked for relighting
(``isLightOn`` 0, light arrays and heightmaps dropped: the game recomputes them on load).
Changed region files are rewritten with fresh sector allocation.

The document's pending scheduled ticks are written into the ``block_ticks`` of every
rewritten chunk (delay from now, priority, in the order they will run), replacing what the
save had there; a chunk with pending ticks is rewritten even without other changes. Fluid
ticks stay as the save had them.

Not written: blocks outside the loaded chunks and blocks of sections the save does not
have.
"""

from __future__ import annotations

import shutil
import struct
import time
import zlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from redsim.mcworld import nbt
from redsim.mcworld.chunk import AIR, pack_indices, palette_entry, state_text, unpack_indices
from redsim.mcworld.region import EXTERNAL, SECTOR, ZLIB, RegionFile, region_of

Pos = tuple[int, int, int]
AIR_TEXT = "minecraft:air"


@dataclass
class WriteReport:
    target: Path
    blocks: int = 0  # blocks written that differ from the save
    chunks: int = 0  # chunks rewritten
    regions: int = 0
    outside: int = 0  # changed blocks outside the loaded chunks (not written)
    skipped_sections: set[tuple[int, int, int]] = field(default_factory=set)


def save_world_copy(document: Any, target: Path) -> WriteReport:
    """Copy the document's save to ``target`` and write the document's blocks into it."""
    from redsim.mcworld.importer import _state

    stream = document.world
    if stream is None:
        raise ValueError("This document was not opened from a Minecraft world.")
    if target.exists():
        raise ValueError(f"{target} already exists.")
    shutil.copytree(stream.info.path, target, ignore=shutil.ignore_patterns("session.lock"))
    report = WriteReport(target)
    level = document.level
    changes: dict[tuple[int, int], dict[Pos, str]] = {}  # chunk → pos → new text

    def same(original: str, state: Any) -> bool:
        if state is None:
            return original in AIR
        return original not in AIR and _state(original) is state

    for pos, state in level.blocks.items():
        x, y, z = pos
        section = stream.sections.get((x >> 4, y >> 4, z >> 4))
        if section is None:
            if (x >> 4, z >> 4) not in stream.loaded:
                report.outside += 1
                continue
            original = AIR_TEXT  # an all-air section the save leaves out
        else:
            original = section.text(y & 15, z & 15, x & 15)
        if not same(original, state):
            changes.setdefault((x >> 4, z >> 4), {})[pos] = _text(state)
    for (cx, sy, cz), section in stream.sections.items():  # removed blocks
        for y, z, x in np.argwhere(section.done):
            pos = (cx * 16 + int(x), sy * 16 + int(y), cz * 16 + int(z))
            if pos not in level.blocks and section.text(y, z, x) not in AIR:
                changes.setdefault((cx, cz), {})[pos] = AIR_TEXT
    # Chunks with block entities are rewritten too: their contents may have changed.
    for pos in level.block_entities:
        if (pos[0] >> 4, pos[2] >> 4) in stream.loaded:
            changes.setdefault((pos[0] >> 4, pos[2] >> 4), {})
    # And chunks with pending ticks now or in the save (ticks that have run must go).
    ticks: dict[tuple[int, int], list[Any]] = {}
    for tick in level.block_ticks.pending():
        chunk = (tick.pos[0] >> 4, tick.pos[2] >> 4)
        if chunk in stream.loaded:
            ticks.setdefault(chunk, []).append(tick)
            changes.setdefault(chunk, {})
    for chunk in stream.ticked:
        changes.setdefault(chunk, {})
    by_region: dict[tuple[int, int], list[tuple[int, int]]] = {}
    for chunk in changes:
        by_region.setdefault(region_of(*chunk), []).append(chunk)
    regions = _region_dir(stream.info.path, target, stream.info.regions)
    for (rx, rz), chunks in by_region.items():
        path = regions / f"r.{rx}.{rz}.mca"
        if not path.exists():
            continue
        new_payloads: dict[tuple[int, int], bytes] = {}
        region = RegionFile(path)
        for cx, cz in chunks:
            root = region.read_chunk(cx, cz)
            if root is None:
                continue
            written = _apply(root, cx, cz, changes[(cx, cz)], level, report)
            root["block_ticks"] = nbt.NbtList(
                [_tick_entry(tick, level.game_time) for tick in ticks.get((cx, cz), [])],
                nbt.COMPOUND,
            )
            report.blocks += written
            new_payloads[(cx, cz)] = zlib.compress(nbt.dumps(root))
        _rewrite_region(region, new_payloads)
        report.chunks += len(new_payloads)
        report.regions += 1
    _rename(target)
    return report


def _tick_entry(tick: Any, now: int) -> dict[str, Any]:
    """A pending tick as the game saves it (``SavedTick``): block id, position, delay from
    now and priority."""
    return {
        "i": tick.block_id,
        "x": nbt.Int(tick.pos[0]),
        "y": nbt.Int(tick.pos[1]),
        "z": nbt.Int(tick.pos[2]),
        "t": nbt.Int(max(0, tick.trigger_tick - now)),
        "p": nbt.Int(int(tick.priority.value)),
    }


def _region_dir(source: Path, target: Path, regions: Path) -> Path:
    return target / regions.relative_to(source)


def _text(state: Any) -> str:
    return AIR_TEXT if state is None else repr(state)


def _entry(text: str) -> Any:
    """A palette entry in the forms 26.x writes: a bare id or ``{id, properties}``."""
    name, _, rest = text.partition("[")
    props = dict(p.split("=", 1) for p in rest.rstrip("]").split(",") if "=" in p)
    return {"id": name, "properties": props} if props else name


def _apply(
    root: dict[str, Any],
    cx: int,
    cz: int,
    changes: dict[Pos, str],
    level: Any,
    report: WriteReport,
) -> int:
    """Write ``changes`` and the block entities of the chunk into its NBT."""
    sections = {int(s["Y"]): s for s in root.get("sections", [])}
    by_section: dict[int, dict[int, str]] = {}
    for (x, y, z), text in changes.items():
        by_section.setdefault(y >> 4, {})[(y & 15) * 256 + (z & 15) * 16 + (x & 15)] = text
    written = 0
    for sy, edits in by_section.items():
        section = sections.get(sy)
        if section is None:
            report.skipped_sections.add((cx, sy, cz))
            continue
        states = section.setdefault("block_states", {})
        palette = [state_text(*palette_entry(e)) for e in states.get("palette", [])] or [AIR_TEXT]
        if len(palette) == 1:
            texts = [palette[0]] * 4096
        else:
            indices = unpack_indices(list(states.get("data", [])), len(palette))
            texts = [palette[i] for i in indices]
        for index, text in edits.items():
            texts[index] = text
        written += len(edits)
        order: dict[str, int] = {}
        indices = [order.setdefault(text, len(order)) for text in texts]
        entries = [_entry(text) for text in order]
        if all(isinstance(e, str) for e in entries):
            states["palette"] = nbt.NbtList(entries, nbt.STRING)
        else:  # a mixed list is a compound list, bare ids wrapped as {"": id} (26.x)
            wrapped = [{"": e} if isinstance(e, str) else e for e in entries]
            states["palette"] = nbt.NbtList(wrapped, nbt.COMPOUND)
        if len(order) == 1:
            states.pop("data", None)
        else:
            states["data"] = nbt.NbtArray(pack_indices(indices, len(order)), nbt.LONG_ARRAY)
        section.pop("BlockLight", None)
        section.pop("SkyLight", None)
    # Block entities: the document's (keeping keys the game stored that it does not model);
    # entries at blocks that no longer have one go.
    old = {(int(e["x"]), int(e["y"]), int(e["z"])): e for e in root.get("block_entities", [])}
    entities = [
        entry
        for pos, entry in old.items()
        # Kept as the save had it unless the document has this entity (written below)
        # or the block there changed (a removed or replaced block loses its entity).
        if pos not in level.block_entities and pos not in changes
    ]
    for pos, entity in level.block_entities.items():
        if (pos[0] >> 4, pos[2] >> 4) != (cx, cz):
            continue
        entry = dict(old.get(pos, {}))
        entry.update(_nbt(entity.to_json()))
        entry.update(
            {
                "id": f"minecraft:{entity.type_id}",
                "x": nbt.Int(pos[0]),
                "y": nbt.Int(pos[1]),
                "z": nbt.Int(pos[2]),
            }
        )
        entities.append(entry)
    root["block_entities"] = nbt.NbtList(entities, nbt.COMPOUND)
    if written:
        root["isLightOn"] = nbt.Byte(0)  # the game relights the chunk
        root.pop("Heightmaps", None)  # recomputed when missing
    return written


def _nbt(value: Any, key: str = "") -> Any:
    """Plain JSON-like data (``BlockEntity.to_json``) as typed NBT, like the game writes."""
    if isinstance(value, dict):
        return {k: _nbt(v, k) for k, v in value.items()}
    if isinstance(value, list):
        items = [_nbt(v) for v in value]
        element = nbt.tag_of(items[0]) if items else nbt.END
        return nbt.NbtList(items, element)
    if isinstance(value, bool):
        return nbt.Byte(int(value))
    if isinstance(value, int):
        return nbt.Byte(value) if key == "Slot" else nbt.Int(value)
    if isinstance(value, float):
        return nbt.Float(value)
    return value


def _rewrite_region(region: RegionFile, payloads: dict[tuple[int, int], bytes]) -> None:
    """Rewrite a region file: changed chunks get their new payloads, the others are copied;
    sectors are allocated afresh from the header on."""
    chunks: dict[int, tuple[int, bytes, int]] = {}  # index → (compression, payload, time)
    for i, location in enumerate(region.locations):
        if location:
            raw = region.read_raw(i & 31, i >> 5)
            if raw is not None:
                chunks[i] = (raw[0], raw[1], region.timestamps[i])
    now = int(time.time())
    for (cx, cz), payload in payloads.items():
        chunks[RegionFile.index(cx, cz)] = (ZLIB, payload, now)
    locations = [0] * 1024
    timestamps = [0] * 1024
    body = bytearray()
    sector = 2
    for index in sorted(chunks):
        compression, payload, stamp = chunks[index]
        data = struct.pack(">IB", len(payload) + 1, compression & ~EXTERNAL) + payload
        count = -(-len(data) // SECTOR)
        if count > 255:
            raise ValueError("a chunk is larger than 1 MiB; not supported yet")
        body += data.ljust(count * SECTOR, b"\0")
        locations[index] = (sector << 8) | count
        timestamps[index] = stamp
        sector += count
    header = struct.pack(">1024I", *locations) + struct.pack(">1024I", *timestamps)
    region.path.write_bytes(header + bytes(body))


def _rename(target: Path) -> None:
    """Name the copy after its folder in the game's world list (``LevelName``)."""
    path = target / "level.dat"
    try:
        root = nbt.read_file(path)
        root.setdefault("Data", {})["LevelName"] = target.name
        nbt.write_file(path, root)
    except (OSError, ValueError, KeyError):
        pass
