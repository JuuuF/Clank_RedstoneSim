"""Schematic files: Litematica (``.litematic``), Sponge/WorldEdit (``.schem``, versions 1–3)
and the game's structure files (``.nbt``, structure blocks and ``/place template``).

A schematic becomes a ``Prefab`` (the editor's clipboard and prefab library): its blocks
relative to the minimum corner, with block-entity data in the game's layout (what
``BlockEntity.load_json`` reads). Blocks the simulator does not model come in as foreign
blocks; properties a simulated block does not have (``waterlogged`` on a lever) are
dropped, as when opening a world. Cells a schematic leaves out (a structure's "structure
void", the space between several boxes) are left out of the prefab too, so pasting keeps
what is there. Entities and pending ticks are not read.

Writing goes the other way: every cell of the prefab (air included; left-out cells as
structure void in ``.nbt`` and air elsewhere), block entities typed like the game writes
them, and the game's data version (26.3: 5023).
"""

from __future__ import annotations

import gzip
import time
from pathlib import Path
from typing import Any

from redsim.editor.clipboard import Prefab
from redsim.mcworld import nbt
from redsim.mcworld.chunk import palette_entry, state_text

#: ``version.json`` ``world_version`` of 26.3.
DATA_VERSION = 5023
#: Litematica's file version for this game version (``LitematicaSchematic.SCHEMATIC_VERSION``).
LITEMATICA_VERSION = 7
FORMATS = {
    ".litematic": "Litematica schematic",
    ".schem": "Sponge schematic (WorldEdit)",
    ".nbt": "Structure file (structure blocks)",
}
#: File types a schematic library lists.
SUFFIXES = (".litematic", ".schem", ".schematic", ".nbt")
FILE_FILTER = (
    "Schematics (*.litematic *.schem *.schematic *.nbt);;"
    "Litematica (*.litematic);;Sponge / WorldEdit (*.schem);;Structure files (*.nbt)"
)

Entry = tuple[int, int, int, str, dict[str, Any] | None]


# ---------------------------------------------------------------------- helpers
def _state(text: str) -> str:
    """Save text → the simulator's state text (unknown properties of known blocks go)."""
    from redsim.mcworld.importer import state_from_text

    return repr(state_from_text(text))


def _entity_data(raw: dict[str, Any], drop: tuple[str, ...]) -> dict[str, Any]:
    from redsim.mcworld.importer import plain_nbt

    return {k: v for k, v in plain_nbt(raw).items() if k not in drop}


def _palette_compound(text: str) -> dict[str, Any]:
    """``id[k=v,…]`` → ``{id, properties}``, as 26.3 writes block states
    (``NbtUtils.writeBlockState``; older versions wrote ``Name``/``Properties``, which
    the game only reads through its data fixer, for older data versions)."""
    name, _, rest = text.partition("[")
    entry: dict[str, Any] = {"id": name}
    props = dict(part.split("=", 1) for part in rest.rstrip("]").split(",") if "=" in part)
    if props:
        entry["properties"] = props
    return entry


def _entity_id(text: str) -> str | None:
    """The block-entity id the game uses for a state (``minecraft:chest`` …), if any."""
    from redsim.world import blocks

    state = blocks.parse_state(text)
    if not state.has_block_entity:
        return None
    entity = state.block.new_block_entity((0, 0, 0), state)
    return f"minecraft:{entity.type_id}" if entity is not None else None


def _typed(data: dict[str, Any]) -> dict[str, Any]:
    from redsim.mcworld.writer import typed_nbt

    typed = typed_nbt(data)
    assert isinstance(typed, dict)
    return typed


def _full(prefab: Prefab) -> dict[tuple[int, int, int], tuple[str, dict[str, Any] | None]]:
    return {(dx, dy, dz): (text, data) for dx, dy, dz, text, data in prefab.blocks}


def _sorted(entries: list[Entry]) -> list[Entry]:
    return sorted(entries, key=lambda e: (e[2], e[1], e[0]))  # /clone order: z, y, x


