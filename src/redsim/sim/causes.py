""" "Why did this block change?": the chain of causes behind a block's last change, read
from the engine's trace (``sim/trace.py``).

Every trace record has a parent (the record being executed when it was caused). Engine
steps are roots; a scheduled tick or a block event continues the chain at the record that
scheduled or queued it (an earlier tick), so a chain can reach back across ticks to the
action that started it (a lever, a sequence pulse, an edit).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from redsim.core.pos import Pos
from redsim.sim import trace as tr
from redsim.sim.trace import Trace, TraceRecord

#: How many links a chain shows at most (update storms can be long).
MAX_LINKS = 60


@dataclass(frozen=True)
class Cause:
    """One link of a chain: what happened, where and when (the trace record's id)."""

    record: int
    tick: int
    pos: Pos | None
    text: str


def _short(block: str) -> str:
    return block.removeprefix("minecraft:").replace("_", " ")


def _properties(state: str) -> dict[str, str]:
    if "[" not in state:
        return {}
    inside = state[state.index("[") + 1 : state.rindex("]")]
    return dict(part.split("=", 1) for part in inside.split(",") if "=" in part)


def state_change(old: str, new: str, name: Callable[[str], str] = _short) -> str:
    """``old`` → ``new`` in words: "stone placed", "powered false → true", …"""
    old_id, new_id = old.split("[")[0], new.split("[")[0]
    if old_id != new_id:
        if new_id in ("minecraft:air", "air"):
            return f"{name(old_id)} removed"
        if old_id in ("minecraft:air", "air"):
            return f"{name(new_id)} placed"
        return f"{name(old_id)} → {name(new_id)}"
    before, after = _properties(old), _properties(new)
    changed = [f"{k} {before.get(k)} → {v}" for k, v in after.items() if before.get(k) != v]
    return f"{name(new_id)}: {', '.join(changed) or 'set again'}"


def describe(record: TraceRecord, name: Callable[[str], str] = _short) -> str:
    """A trace record in words."""
    d = record.detail
    if record.kind == tr.SET_BLOCK:
        return state_change(str(d.get("old")), str(d.get("new")), name)
    if record.kind == tr.NEIGHBOR_UPDATE:
        source = name(str(d.get("source", "")))
        where = d.get("source_pos")
        at = f" at {' '.join(str(v) for v in where)}" if where else ""
        return f"neighbor update from {source}{at}"
    if record.kind == tr.SHAPE_UPDATE:
        return f"shape update from the {d.get('direction')}"
    if record.kind == tr.SCHEDULE_TICK:
        return f"{name(str(d.get('block')))} scheduled a tick for tick {d.get('trigger_tick')}"
    if record.kind == tr.BLOCK_EVENT_QUEUED:
        return f"{name(str(d.get('block')))} queued a block event ({d.get('b0')}, {d.get('b1')})"
    if record.kind == tr.BLOCK_ENTITY:
        return f"block entity {d.get('action')}"
    if record.kind == tr.NOTE:
        return str(d.get("text") or d.get("info") or "note")
    if record.kind == tr.STEP:
        kind = str(d.get("kind"))
        if kind == "action":
            return f"edit or player action: {d.get('action')}"
        if kind == "scheduled_tick":
            return f"scheduled tick of {name(str(d.get('block')))}"
        if kind == "block_event":
            return f"block event of {name(str(d.get('block')))}"
        if kind == "block_entity":
            return "block entity tick"
        if kind == "tick_start":
            return "start of the tick"
        return kind.replace("_", " ")
    return record.summary()


def last_change(trace: Trace, pos: Pos) -> TraceRecord | None:
    """The latest record that changed the block at ``pos`` (state differs), if kept."""
    for record in reversed(trace.records):
        if (
            record.kind == tr.SET_BLOCK
            and record.pos == pos
            and record.detail.get("old") != record.detail.get("new")
        ):
            return record
    return None


def _origin(trace: Trace, step: TraceRecord) -> TraceRecord | None:
    """What led to a step: the scheduling of its tick or the queuing of its event."""
    d = step.detail
    kind = d.get("kind")
    if kind not in ("scheduled_tick", "block_event"):
        return None
    end = step.id - trace.base_id
    for record in reversed(trace.records[: max(0, end)]):
        if record.pos != step.pos:
            continue
        r = record.detail
        if (
            kind == "scheduled_tick"
            and record.kind == tr.SCHEDULE_TICK
            and r.get("accepted")
            and r.get("trigger_tick") == step.game_time
            and r.get("sub_tick") == d.get("sub_tick")
        ):
            return record
        if (
            kind == "block_event"
            and record.kind == tr.BLOCK_EVENT_QUEUED
            and r.get("accepted")
            and (r.get("b0"), r.get("b1")) == (d.get("b0"), d.get("b1"))
        ):
            return record
    return None


def _source_change(trace: Trace, update: TraceRecord) -> TraceRecord | None:
    """The change of the block a neighbor update came from, earlier in the same step.
    Some blocks change first and update their neighbors afterwards (redstone wire sets its
    power with flags 2, then updates around it), so the change is not the update's
    parent."""
    source = update.detail.get("source_pos")
    if source is None:
        return None
    source = tuple(source)
    end = update.id - trace.base_id
    for record in reversed(trace.records[: max(0, end)]):
        if record.step != update.step:
            return None
        if (
            record.kind == tr.SET_BLOCK
            and record.pos == source
            and record.detail.get("old") != record.detail.get("new")
        ):
            return record
    return None


def chain(trace: Trace, record: TraceRecord, limit: int = MAX_LINKS) -> list[TraceRecord]:
    """``record`` and its causes, newest first, back to the action that started it (or as
    far as the kept trace reaches)."""
    links = [record]
    current = record
    while len(links) < limit:
        parent = trace.get(current.parent)
        if current.kind == tr.NEIGHBOR_UPDATE and not (
            parent is not None
            and parent.kind == tr.SET_BLOCK
            and parent.pos == tuple(current.detail.get("source_pos") or ())
        ):
            parent = _source_change(trace, current) or parent
        if parent is None and current.kind == tr.STEP:
            parent = _origin(trace, current)
        if parent is None:
            break
        links.append(parent)
        current = parent
    return links


def why(
    trace: Trace, pos: Pos, name: Callable[[str], str] = _short, limit: int = MAX_LINKS
) -> list[Cause]:
    """The causes of the last change of the block at ``pos``, newest first; empty when the
    trace holds no change there (unchanged since the build, or too long ago)."""
    record = last_change(trace, pos)
    if record is None:
        return []
    return [Cause(r.id, r.game_time, r.pos, describe(r, name)) for r in chain(trace, record, limit)]
