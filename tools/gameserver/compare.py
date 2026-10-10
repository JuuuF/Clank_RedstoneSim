"""Run the same scenario in the simulator and in the sandboxed 26.3 server, tick by tick.

A scenario is built only from ``/setblock`` commands (replace mode), which the simulator
mirrors exactly (``Action("setblock", ...)`` ports ``SetBlockCommand``). Inputs are applied
between ticks, like any command or player action. After every tick, the full block state of
each watched position in the simulator is checked in the game with ``execute if block``;
mismatches are resolved property by property so the report shows the real state.

Terrain: the superflat sandbox world has bedrock at y=-64, dirt at -63/-62 and grass at -61.
Each scenario gets a stone floor at y=-61 under its area (``fill ... strict``, no updates);
the simulator builds the same columns, so neighbor queries see identical blocks.
"""

from __future__ import annotations

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
    setup: list[tuple[Pos, str]]
    watch: list[Pos]
    ticks: int
    inputs: dict[int, list[tuple[Pos, str]]] = field(default_factory=dict)
    #: Region commands after ``t`` ticks (applied after ``inputs``):
    #: ``("fill", rel_a, rel_b, state)`` or ``("clone", rel_a, rel_b, rel_destination)``.
    #: The cloned area must have no pending scheduled ticks (the simulator's paste does
    #: not copy ticks, ``/clone`` does).
    commands: dict[int, list[tuple[Any, ...]]] = field(default_factory=dict)

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
def build_terrain(engine: Engine, origin: Pos, size: tuple[int, int], margin: int = 2) -> None:
    level = engine.level
    for dx in range(-margin, size[0] + margin):
        for dz in range(-margin, size[1] + margin):
            x, z = origin[0] + dx, origin[2] + dz
            level.blocks[(x, -64, z)] = blocks.BEDROCK.default_state
            level.blocks[(x, -63, z)] = blocks.get("minecraft:stone").default_state
            level.blocks[(x, -62, z)] = blocks.get("minecraft:stone").default_state
            level.blocks[(x, FLOOR_Y, z)] = blocks.STONE.default_state


def run_sim(scenario: Scenario, origin: Pos, start_time: int) -> list[dict[str, str]]:
    engine = Engine()
    engine.level.game_time = start_time
    build_terrain(engine, origin, scenario.size)
    for rel, state in scenario.setup:
        engine.apply(Action("setblock", absolute(origin, rel), state))
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

    kind, rel_a, rel_b, last = command
    a, b = absolute(origin, rel_a), absolute(origin, rel_b)
    if kind == "fill":
        return Action("fill", a, last, payload={"to": list(b)})
    prefab = Prefab.capture(engine.level, Region.from_corners(a, b))
    return Action("clone", absolute(origin, last), payload=prefab.payload())


def game_command(origin: Pos, command: tuple[Any, ...]) -> str:
    kind, rel_a, rel_b, last = command
    a, b = absolute(origin, rel_a), absolute(origin, rel_b)
    corners = f"{a[0]} {a[1]} {a[2]} {b[0]} {b[1]} {b[2]}"
    if kind == "fill":
        return f"fill {corners} {last}"
    d = absolute(origin, last)
    return f"clone {corners} {d[0]} {d[1]} {d[2]}"


def observe_sim(engine: Engine, scenario: Scenario, origin: Pos) -> dict[str, str]:
    """Full block states, plus ``<rel>#output`` for comparators (block-entity data)."""
    level = engine.level
    frame: dict[str, str] = {}
    for rel in scenario.watch:
        pos = absolute(origin, rel)
        state = level.get_block_state(pos)
        frame[str(rel)] = repr(state)
        be = level.get_block_entity(pos, create=False)
        if state.block.id == "minecraft:comparator":
            frame[f"{rel}#output"] = str(getattr(be, "output", 0))
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


DATA_PATHS = {"output": "OutputSignal", "progress": "progress"}


def read_block_data(server: GameServer, pos: Pos, key: str) -> str:
    """Read one block-entity field with ``data get block`` (e.g. comparator output)."""
    path = DATA_PATHS[key.split("#")[1]]
    text = server.command(f"data get block {pos[0]} {pos[1]} {pos[2]} {path}").text
    match = re.search(r"has the following block data: (-?[\d.]+)([fdbsL]?)", text)
    if not match:
        return f"<no data: {text.strip()[:80]}>"
    number = match.group(1)
    return str(float(number)) if match.group(2) in ("f", "d") or "." in number else number


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


def run_game(
    server: GameServer, scenario: Scenario, origin: Pos, sim_frames: list[dict[str, str]]
) -> list[dict[str, str]]:
    prepare_area(server, origin, scenario.size)
    server.run(
        [f"setblock {' '.join(map(str, absolute(origin, rel)))} {s}" for rel, s in scenario.setup]
    )
    frames = [observe_game(server, sim_frames[0], origin)]
    for tick in range(scenario.ticks):
        commands = [
            f"setblock {' '.join(map(str, absolute(origin, rel)))} {s}"
            for rel, s in scenario.inputs.get(tick, [])
        ]
        commands += [game_command(origin, c) for c in scenario.commands.get(tick, [])]
        if commands:
            server.run(commands)
        server.step(1)
        frames.append(observe_game(server, sim_frames[tick + 1], origin))
    return frames


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
    (RESULTS_DIR / f"{scenario.name}.json").write_text(json.dumps(result, indent=1) + "\n")
    return result