def _signed64(value: int) -> int:
    return value - (1 << 64) if value >= 1 << 63 else value


# ---------------------------------------------------------------------- reading
def read_schematic_metadata(path: Path) -> dict[str, str]:
    """The name, author and description a schematic carries (Litematica and Sponge
    files have a ``Metadata`` compound; structure files have none)."""
    raw = nbt.decompress(path.read_bytes())
    _, root = nbt.loads(raw)
    meta = root.get("Metadata") or root.get("Schematic", {}).get("Metadata") or {}
    out = {}
    for key in ("Name", "Author", "Description"):
        value = meta.get(key) if isinstance(meta, dict) else None
        if isinstance(value, str) and value.strip():
            out[key.lower()] = value.strip()
    return out


def read_schematic(path: Path) -> Prefab:
    """A schematic file as a prefab named after the file."""
    raw = nbt.decompress(path.read_bytes())
    _, root = nbt.loads(raw)
    name = path.name.split(".")[0]
    suffix = path.suffix.lower()
    if suffix == ".litematic" or "Regions" in root:
        return _read_litematic(root, name)
    if suffix in (".schem", ".schematic") or "Schematic" in root or "Palette" in root:
        return _read_sponge(root, name)
    if "palette" in root or "palettes" in root:
        return _read_structure(root, name)
    raise ValueError(f"{path.name} is not a schematic this simulator reads")


def _read_structure(root: dict[str, Any], name: str) -> Prefab:
    size = tuple(int(v) for v in root["size"])
    palette_raw = root.get("palette") or root["palettes"][0]
    palette = [_state(state_text(*palette_entry(e))) for e in palette_raw]
    entries: list[Entry] = []
    for block in root.get("blocks", []):
        x, y, z = (int(v) for v in block["pos"])
        data = _entity_data(block["nbt"], ("id",)) if "nbt" in block else None
        entries.append((x, y, z, palette[int(block["state"])], data))
    return Prefab(name, size, _sorted(entries))  # type: ignore[arg-type]


def _varints(data: list[int], count: int) -> list[int]:
    values, value, shift = [], 0, 0
    for byte in data:
        byte &= 0xFF
        value |= (byte & 0x7F) << shift
        if byte & 0x80:
            shift += 7
            continue
        values.append(value)
        value, shift = 0, 0
        if len(values) == count:
            break
    return values


