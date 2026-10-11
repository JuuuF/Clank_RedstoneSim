"""Run the same scenario in the simulator and in the sandboxed 26.3 server, tick by tick.

A scenario is built only from ``/setblock`` commands (replace mode, optionally with
block-entity data), which the simulator mirrors exactly (``Action("setblock", ...)`` ports
``SetBlockCommand``). Inputs are applied
between ticks, like any command or player action. After every tick, the full block state of
each watched position in the simulator is checked in the game with ``execute if block``;
mismatches are resolved property by property so the report shows the real state.

Terrain: the superflat sandbox world has bedrock at y=-64, dirt at -63/-62 and grass at -61.
Each scenario gets a stone floor at y=-61 under its area (``fill ... strict``, no updates);
the simulator builds the same columns, so neighbor queries see identical blocks.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from redsim.core.pos import Pos
from redsim.sim.engine import Action, Engine
from redsim.world import blocks
from redsim.world.block import BlockState
from tools.gameserver.server import GameServer

FLOOR_Y = -61
RESULTS_DIR = Path(__file__).resolve().parents[2] / "experiments" / "results"


@dataclass
class Scenario:
    """Positions are relative: ``(x, y, z)`` with y=1 the first layer above the floor."""

    name: str
    description: str
    size: tuple[int, int]  # floor footprint (x, z) starting at relative (0, 0)
    #: ``(rel, state)`` or ``(rel, state, nbt)``; ``nbt`` is the simulator's block-entity
    #: JSON (``BlockEntity.to_json``), translated for the game by ``game_nbt``.
    setup: list[tuple[Any, ...]]
    watch: list[Pos]
    ticks: int
    inputs: dict[int, list[tuple[Pos, str]]] = field(default_factory=dict)
    #: Region commands after ``t`` ticks (applied after ``inputs``):
    #: ``("fill", rel_a, rel_b, state)``, ``("clone", rel_a, rel_b, rel_destination)``, or
    #: ``("clone_move" | "clone_force", rel_a, rel_b, rel_destination)`` (``replace move/force``),
    #: ``("clone_strict", …)`` (prefab paste, ``/clone … strict``), ``("clone_move_strict", …)``,
    #: or ``("item", rel, slot, (item_id | None, count))`` (``/item replace block``).
    #: The cloned area must have no pending scheduled ticks (the simulator's paste does
    #: not copy ticks, ``/clone`` does).
    commands: dict[int, list[tuple[Any, ...]]] = field(default_factory=dict)
    #: Also compare barrel contents (hopper contents and cooldowns are always compared).
    watch_items: bool = False

    def fingerprint(self) -> str:
        """Hash of everything that determines the run (recordings go stale if it changes)."""
        parts: list[Any] = [
            self.size,
            self.setup,
            self.watch,
            self.ticks,
            sorted(self.inputs.items()),
        ]
        if self.commands:
            parts.append(sorted(self.commands.items()))
        if self.watch_items:
            parts.append("watch_items")
        payload = json.dumps(parts)
        return hashlib.sha256(payload.encode()).hexdigest()[:16]


@dataclass
class TickRecord:
    tick: int
    sim: dict[str, str]
    game: dict[str, str]

    @property
    def mismatches(self) -> list[str]:
        return [key for key in self.sim if self.sim[key] != self.game.get(key)]


def absolute(origin: Pos, rel: Pos) -> Pos:
    return (origin[0] + rel[0], FLOOR_Y + rel[1], origin[2] + rel[2])


# ---------------------------------------------------------------- simulator side
#: Superflat terrain mirrored around each area: pushes can drag the ground (slime and honey
#: stick to it), and a push line of up to 12 blocks must see the same blocks as the game.
TERRAIN_RING = 16


def build_terrain(engine: Engine, origin: Pos, size: tuple[int, int], margin: int = 2) -> None:
    """The prepared stone area (``prepare_area``) inside the default superflat world
    (bedrock, dirt, dirt, grass) as far as any push could reach."""
    level = engine.level
    ring = margin + TERRAIN_RING
    for dx in range(-ring, size[0] + ring):
        for dz in range(-ring, size[1] + ring):
            x, z = origin[0] + dx, origin[2] + dz
            prepared = -margin <= dx < size[0] + margin and -margin <= dz < size[1] + margin
            level.blocks[(x, -64, z)] = blocks.BEDROCK.default_state
            if prepared:
                level.blocks[(x, -63, z)] = blocks.STONE.default_state
                level.blocks[(x, -62, z)] = blocks.STONE.default_state
                level.blocks[(x, FLOOR_Y, z)] = blocks.STONE.default_state
            else:
                level.blocks[(x, -63, z)] = blocks.DIRT.default_state
                level.blocks[(x, -62, z)] = blocks.DIRT.default_state
                level.blocks[(x, FLOOR_Y, z)] = blocks.GRASS_BLOCK.default_state


def run_sim(scenario: Scenario, origin: Pos, start_time: int) -> list[dict[str, str]]:
    engine = Engine()
    engine.level.game_time = start_time
    build_terrain(engine, origin, scenario.size)
    for rel, state, *nbt in scenario.setup:
        payload = {"nbt": nbt[0]} if nbt else None
        engine.apply(Action("setblock", absolute(origin, rel), state, payload=payload))
    frames = [observe_sim(engine, scenario, origin)]
    for tick in range(scenario.ticks):
        for rel, state in scenario.inputs.get(tick, []):
            engine.apply(Action("setblock", absolute(origin, rel), state))
        for command in scenario.commands.get(tick, []):
            engine.apply(sim_command(engine, origin, command))
        engine.run_tick()
        frames.append(observe_sim(engine, scenario, origin))
    return frames


def sim_command(engine: Engine, origin: Pos, command: tuple[Any, ...]) -> Action:
    from redsim.editor.clipboard import Prefab, Region

    if command[0] == "item":
        _, rel, slot, (item, count) = command
        payload = {"slot": slot, "item": item, "count": count}
        return Action("container_item", absolute(origin, rel), payload=payload)
    if command[0] == "hit":  # a projectile straight down onto the top center: strength 15
        _, rel, projectile = command
        payload = {"strength": 15, "ticks": 20 if projectile == "arrow" else 8}
        return Action("projectile_hit", absolute(origin, rel), payload=payload)
    kind, rel_a, rel_b, last = command
    a, b = absolute(origin, rel_a), absolute(origin, rel_b)
    if kind == "fill":
        return Action("fill", a, last, payload={"to": list(b)})
    if kind in ("clone_move", "clone_force", "clone_move_strict"):
        mode = kind.removeprefix("clone_").removesuffix("_strict")
        payload = {"begin": list(a), "end": list(b), "mode": mode, "strict": "strict" in kind}
        return Action("clone_region", absolute(origin, last), payload=payload)
    prefab = Prefab.capture(engine.level, Region.from_corners(a, b))
    payload = {**prefab.payload(), "strict": kind == "clone_strict"}
    return Action("clone", absolute(origin, last), payload=payload)


def game_command(origin: Pos, command: tuple[Any, ...]) -> str:
    if command[0] == "hit":
        _, rel, projectile = command
        x, y, z = absolute(origin, rel)
        return f"summon {projectile} {x + 0.5} {y + 1.5} {z + 0.5} {{Motion:[0.0,-3.0,0.0]}}"
    if command[0] == "item":
        _, rel, slot, (item, count) = command
        x, y, z = absolute(origin, rel)
        stack = f"{item or 'minecraft:air'} {count}"
        return f"item replace block {x} {y} {z} container.{slot} with {stack}"
    kind, rel_a, rel_b, last = command
    a, b = absolute(origin, rel_a), absolute(origin, rel_b)
    corners = f"{a[0]} {a[1]} {a[2]} {b[0]} {b[1]} {b[2]}"
    if kind == "fill":
        return f"fill {corners} {last}"
    d = absolute(origin, last)
    target = f"{d[0]} {d[1]} {d[2]}"
    if kind == "clone_move_strict":
        return f"clone {corners} {target} strict replace move"
    if kind in ("clone_move", "clone_force"):
        return f"clone {corners} {target} replace {kind.removeprefix('clone_')}"
    if kind == "clone_strict":
        return f"clone {corners} {target} strict"
    return f"clone {corners} {target}"


def observe_sim(engine: Engine, scenario: Scenario, origin: Pos) -> dict[str, str]:
    """Full block states, plus block-entity data: ``<rel>#output`` for comparators,
    ``#items``/``#cooldown`` for hoppers (``#items`` for barrels with ``watch_items``)."""
    level = engine.level
    frame: dict[str, str] = {}
    for rel in scenario.watch:
        pos = absolute(origin, rel)
        state = level.get_block_state(pos)
        frame[str(rel)] = repr(state)
        be = level.get_block_entity(pos, create=False)
        if state.block.id == "minecraft:comparator":
            frame[f"{rel}#output"] = str(getattr(be, "output", 0))
        elif state.block.id == "minecraft:hopper" and be is not None:
            frame[f"{rel}#items"] = be.contents()  # type: ignore[attr-defined]
            frame[f"{rel}#cooldown"] = str(be.cooldown_time)  # type: ignore[attr-defined]
        elif state.block.id == "minecraft:barrel" and be is not None and scenario.watch_items:
            frame[f"{rel}#items"] = be.contents()  # type: ignore[attr-defined]
        elif state.block.id == "minecraft:moving_piston" and be is not None:
            # The saved "progress" tag is progressO (PistonMovingBlockEntity.saveAdditional).
            frame[f"{rel}#progress"] = str(float(be.progress_o))  # type: ignore[attr-defined]
    return frame


