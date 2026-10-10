"""Scheduled ticks, block events and engine phases (doc/mechanics/tick-scheduling.md)."""

from __future__ import annotations

from typing import Any

import pytest

from redsim.sim.engine import Action, ActionError, Engine, Phase
from redsim.sim.ticks import TickPriority
from redsim.world import blocks
from tests.sim.probe import ProbeBlock


def make_engine() -> tuple[Engine, list[tuple[Any, ...]]]:
    return Engine(), []


def test_tick_runs_after_delay_counted_from_current_game_time() -> None:
    engine, log = make_engine()
    probe = ProbeBlock("p", log)
    pos = (0, 0, 0)
    engine.level.blocks[pos] = probe.default_state
    engine.level.schedule_tick(pos, probe, 2)  # game time 0 → trigger tick 2
    engine.run_tick()
    assert log == []
    engine.run_tick()
    assert log == [("tick", "p", pos, 2)]


def test_order_is_priority_then_scheduling_order() -> None:
    engine, log = make_engine()
    probe = ProbeBlock("p", log)
    level = engine.level
    for x in range(4):
        level.blocks[(x, 0, 0)] = probe.default_state
    level.schedule_tick((0, 0, 0), probe, 1, TickPriority.NORMAL)
    level.schedule_tick((1, 0, 0), probe, 1, TickPriority.HIGH)
    level.schedule_tick((2, 0, 0), probe, 1, TickPriority.EXTREMELY_HIGH)
    level.schedule_tick((3, 0, 0), probe, 1, TickPriority.HIGH)
    engine.run_tick()
    assert [entry[2][0] for entry in log] == [2, 1, 3, 0]


def test_duplicate_request_is_dropped_but_consumes_a_sub_tick() -> None:
    engine, log = make_engine()
    probe = ProbeBlock("p", log)
    level = engine.level
    level.blocks[(0, 0, 0)] = probe.default_state
    assert level.schedule_tick((0, 0, 0), probe, 3) is True
    assert level.schedule_tick((0, 0, 0), probe, 1, TickPriority.EXTREMELY_HIGH) is False
    assert level.sub_tick_count == 2
    engine.run_ticks(2)
    assert log == []
    engine.run_tick()
    assert log == [("tick", "p", (0, 0, 0), 3)]


def test_ticks_scheduled_during_the_phase_wait_for_next_tick() -> None:
    engine, log = make_engine()
    probe = ProbeBlock("p", log)
    level = engine.level
    level.blocks[(0, 0, 0)] = probe.default_state
    level.blocks[(1, 0, 0)] = probe.default_state

    def reschedule(state: Any, lvl: Any, pos: Any) -> None:
        if pos == (0, 0, 0):
            # Even with delay 0 the tick was not collected, so it runs next tick.
            lvl.schedule_tick((1, 0, 0), probe, 0)
            assert lvl.will_tick_this_tick((1, 0, 0), probe) is False
            assert lvl.has_scheduled_tick((1, 0, 0), probe) is True

    probe.on_tick = reschedule
    level.schedule_tick((0, 0, 0), probe, 1)
    engine.run_tick()
    assert log == [("tick", "p", (0, 0, 0), 1)]
    engine.run_tick()
    assert log[-1] == ("tick", "p", (1, 0, 0), 2)


def test_will_tick_this_tick_and_rescheduling_own_tick() -> None:
    engine, log = make_engine()
    probe = ProbeBlock("p", log)
    level = engine.level
    a, b = (0, 0, 0), (1, 0, 0)
    level.blocks[a] = probe.default_state
    level.blocks[b] = probe.default_state
    seen: list[bool] = []

    def check(state: Any, lvl: Any, pos: Any) -> None:
        if pos == a:
            seen.append(lvl.will_tick_this_tick(b, probe))  # b collected, not yet run
            seen.append(lvl.has_scheduled_tick(b, probe))  # no longer pending
            seen.append(lvl.schedule_tick(a, probe, 1))  # own tick was collected: accepted

    probe.on_tick = check
    level.schedule_tick(a, probe, 1)
    level.schedule_tick(b, probe, 1)
    engine.run_tick()
    assert seen == [True, False, True]


