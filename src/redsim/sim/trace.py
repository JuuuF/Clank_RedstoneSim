"""Causal trace of everything the engine does.

Each record has a parent: the record that was being executed when this one was caused.
Neighbor updates remember the record that queued them, because the collecting neighbor
updater may run them later than they were requested. Engine steps are the roots.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

from redsim.core.pos import Pos

# Record kinds.
STEP = "step"
NEIGHBOR_UPDATE = "neighbor_update"
SHAPE_UPDATE = "shape_update"
COMPARATOR_UPDATE = "comparator_update"
SET_BLOCK = "set_block"
SCHEDULE_TICK = "schedule_tick"
BLOCK_EVENT_QUEUED = "block_event_queued"
BLOCK_ENTITY = "block_entity"
NOTE = "note"


@dataclass(slots=True)
class TraceRecord:
    id: int
    kind: str
    parent: int | None
    game_time: int
    step: int
    pos: Pos | None
    detail: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        d = self.detail
        where = f" @ {self.pos}" if self.pos is not None else ""
        if self.kind == STEP:
            return f"[{d.get('kind')}]{where} {d.get('info', '')}".rstrip()
        if self.kind == NEIGHBOR_UPDATE:
            return f"neighborChanged{where} from {d.get('source')} ({d.get('target')})"
        if self.kind == SHAPE_UPDATE:
            return f"updateShape{where} dir={d.get('direction')} ({d.get('target')})"
        if self.kind == SET_BLOCK:
            return f"setBlock{where} {d.get('old')} -> {d.get('new')} flags={d.get('flags')}"
        if self.kind == SCHEDULE_TICK:
            verdict = "" if d.get("accepted") else " (duplicate, dropped)"
            return (
                f"scheduleTick{where} {d.get('block')} delay={d.get('delay')} "
                f"priority={d.get('priority')} at={d.get('trigger_tick')}{verdict}"
            )
        if self.kind == BLOCK_EVENT_QUEUED:
            verdict = "" if d.get("accepted") else " (duplicate, merged)"
            return f"blockEvent{where} {d.get('block')} ({d.get('b0')}, {d.get('b1')}){verdict}"
        return f"{self.kind}{where} {d}"


class Trace:
    """Append-only record list with a cause stack."""

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self.records: list[TraceRecord] = []
        self._cause: list[int | None] = []
        self.game_time = 0
        self.step = 0

    @property
    def current_cause(self) -> int | None:
        return self._cause[-1] if self._cause else None

    def emit(
        self,
        kind: str,
        pos: Pos | None = None,
        /,
        parent: int | None | bool = True,
        **detail: Any,
    ) -> int | None:
        """Append a record. ``parent=True`` means "the current cause"."""
        if not self.enabled:
            return None
        record_id = len(self.records)
        actual_parent = self.current_cause if parent is True else parent
        self.records.append(
            TraceRecord(
                record_id,
                kind,
                actual_parent if isinstance(actual_parent, int) else None,
                self.game_time,
                self.step,
                pos,
                detail,
            )
        )
        return record_id

    def push(self, record_id: int | None) -> None:
        self._cause.append(record_id)

    def pop(self) -> None:
        self._cause.pop()

    def clear(self) -> None:
        self.records.clear()
        self._cause.clear()

    def for_step(self, step: int) -> Iterator[TraceRecord]:
        return (r for r in self.records if r.step == step)
