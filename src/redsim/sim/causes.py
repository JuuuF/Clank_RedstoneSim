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
from typing import Any

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
    #: 0: the chain itself; 1: where a piston's power comes from (and why that is on).
    branch: int = 0


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
    if record.kind == tr.NOTE and d.get("kind") == "piston_power":
        return piston_power_text(record, name)
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


def _at(pos: Any) -> str:
    return " ".join(str(v) for v in pos)


def piston_power_text(record: TraceRecord, name: Callable[[str], str] = _short) -> str:
    """Where the power that extends a piston comes from (``Piston._trace_power``)."""
    d = record.detail
    via = name(str(d.get("via_block")))
    sources = [
        f"{label if label == 'sequence power' else name(str(label))} at {_at(pos)}"
        for pos, label in d.get("sources") or ()
    ]
    powered = f" (powered by {', '.join(sources)})" if sources else ""
    if d.get("quasi"):
        above = record.pos[0], record.pos[1] + 1, record.pos[2]  # type: ignore[index]
        return (
            f"the piston is powered through quasi-connectivity: {via} at {_at(d.get('via'))}"
            f"{powered} powers the space above it ({_at(above)}), as if the piston were there"
        )
    return f"the piston is powered by {via} at {_at(d.get('via'))}{powered}"


def last_change(trace: Trace, pos: Pos, before: int | None = None) -> TraceRecord | None:
    """The latest record that changed the block at ``pos`` (state differs), if kept;
    with ``before``, the latest one with a smaller id."""
    records = trace.records if before is None else trace.records[: max(0, before - trace.base_id)]
    for record in reversed(records):
        if (
            record.kind == tr.SET_BLOCK
            and record.pos == pos
            and record.detail.get("old") != record.detail.get("new")
        ):
            return record
    return None


MOVING_PISTON = "minecraft:moving_piston"


def _origin(trace: Trace, step: TraceRecord) -> TraceRecord | None:
    """What led to a step: the scheduling of its tick, the queuing of its event, or for
    a moving piston's block-entity tick, the change that put the moving piston there (it
    only exists because a piston started moving; other block entities, like hoppers,
    tick on their own and have no origin)."""
    d = step.detail
    kind = d.get("kind")
    if kind not in ("scheduled_tick", "block_event", "block_entity"):
        return None
    end = step.id - trace.base_id
    for record in reversed(trace.records[: max(0, end)]):
        if record.pos != step.pos:
            continue
        r = record.detail
        if kind == "block_entity":
            if record.kind == tr.SET_BLOCK and r.get("old") != r.get("new"):
                return record if str(r.get("new")).startswith(MOVING_PISTON) else None
            continue
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


def _block_name(state_text: Any) -> str:
    """``minecraft:stone_button[…]`` → ``stone_button`` (the name neighbor updates carry)."""
    return str(state_text).split("[", 1)[0].removeprefix("minecraft:")


def _adjacent(a: Pos, b: Pos) -> bool:
    return abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[2] - b[2]) == 1


def _source_change(trace: Trace, update: TraceRecord) -> TraceRecord | None:
    """The change of the block a neighbor update came from, earlier in the same step.
    Some blocks change first and update their neighbors afterwards, so the change is not
    the update's parent: redstone wire sets its power with flags 2, then updates around
    it (the update comes from the wire's position); buttons, levers, torches, repeaters
    and observers change, then update around a block next to them (the block they are
    attached to or point into: the update comes from that block's position, naming the
    component as its source). So: the latest change at the update's source position, or
    else the latest change next to it to the block the update names."""
    source = update.detail.get("source_pos")
    if source is None:
        return None
    source = tuple(source)
    name = update.detail.get("source")
    end = update.id - trace.base_id
    beside: TraceRecord | None = None
    for record in reversed(trace.records[: max(0, end)]):
        if record.step != update.step:
            break
        if record.kind != tr.SET_BLOCK or record.detail.get("old") == record.detail.get("new"):
            continue
        if record.pos == source:
            return record
        if (
            beside is None
            and record.pos is not None
            and _adjacent(record.pos, source)
            and _block_name(record.detail.get("new")) == name
        ):
            beside = record
    return beside


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
    links = chain(trace, record, limit)
    causes = [Cause(r.id, r.game_time, r.pos, describe(r, name)) for r in links]
    return causes + _power_branch(trace, links, name, limit)


