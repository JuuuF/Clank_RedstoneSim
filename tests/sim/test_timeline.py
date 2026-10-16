"""Rewind and replay must reproduce the original run exactly (doc/decisions.md ADR-004)."""

from __future__ import annotations

import random

import pytest

from redsim.sim.engine import Action, Engine
from redsim.sim.timeline import Timeline
from tests.io.test_save import world_signature
from tools.gameserver import scenarios
from tools.gameserver.compare import absolute, build_terrain


def scenario_timeline(name: str, keyframe_interval: int) -> tuple[Timeline, scenarios.Scenario]:
    scenario = scenarios.BY_NAME[name]
    engine = Engine()
    build_terrain(engine, (0, 0, 0), scenario.size)
    timeline = Timeline(engine, keyframe_interval)
    for rel, state in scenario.setup:
        timeline.apply(Action("setblock", absolute((0, 0, 0), rel), state))
    return timeline, scenario


def record_run(timeline: Timeline, scenario: scenarios.Scenario) -> dict[int, list[object]]:
    """Run the scenario's inputs and ticks, recording the world signature at every step."""
    signatures: dict[int, list[object]] = {timeline.position: world_signature(timeline.engine)}
    for tick in range(scenario.ticks):
        for rel, state in scenario.inputs.get(tick, []):
            timeline.apply(Action("setblock", absolute((0, 0, 0), rel), state))
            signatures[timeline.position] = world_signature(timeline.engine)
        while True:
            timeline.step()
            signatures[timeline.position] = world_signature(timeline.engine)
            if timeline.engine.at_tick_boundary():
                break
    return signatures


@pytest.mark.parametrize("name", ["and_gate", "piston_door", "sticky_short_pulses"])
@pytest.mark.parametrize("interval", [1, 7, 200])
def test_seek_reproduces_every_recorded_step(name: str, interval: int) -> None:
    timeline, scenario = scenario_timeline(name, interval)
    signatures = record_run(timeline, scenario)
    rng = random.Random(f"{name}-{interval}")
    targets = rng.sample(sorted(signatures), k=min(25, len(signatures)))
    for target in targets + [min(signatures), timeline.end]:
        timeline.seek(target)
        assert timeline.position == target
        assert world_signature(timeline.engine) == signatures[target], target


def test_replay_after_rewind_produces_the_same_trace() -> None:
    timeline, scenario = scenario_timeline("piston_door", 50)
    record_run(timeline, scenario)
    end = timeline.end
    trace = timeline.engine.level.trace
    original = [(r.step, r.summary()) for r in trace.records]
    middle = end // 2
    timeline.seek(middle)
    assert all(r.step < middle for r in trace.records)
    timeline.seek(end)
    assert [(r.step, r.summary()) for r in trace.records] == original


def test_a_traced_seek_leaves_no_gap_in_the_trace() -> None:
    """``seek`` jumps to a keyframe when the target is far ahead (the steps in between are
    not traced); ``seek_traced`` replays them, so cause chains are complete."""
    timeline, scenario = scenario_timeline("piston_door", 5)
    record_run(timeline, scenario)
    end = timeline.end
    trace = timeline.engine.level.trace
    original = [(r.step, r.summary()) for r in trace.records]
    timeline.seek(timeline.start + 1)
    timeline.seek(end)  # a jump: the trace now has a gap
    assert {r.step for r in trace.records} != {step for step, _ in original}
    assert not timeline._trace_complete(end)
    timeline.seek_traced(end)
    assert [(r.step, r.summary()) for r in trace.records] == original
    assert timeline._trace_complete(end)
    timeline.seek_traced(end // 2)  # backwards keeps what is before the restored keyframe
    assert timeline._trace_complete(end // 2)


def test_editing_after_rewind_truncates_the_future() -> None:
    timeline, scenario = scenario_timeline("lamp_redstone_block", 200)
    record_run(timeline, scenario)
    old_end = timeline.end
    first_input = min(i for i in timeline.inputs if i > timeline.start + len(scenario.setup) - 1)
    timeline.seek(first_input)
    timeline.apply(Action("setblock", absolute((0, 0, 0), (2, 2, 1)), "minecraft:stone"))
    assert timeline.end == first_input + 1 < old_end
    assert max(timeline.inputs) == first_input


def test_tick_back_returns_to_tick_boundaries() -> None:
    timeline, scenario = scenario_timeline("and_gate", 200)
    record_run(timeline, scenario)
    time_at_end = timeline.engine.game_time
    timeline.tick_back()
    assert timeline.engine.game_time == time_at_end - 1
    timeline.step()  # into the middle of the tick
    timeline.tick_back()  # back to the start of that tick
    assert timeline.engine.game_time == time_at_end - 1
    assert timeline.engine.at_tick_boundary()


def test_undo_and_redo_targets() -> None:
    timeline, _ = scenario_timeline("lamp_redstone_block", 200)
    last_setup = max(timeline.inputs)
    assert timeline.undo_target() == last_setup
    timeline.seek(last_setup)
    assert timeline.redo_target() == last_setup + 1


def test_trace_trimming_keeps_ids_stable(monkeypatch: pytest.MonkeyPatch) -> None:
    from redsim.sim import trace as trace_module

    monkeypatch.setattr(trace_module, "MAX_RECORDS", 50)
    monkeypatch.setattr(trace_module, "KEEP_AFTER_TRIM", 30)
    trace = trace_module.Trace()
    ids = [trace.emit(trace_module.NOTE, None, parent=None, n=i) for i in range(120)]
    assert len(trace.records) <= 50
    assert trace.get(ids[-1]) is trace.records[-1]
    assert trace.get(ids[0]) is None  # trimmed
    assert trace.records[0].id == trace.base_id


@pytest.mark.parametrize(
    "name", ["torch_burnout", "torch_burnout_update", "torch_tower", "piston_door", "hopper_clock"]
)
def test_rebasing_the_clock_changes_nothing(name: str) -> None:
    """Rebasing shifts every stored game time (scheduled ticks, torch burnout history,
    hopper and piston timestamps): the following ticks are identical."""
    from tools.gameserver.compare import observe_sim, run_sim

    scenario = scenarios.BY_NAME[name]
    reference = run_sim(scenario, (0, 0, 0), 0)
    engine = Engine()
    build_terrain(engine, (0, 0, 0), scenario.size)
    timeline = Timeline(engine)
    for rel, state, *nbt in scenario.setup:
        payload = {"nbt": nbt[0]} if nbt else None
        timeline.apply(Action("setblock", absolute((0, 0, 0), rel), state, payload=payload))
    for tick in range(scenario.ticks):
        assert observe_sim(engine, scenario, (0, 0, 0)) == reference[tick], tick
        for rel, state in scenario.inputs.get(tick, []):
            timeline.apply(Action("setblock", absolute((0, 0, 0), rel), state))
        if tick in (scenario.ticks // 3, 2 * scenario.ticks // 3):
            timeline.rebase()
            assert engine.game_time == 0
        timeline.run_tick()