# ---------------------------------------------------------------- game side
def prepare_area(server: GameServer, origin: Pos, size: tuple[int, int], margin: int = 2) -> None:
    x0, z0 = origin[0] - margin, origin[2] - margin
    x1, z1 = origin[0] + size[0] + margin - 1, origin[2] + size[1] + margin - 1
    server.run(
        [
            f"fill {x0} -63 {z0} {x1} -62 {z1} minecraft:stone strict",
            f"fill {x0} {FLOOR_Y} {z0} {x1} {FLOOR_Y} {z1} minecraft:stone strict",
            f"fill {x0} {FLOOR_Y + 1} {z0} {x1} {FLOOR_Y + 12} {z1} minecraft:air strict",
            "kill @e[type=minecraft:item]",
        ]
    )


def observe_game(server: GameServer, expected: dict[str, str], origin: Pos) -> dict[str, str]:
    data_keys = [key for key in expected if "#" in key]
    observed_data = {
        key: read_block_data(server, absolute(origin, _parse_rel(key.split("#")[0])), key)
        for key in data_keys
    }
    keys = [key for key in expected if "#" not in key]
    positions = [absolute(origin, _parse_rel(key)) for key in keys]
    verdicts = server.test_blocks(list(zip(positions, [expected[k] for k in keys], strict=True)))
    observed: dict[str, str] = {}
    for key, pos, ok in zip(keys, positions, verdicts, strict=True):
        observed[key] = expected[key] if ok else discover_state(server, pos)
    observed.update(observed_data)
    return observed


