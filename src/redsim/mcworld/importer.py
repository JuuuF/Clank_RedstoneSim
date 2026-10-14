"""Open a Minecraft world as an editor document (doc/world-import.md).

The chunks within a radius of a point (default: the player) are read first; more stream
in around the camera later (``stream_chunks``). Which blocks enter the document is
decided by ``mcworld.stream``: every non-terrain block, terrain only where it matters.
Blocks the simulator does not model come in as foreign blocks; their ids are reported.
"""

from __future__ import annotations

import json
import math
import time
from collections import Counter
from collections.abc import Container, Iterable
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

from redsim.mcworld import nbt
from redsim.mcworld.stream import ChunkLoad, WorldStream

Pos = tuple[int, int, int]


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


def player_chunk(info: SaveInfo) -> tuple[int, int]:
    x, _, z = info.player_pos if info.player_pos is not None else info.spawn
    return (math.floor(x) >> 4, math.floor(z) >> 4)


@dataclass
class OpenedWorld:
    """An opened save as an editor document, plus what the first load found."""

    document: Any  # redsim.editor.document.Document
    stream: WorldStream
    foreign: Counter[str]
    ticks_imported: int

    @property
    def info(self) -> SaveInfo:
        return self.stream.info


def foreign_ids(texts: Iterable[str]) -> Counter[str]:
    """How often each block id the simulator does not know occurs."""
    from redsim.world import blocks

    ids = (text.split("[", 1)[0] for text in texts)
    return Counter(i for i in ids if i not in blocks.REGISTRY)


def sign_texts(entities: dict[Pos, Any], texts: dict[Pos, str]) -> dict[str, list[str]]:
    """The front text of every sign among ``entities`` that the simulator keeps as a
    foreign block (hanging signs: no block entity), "x,y,z" → its 4 lines, kept as
    document data for the viewport (``extra["signs"]``). Standing and wall signs are
    simulated; their text is in their block entity."""
    from redsim.world import blocks

    out: dict[str, list[str]] = {}
    for pos, data in entities.items():
        block_id = texts.get(pos, "").split("[", 1)[0]
        if not block_id.endswith("_sign") or block_id in blocks.REGISTRY:
            continue  # simulated signs keep their text in their block entity
        front = data.get("front_text") or {}
        messages = front.get("messages") or [data.get(f"Text{i}", "") for i in range(1, 5)]
        lines = [_plain_text(message) for message in messages]
        if any(lines):
            out[f"{pos[0]},{pos[1]},{pos[2]}"] = lines
    return out


def _plain_text(message: Any) -> str:
    """A text component (JSON text, a plain string, or a compound) as plain text."""
    if isinstance(message, str):
        try:
            message = json.loads(message)
        except ValueError:
            return message
    if isinstance(message, str):
        return message
    if isinstance(message, list):
        return "".join(_plain_text(part) for part in message)
    if isinstance(message, dict):
        text = str(message.get("text", message.get("translate", "")))
        return text + "".join(_plain_text(part) for part in message.get("extra", []))
    return str(message)


def block_states(texts: dict[Pos, str]) -> dict[Pos, Any]:
    """Block states for save texts."""
    return {pos: _state(text) for pos, text in texts.items()}


def open_world(path: Path, radius: int = 4, center: tuple[int, int] | None = None) -> OpenedWorld:
    """Open a save as a document with the chunks within ``radius`` of ``center`` (a chunk;
    default: the player's): blocks as they are (no updates, like the game loading a
    chunk), block entities from their NBT, pending scheduled ticks, and the camera at the
    player. More chunks stream in later (``stream_chunks``)."""
    from redsim.editor.document import Document
    from redsim.sim.engine import Engine
    from redsim.world import blocks
    from redsim.world.tick_priority import TickPriority

    info = read_save(path)
    stream = WorldStream(info)
    load = stream.load(stream.wanted(center if center is not None else player_chunk(info), radius))
    engine = Engine()
    level = engine.level
    level.blocks.update(block_states(load.blocks))
    add_block_entities(level, load.block_entities, level.blocks)
    ticks = 0
    for tick in load.block_ticks:
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
    document.world = stream
    document.extra["signs"] = sign_texts(load.block_entities, load.blocks)
    x, y, z = info.player_pos if info.player_pos is not None else info.spawn
    yaw, pitch = info.player_rotation
    document.extra["camera"] = {
        "pivot": [x, y + 1.62, z],  # the player's eyes
        "distance": 10.0,
        "yaw": yaw,
        "pitch": max(15.0, pitch),
    }
    document.extra["minecraft_world"] = {"path": str(path), "name": info.name, "seed": info.seed}
    document.dirty = False
    return OpenedWorld(document, stream, foreign_ids(load.blocks.values()), ticks)


def attach_world(document: Any) -> WorldStream | None:
    """Connect a document saved from a Minecraft world (``extra["minecraft_world"]``) to
    its save again, so chunks stream in around the camera as before. The chunks it held
    are read again first (``WorldStream.reload``) without adding their blocks. None when
    the save is gone or is another world now (a different seed)."""
    world = document.extra.get("minecraft_world")
    if not isinstance(world, dict) or "path" not in world:
        return None
    path = Path(str(world["path"]))
    if not (path / "level.dat").exists():
        return None
    try:
        info = read_save(path)
    except (OSError, ValueError, KeyError):
        return None
    if world.get("seed") is not None and info.seed is not None and info.seed != world["seed"]:
        return None
    stream = WorldStream(info)
    stream.reload = [(int(cx), int(cz)) for cx, cz in world.get("chunks", [])]
    document.world = stream
    return stream


def stream_chunks(document: Any, center: tuple[int, int], radius: int, budget: float) -> int:
    """Load chunks of the document's world within ``radius`` of ``center`` (nearest
    first) for up to ``budget`` seconds; returns how many were loaded. Their blocks join
    the document as if they had always been there (``Document.add_world_blocks``);
    pending ticks of chunks loaded after opening are not imported."""
    stream: WorldStream | None = document.world
    if stream is None:
        return 0
    if stream.reload:  # a reopened document: its own chunks first
        stream.reload_some(budget)
        return 0
    wanted = stream.wanted(center, radius)
    if not wanted:
        return 0
    deadline = time.perf_counter() + budget
    load = ChunkLoad()
    for chunk in wanted:
        load.merge(stream.load([chunk]))
        if time.perf_counter() >= deadline:
            break
    if load.blocks:
        document.add_world_blocks(block_states(load.blocks), _plain(load.block_entities))
        document.extra.setdefault("signs", {}).update(sign_texts(load.block_entities, load.blocks))
    return len(load.chunks)


def add_block_entities(level: Any, entities: dict[Pos, Any], only: Container[Pos]) -> None:
    """Block entities from their saved NBT, for the blocks at positions in ``only``."""
    for pos, data in entities.items():
        state = level.blocks.get(pos)
        if pos not in only or state is None or not state.has_block_entity:
            continue
        entity = state.block.new_block_entity(pos, state)
        if entity is not None:
            entity.load_json(_plain(data))
            level.set_block_entity(entity)


@cache
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