def _power_note(trace: Trace, queued: TraceRecord) -> TraceRecord | None:
    """The note a piston left right before queuing its extension (``_trace_power``)."""
    end = queued.id - trace.base_id
    for record in reversed(trace.records[max(0, end - 8) : max(0, end)]):
        is_note = record.kind == tr.NOTE and record.detail.get("kind") == "piston_power"
        if is_note and record.pos == queued.pos:
            return record
    return None


def _power_branch(
    trace: Trace, links: list[TraceRecord], name: Callable[[str], str], limit: int
) -> list[Cause]:
    """For a piston that extended: where its power came from, and that block's own
    causes (owner, 2026-10-14: a quasi-connected piston only showed the update that
    made it look, not why it would extend)."""
    out: list[Cause] = []
    seen = {record.id for record in links}
    for record in links:
        if record.kind != tr.BLOCK_EVENT_QUEUED or record.detail.get("b0") != 0:
            continue
        note = _power_note(trace, record)
        if note is None:
            continue
        out.append(Cause(note.id, note.game_time, note.detail.get("via"), describe(note, name), 1))
        targets = [tuple(pos) for pos, _ in note.detail.get("sources") or ()]
        targets = targets or [tuple(note.detail.get("via") or ())]
        for target in targets:
            change = last_change(trace, target, before=note.id)
            if change is None or change.id in seen:
                continue
            for link in chain(trace, change, limit):
                if link.id in seen:
                    break
                seen.add(link.id)
                out.append(Cause(link.id, link.game_time, link.pos, describe(link, name), 1))
    return out


#: How many block changes ``effects`` lists at most.
MAX_EFFECTS = 200


def effects(trace: Trace, record: TraceRecord, limit: int = MAX_EFFECTS) -> list[TraceRecord]:
    """The block changes that ``record`` (a block change) caused, oldest first: through
    the updates it sent, the scheduled ticks and block events those queued (in later
    ticks too), the block-entity ticks of moving pistons it placed, and their own updates
    — ``chain`` read forwards. Neighbor updates sent in
    the same engine step from the position of a caused change, or from next to it naming
    the changed block as their source, count as caused too (blocks that change first and
    update around themselves afterwards, see ``_source_change``)."""
    caused = {record.id}
    #: (step, position) → name of the block a caused change put there.
    changed: dict[tuple[int, Any], str] = {
        (record.step, record.pos): _block_name(record.detail.get("new"))
    }
    scheduled: set[tuple[Any, Any, Any]] = set()
    queued: set[tuple[Any, Any, Any]] = set()
    #: Positions of moving pistons a caused change placed (their block entity ticks).
    moving: set[Any] = set()
    out: list[TraceRecord] = []
    for r in trace.after(record.id):
        d = r.detail
        if r.kind == tr.SET_BLOCK and r.pos in moving and d.get("old") != d.get("new"):
            moving.discard(r.pos)  # the moving piston is gone (or replaced)
        inside = r.parent in caused
        if not inside and r.kind == tr.NEIGHBOR_UPDATE and d.get("source_pos") is not None:
            x, y, z = d["source_pos"]
            inside = (r.step, (x, y, z)) in changed or any(
                changed.get((r.step, near)) == d.get("source")
                for near in ((x - 1, y, z), (x + 1, y, z), (x, y - 1, z), (x, y + 1, z),
                             (x, y, z - 1), (x, y, z + 1))
            )  # fmt: skip
        if not inside and r.kind == tr.STEP:
            kind = d.get("kind")
            if kind == "scheduled_tick":
                inside = (r.pos, r.game_time, d.get("sub_tick")) in scheduled
            elif kind == "block_event":
                inside = (r.pos, d.get("b0"), d.get("b1")) in queued
            elif kind == "block_entity":
                inside = r.pos in moving
        if not inside:
            continue
        caused.add(r.id)
        if r.kind == tr.SET_BLOCK and d.get("old") != d.get("new"):
            out.append(r)
            changed[(r.step, r.pos)] = _block_name(d.get("new"))
            if str(d.get("new")).startswith(MOVING_PISTON):
                moving.add(r.pos)
            if len(out) >= limit:
                break
        elif r.kind == tr.SCHEDULE_TICK and d.get("accepted"):
            scheduled.add((r.pos, d.get("trigger_tick"), d.get("sub_tick")))
        elif r.kind == tr.BLOCK_EVENT_QUEUED and d.get("accepted"):
            queued.add((r.pos, d.get("b0"), d.get("b1")))
    return out