DATA_PATHS = {
    "output": "OutputSignal",
    "progress": "progress",
    "cooldown": "TransferCooldown",
    "items": "Items",
}


def read_block_data(server: GameServer, pos: Pos, key: str) -> str:
    """Read one block-entity field with ``data get block`` (e.g. comparator output)."""
    path = DATA_PATHS[key.split("#")[1]]
    text = server.command(f"data get block {pos[0]} {pos[1]} {pos[2]} {path}").text
    if path == "Items":
        return _parse_items(text)
    match = re.search(r"has the following block data: (-?[\d.]+)([fdbsL]?)", text)
    if not match:
        return f"<no data: {text.strip()[:80]}>"
    number = match.group(1)
    return str(float(number)) if match.group(2) in ("f", "d") or "." in number else number


def _parse_items(text: str) -> str:
    """``data get block … Items`` → ``slot:id*count …`` (``ContainerBlockEntity.contents``)."""
    if "has the following block data" not in text:
        return f"<no data: {text.strip()[:80]}>"
    found = []
    for entry in re.findall(r"\{[^{}]*\}", text.split("block data:", 1)[1]):
        slot = re.search(r"Slot: (\d+)b", entry)
        item = re.search(r'id: "([^"]+)"', entry)
        count = re.search(r"count: (\d+)", entry)
        if not (slot and item):
            return f"<unparsed: {entry[:80]}>"
        found.append((int(slot.group(1)), item.group(1), int(count.group(1)) if count else 1))
    return " ".join(f"{slot}:{item}*{count}" for slot, item, count in sorted(found))


def discover_state(server: GameServer, pos: Pos) -> str:
    """Find the real block state by testing candidate blocks and property values."""
    candidates = list(blocks.REGISTRY.values())
    hits = server.test_blocks([(pos, block.id) for block in candidates])
    matches = [block for block, ok in zip(candidates, hits, strict=True) if ok]
    if not matches:
        return "<unknown block (not in simulator registry)>"
    block = matches[0]
    state: BlockState = block.default_state
    for prop in block.properties:
        checks = [(pos, f"{block.id}[{prop.name}={prop.serialize(v)}]") for v in prop.values]
        values = server.test_blocks(checks)
        for value, ok in zip(prop.values, values, strict=True):
            if ok:
                state = state.with_(prop, value)
    return repr(state)