def test_tick_skipped_when_block_changed() -> None:
    engine, log = make_engine()
    probe = ProbeBlock("p", log)
    engine.level.blocks[(0, 0, 0)] = probe.default_state
    engine.level.schedule_tick((0, 0, 0), probe, 1)
    engine.level.blocks[(0, 0, 0)] = blocks.STONE.default_state
    steps = engine.run_tick()
    assert log == []
    assert steps[1].kind == "scheduled_tick" and "skipped" in steps[1].detail["info"]


def test_block_events_fifo_dedup_and_same_phase_cascade() -> None:
    engine, log = make_engine()
    probe = ProbeBlock("p", log)
    level = engine.level
    level.blocks[(0, 0, 0)] = probe.default_state
    level.blocks[(1, 0, 0)] = probe.default_state

    def on_event(state: Any, lvl: Any, pos: Any, b0: int, b1: int) -> bool:
        if (b0, b1) == (1, 0):
            lvl.block_event((1, 0, 0), probe, 9, 9)  # queued during the phase: same tick
        return True

    probe.on_event = on_event
    level.block_event((0, 0, 0), probe, 1, 0)
    level.block_event((1, 0, 0), probe, 2, 0)
    level.block_event((0, 0, 0), probe, 1, 0)  # identical: merged
    engine.run_tick()
    assert [(e[2], e[3]) for e in log] == [
        ((0, 0, 0), (1, 0)),
        ((1, 0, 0), (2, 0)),
        ((1, 0, 0), (9, 9)),
    ]
    assert all(e[3] == 1 for e in log if e[0] == "tick")


def test_phase_order_within_a_tick() -> None:
    engine, log = make_engine()
    probe = ProbeBlock("p", log)
    level = engine.level
    level.blocks[(0, 0, 0)] = probe.default_state
    probe.on_tick = lambda s, lvl, p: lvl.block_event(p, probe, 0, 0)
    level.schedule_tick((0, 0, 0), probe, 1)
    steps = engine.run_tick()
    assert [s.kind for s in steps] == ["tick_start", "scheduled_tick", "block_event"]
    assert engine.phase is Phase.BETWEEN_TICKS
    assert level.handling_tick is False


def test_actions_only_between_ticks() -> None:
    engine, log = make_engine()
    probe = ProbeBlock("p", log)
    engine.level.blocks[(0, 0, 0)] = probe.default_state
    engine.level.schedule_tick((0, 0, 0), probe, 1)
    engine.step()  # tick start: now inside the tick
    assert engine.phase is Phase.BLOCK_TICKS
    with pytest.raises(ActionError):
        engine.apply(Action("set_block", (5, 0, 0), "stone"))
    engine.finish_tick()
    engine.apply(Action("set_block", (5, 0, 0), "stone"))
    assert engine.level.get_block_state((5, 0, 0)).is_(blocks.STONE)


def test_snapshot_restore_replays_identically() -> None:
    engine, log = make_engine()
    probe = ProbeBlock("p", log)
    level = engine.level
    for x in range(3):
        level.blocks[(x, 0, 0)] = probe.default_state

    def chain(state: Any, lvl: Any, pos: Any) -> None:
        nxt = ((pos[0] + 1) % 3, 0, 0)
        lvl.schedule_tick(nxt, probe, 1 + pos[0])
        lvl.block_event(pos, probe, pos[0], 0)

    probe.on_tick = chain
    level.schedule_tick((0, 0, 0), probe, 1)
    engine.run_ticks(2)
    engine.step()  # stop in the middle of a tick
    snap = engine.snapshot()
    start = len(log)
    for _ in range(15):
        engine.step()
    original = log[start:]
    engine.restore(snap)
    del log[start:]
    for _ in range(15):
        engine.step()
    assert log[start:] == original
    assert len(original) > 5