def _read_sponge(root: dict[str, Any], name: str) -> Prefab:
    data = root.get("Schematic", root)
    width, height, length = (int(data[k]) & 0xFFFF for k in ("Width", "Height", "Length"))
    version = int(data.get("Version", 2))
    if version >= 3:
        blocks = data.get("Blocks", {})
        palette_map, packed = blocks.get("Palette", {}), blocks.get("Data", [])
        raw_entities = blocks.get("BlockEntities", [])
    else:
        palette_map, packed = data.get("Palette", {}), data.get("BlockData", [])
        raw_entities = data.get("BlockEntities", data.get("TileEntities", []))
    palette = {int(index): _state(text) for text, index in palette_map.items()}
    entities: dict[tuple[int, int, int], dict[str, Any]] = {}
    for raw in raw_entities:
        x, y, z = (int(v) for v in raw["Pos"])
        fields = raw.get("Data", raw) if version >= 3 else raw
        entities[(x, y, z)] = _entity_data(fields, ("Id", "id", "Pos", "x", "y", "z"))
    indices = _varints(list(packed), width * height * length)
    entries: list[Entry] = []
    for i, index in enumerate(indices):
        x = i % width
        z = (i // width) % length
        y = i // (width * length)
        entries.append((x, y, z, palette[index], entities.get((x, y, z))))
    return Prefab(name, (width, height, length), _sorted(entries))


def _unpack_tight(longs: list[int], bits: int, count: int) -> list[int]:
    """Litematica's bit array: values packed back to back, spanning longs."""
    mask = (1 << bits) - 1
    words = [v & 0xFFFFFFFFFFFFFFFF for v in longs]
    out = []
    for i in range(count):
        start = i * bits
        word, offset = divmod(start, 64)
        value = words[word] >> offset
        if offset + bits > 64:
            value |= words[word + 1] << (64 - offset)
        out.append(value & mask)
    return out


def _read_litematic(root: dict[str, Any], name: str) -> Prefab:
    regions = []
    for region in root["Regions"].values():
        pos = region["Position"]
        size = region["Size"]
        lo, extent = [], []
        for axis in "xyz":
            p, s = int(pos[axis]), int(size[axis])
            lo.append(p + s + 1 if s < 0 else p)
            extent.append(abs(s))
        regions.append((region, lo, extent))
    low = [min(r[1][i] for r in regions) for i in range(3)]
    high = [max(r[1][i] + r[2][i] - 1 for r in regions) for i in range(3)]
    entries: dict[tuple[int, int, int], Entry] = {}
    for region, lo, (sx, sy, sz) in regions:
        palette = [_state(state_text(*palette_entry(e))) for e in region["BlockStatePalette"]]
        bits = max(2, (len(palette) - 1).bit_length())
        values = _unpack_tight(list(region["BlockStates"]), bits, sx * sy * sz)
        entities = {
            (int(e["x"]), int(e["y"]), int(e["z"])): _entity_data(e, ("id", "x", "y", "z"))
            for e in region.get("TileEntities", [])
        }
        for i, index in enumerate(values):
            x = i % sx
            z = (i // sx) % sz
            y = i // (sx * sz)
            offset = (lo[0] + x - low[0], lo[1] + y - low[1], lo[2] + z - low[2])
            entries[offset] = (*offset, palette[index], entities.get((x, y, z)))
    size = (high[0] - low[0] + 1, high[1] - low[1] + 1, high[2] - low[2] + 1)
    return Prefab(name, size, _sorted(list(entries.values())))


# ---------------------------------------------------------------------- writing
def write_schematic(path: Path, prefab: Prefab, author: str = "redsim") -> None:
    """Write ``prefab`` in the format of ``path``'s suffix."""
    suffix = path.suffix.lower()
    if suffix == ".litematic":
        root, name = _litematic(prefab, author), ""
    elif suffix in (".schem", ".schematic"):
        root, name = _sponge(prefab, author), ""
    elif suffix == ".nbt":
        root, name = _structure(prefab, author), ""
    else:
        raise ValueError(f"unknown schematic format {path.suffix!r} (use {', '.join(FORMATS)})")
    path.write_bytes(gzip.compress(nbt.dumps(root, name)))


def _structure(prefab: Prefab, author: str) -> dict[str, Any]:
    palette: dict[str, int] = {}
    blocks = []
    for dx, dy, dz, text, data in prefab.blocks:  # left-out cells: structure void
        index = palette.setdefault(text, len(palette))
        entry: dict[str, Any] = {
            "state": nbt.Int(index),
            "pos": nbt.NbtList([nbt.Int(dx), nbt.Int(dy), nbt.Int(dz)], nbt.INT),
        }
        entity_id = _entity_id(text)
        if entity_id is not None:
            entry["nbt"] = {**_typed(data or {}), "id": entity_id}
        blocks.append(entry)
    return {
        "DataVersion": nbt.Int(DATA_VERSION),
        "author": author,
        "size": nbt.NbtList([nbt.Int(v) for v in prefab.size], nbt.INT),
        "palette": nbt.NbtList([_palette_compound(text) for text in palette], nbt.COMPOUND),
        "blocks": nbt.NbtList(blocks, nbt.COMPOUND),
        "entities": nbt.NbtList([], nbt.COMPOUND),
    }


def _sponge(prefab: Prefab, author: str) -> dict[str, Any]:
    """Sponge schematic version 3 (WorldEdit 7.3+): left-out cells become air."""
    width, height, length = prefab.size
    cells = _full(prefab)
    palette: dict[str, int] = {"minecraft:air": 0}
    data: list[int] = []
    entities = []
    for y in range(height):
        for z in range(length):
            for x in range(width):
                text, entity = cells.get((x, y, z), ("minecraft:air", None))
                index = palette.setdefault(text, len(palette))
                while index >= 0x80:
                    data.append((index & 0x7F) | 0x80)
                    index >>= 7
                data.append(index)
                entity_id = _entity_id(text)
                if entity_id is not None:
                    entities.append(
                        {
                            "Pos": nbt.NbtArray([x, y, z], nbt.INT_ARRAY),
                            "Id": entity_id,
                            "Data": _typed(entity or {}),
                        }
                    )
    signed = [b - 256 if b > 127 else b for b in data]
    return {
        "Schematic": {
            "Version": nbt.Int(3),
            "DataVersion": nbt.Int(DATA_VERSION),
            "Metadata": {"Name": prefab.name, "Author": author, "Date": nbt.Long(_now_ms())},
            "Width": nbt.Short(width),
            "Height": nbt.Short(height),
            "Length": nbt.Short(length),
            "Offset": nbt.NbtArray([0, 0, 0], nbt.INT_ARRAY),
            "Blocks": {
                "Palette": {text: nbt.Int(index) for text, index in palette.items()},
                "Data": nbt.NbtArray(signed, nbt.BYTE_ARRAY),
                "BlockEntities": nbt.NbtList(entities, nbt.COMPOUND),
            },
        }
    }


def _litematic(prefab: Prefab, author: str) -> dict[str, Any]:
    width, height, length = prefab.size
    cells = _full(prefab)
    palette: dict[str, int] = {"minecraft:air": 0}
    values: list[int] = []
    entities = []
    for y in range(height):
        for z in range(length):
            for x in range(width):
                text, entity = cells.get((x, y, z), ("minecraft:air", None))
                values.append(palette.setdefault(text, len(palette)))
                entity_id = _entity_id(text)
                if entity_id is not None:
                    entities.append(
                        {
                            **_typed(entity or {}),
                            "id": entity_id,
                            "x": nbt.Int(x),
                            "y": nbt.Int(y),
                            "z": nbt.Int(z),
                        }
                    )
    bits = max(2, (len(palette) - 1).bit_length())
    words = [0] * ((len(values) * bits + 63) // 64)
    for i, value in enumerate(values):
        start = i * bits
        word, offset = divmod(start, 64)
        words[word] |= (value << offset) & 0xFFFFFFFFFFFFFFFF
        if offset + bits > 64:
            words[word + 1] |= value >> (64 - offset)
    now = nbt.Long(_now_ms())
    size = {"x": nbt.Int(width), "y": nbt.Int(height), "z": nbt.Int(length)}
    region = {
        "Position": {"x": nbt.Int(0), "y": nbt.Int(0), "z": nbt.Int(0)},
        "Size": size,
        "BlockStatePalette": nbt.NbtList(
            [_palette_compound(text) for text in palette], nbt.COMPOUND
        ),
        "BlockStates": nbt.NbtArray([_signed64(w) for w in words], nbt.LONG_ARRAY),
        "TileEntities": nbt.NbtList(entities, nbt.COMPOUND),
        "Entities": nbt.NbtList([], nbt.COMPOUND),
        "PendingBlockTicks": nbt.NbtList([], nbt.COMPOUND),
        "PendingFluidTicks": nbt.NbtList([], nbt.COMPOUND),
    }
    return {
        "Version": nbt.Int(LITEMATICA_VERSION),
        "SubVersion": nbt.Int(1),
        "MinecraftDataVersion": nbt.Int(DATA_VERSION),
        "Metadata": {
            "Name": prefab.name,
            "Author": author,
            "Description": "",
            "RegionCount": nbt.Int(1),
            "TotalBlocks": nbt.Int(prefab.non_air_count),
            "TotalVolume": nbt.Int(width * height * length),
            "EnclosingSize": dict(size),
            "TimeCreated": now,
            "TimeModified": now,
        },
        "Regions": {prefab.name or "main": region},
    }


def _now_ms() -> int:
    return int(time.time() * 1000)
