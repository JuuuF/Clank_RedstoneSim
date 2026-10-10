"""Save/load round trips must preserve behavior exactly, including mid-tick saves."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from redsim.io.save import engine_from_json, engine_to_json, load, save
from redsim.sim.engine import Action, Engine, Phase
from tests.sim.bench import Bench
from tools.gameserver import scenarios
from tools.gameserver.compare import absolute, build_terrain


def scenario_engine(name: str) -> tuple[Engine, scenarios.Scenario]:
    scenario = scenarios.BY_NAME[name]
    engine = Engine()
    build_terrain(engine, (0, 0, 0), scenario.size)
    for rel, state in scenario.setup:
        engine.apply(Action("setblock", absolute((0, 0, 0), rel), state))
    return engine, scenario


def world_signature(engine: Engine) -> list[tuple[object, ...]]:
    level = engine.level
    entities = sorted((p, be.to_json().__repr__()) for p, be in level.block_entities.items())
    return [
        tuple(sorted((p, repr(s)) for p, s in level.blocks.items())),
        tuple(entities),
        tuple(level.block_ticks.pending()),
        tuple(level.block_ticks.to_run),
        tuple(level.block_events),
        level.game_time,
        level.sub_tick_count,
        tuple(level.torch_toggles),
        engine.phase,
    ]


def run_steps(engine: Engine, count: int) -> list[str]:
    return [engine.step().kind for _ in range(count)]


@pytest.mark.parametrize("name", ["and_gate", "torch_burnout", "comparator_modes"])
def test_round_trip_mid_tick_continues_identically(name: str) -> None:
    engine, scenario = scenario_engine(name)
    for tick in range(12):
        for rel, state in scenario.inputs.get(tick, []):
            engine.apply(Action("setblock", absolute((0, 0, 0), rel), state))
        engine.run_tick()
    engine.step()  # stop inside a tick
    restored = engine_from_json(json.loads(json.dumps(engine_to_json(engine))))
    assert world_signature(restored) == world_signature(engine)
    assert run_steps(restored, 60) == run_steps(engine, 60)
    assert world_signature(restored) == world_signature(engine)


def test_round_trip_preserves_pending_and_collected_ticks(tmp_path: Path) -> None:
    b = Bench()
    b.place((0, 1, 0), "redstone_block")
    b.place((1, 1, 0), "repeater[facing=west]")
    b.place((1, 1, 2), "repeater[facing=west]")
    b.place((0, 1, 2), "redstone_block")
    b.engine.step()  # tick start: the repeater ticks are collected
    assert b.engine.phase is Phase.BLOCK_TICKS
    path = tmp_path / "world.json"
    save(path, b.engine, {"note": "kept"})
    restored, extra = load(path)
    assert extra == {"note": "kept"}
    assert list(restored.level.block_ticks.to_run) == list(b.engine.level.block_ticks.to_run)
    assert restored.level.will_tick_this_tick(
        (1, 1, 0), restored.level.get_block_state((1, 1, 0)).block
    )
    assert run_steps(restored, 5) == run_steps(b.engine, 5)


def test_rejects_foreign_or_newer_files() -> None:
    with pytest.raises(ValueError):
        engine_from_json({"format": "something-else"})
    data = engine_to_json(Engine())
    data["version"] = 999
    with pytest.raises(ValueError):
        engine_from_json(data)