def _parse_rel(key: str) -> Pos:
    x, y, z = (int(v) for v in key.strip("()").split(","))
    return (x, y, z)


FATAL_OUTPUT = ("not loaded", "Unknown", "Incorrect argument", "Expected", "Invalid")


def check_outputs(results: list[Any]) -> None:
    """Fail loudly if the game rejected a command (unloaded area, syntax, unknown block).

    "Could not set the block" is not an error: it means "no change", which the simulator
    reproduces as a no-op too."""
    for result in results:
        if any(marker in result.text for marker in FATAL_OUTPUT):
            raise RuntimeError(f"game rejected {result.command!r}: {result.text.strip()[:200]}")


def run_game(
    server: GameServer, scenario: Scenario, origin: Pos, sim_frames: list[dict[str, str]]
) -> list[dict[str, str]]:
    prepare_area(server, origin, scenario.size)
    check_outputs(
        server.run(
            [
                f"setblock {' '.join(map(str, absolute(origin, rel)))} {s}"
                + (snbt(game_nbt(nbt[0])) if nbt else "")
                for rel, s, *nbt in scenario.setup
            ]
        )
    )
    frames = [observe_game(server, sim_frames[0], origin)]
    for tick in range(scenario.ticks):
        commands = [
            f"setblock {' '.join(map(str, absolute(origin, rel)))} {s}"
            for rel, s in scenario.inputs.get(tick, [])
        ]
        commands += [game_command(origin, c) for c in scenario.commands.get(tick, [])]
        if commands:
            check_outputs(server.run(commands))
        server.step(1)
        frames.append(observe_game(server, sim_frames[tick + 1], origin))
    return frames


class _Byte(int):
    """An NBT byte (``1b``)."""


def game_nbt(nbt: dict[str, Any]) -> dict[str, Any]:
    """The simulator's block-entity JSON in the game's NBT layout: slot numbers are bytes,
    and a lectern book's page count becomes a ``writable_book_content`` page list."""
    data = json.loads(json.dumps(nbt))
    for item in data.get("Items", []):
        item["Slot"] = _Byte(item["Slot"])
    book = data.get("Book")
    if book is not None and "pages" in book:
        pages = [str(i + 1) for i in range(book.pop("pages"))]
        book["components"] = {"minecraft:writable_book_content": {"pages": pages}}
    return data


def snbt(value: Any) -> str:
    """Stringified NBT for commands."""
    if isinstance(value, dict):
        items = []
        for key, item in value.items():
            name = key if re.fullmatch(r"[A-Za-z0-9_]+", key) else json.dumps(key)
            items.append(f"{name}:{snbt(item)}")
        return "{" + ",".join(items) + "}"
    if isinstance(value, list):
        return "[" + ",".join(snbt(item) for item in value) + "]"
    if isinstance(value, _Byte):
        return f"{int(value)}b"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return str(value)
    return json.dumps(str(value))


# ---------------------------------------------------------------- driver
def compare(server: GameServer, scenario: Scenario, origin: Pos) -> dict[str, Any]:
    start_time = server.game_time()
    sim_frames = run_sim(scenario, origin, start_time)
    game_frames = run_game(server, scenario, origin, sim_frames)
    records = [
        TickRecord(t, sim, game)
        for t, (sim, game) in enumerate(zip(sim_frames, game_frames, strict=True))
    ]
    mismatching = [r.tick for r in records if r.mismatches]
    result = {
        "scenario": scenario.name,
        "description": scenario.description,
        "origin": list(origin),
        "start_time": start_time,
        "fingerprint": scenario.fingerprint(),
        "game_version": "26.3",
        "ticks": scenario.ticks,
        "match": not mismatching,
        "mismatching_ticks": mismatching,
        "frames": [
            {"tick": r.tick, "sim": r.sim, "game": r.game, "mismatches": r.mismatches}
            for r in records
        ],
    }
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    text = json.dumps(result, indent=1) + "\n"
    if scenario.name.startswith("fuzz_"):
        # Random circuits watch whole volumes: store compressed (about 100× smaller).
        data = gzip.compress(text.encode(), compresslevel=9, mtime=0)
        (RESULTS_DIR / f"{scenario.name}.json.gz").write_bytes(data)
    else:
        (RESULTS_DIR / f"{scenario.name}.json").write_text(text)
    return result
