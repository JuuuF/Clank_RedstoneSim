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


#: Records kept in memory; older ones are dropped (ids stay stable through ``base_id``).
MAX_RECORDS = 200_000
KEEP_AFTER_TRIM = 150_000


class Trace:
    """Append-only record list with a cause stack.

    Record ids are global: ``records[i]`` has id ``base_id + i``. When the list exceeds
    ``MAX_RECORDS`` the oldest records are dropped and ``base_id`` advances, so ids (and
    parent links to records still kept) remain valid.
    """

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self.records: list[TraceRecord] = []
        self.base_id = 0
        self._cause: list[int | None] = []
        self.game_time = 0
        self.step = 0

    @property
    def current_cause(self) -> int | None:
        return self._cause[-1] if self._cause else None

    def emit(
        self,
        record_kind: str,
        record_pos: Pos | None = None,
        /,
        parent: int | None | bool = True,
        **detail: Any,
    ) -> int | None:
        """Append a record. ``parent=True`` means "the current cause"."""
        if not self.enabled:
            return None
        if len(self.records) >= MAX_RECORDS:
            self._trim()
        record_id = self.base_id + len(self.records)
        actual_parent = self.current_cause if parent is True else parent
        self.records.append(
            TraceRecord(
                record_id,
                record_kind,
                actual_parent if isinstance(actual_parent, int) else None,
                self.game_time,
                self.step,
                record_pos,
                detail,
            )
        )
        return record_id

    def _trim(self) -> None:
        dropped = len(self.records) - KEEP_AFTER_TRIM
        del self.records[:dropped]
        self.base_id += dropped

    def get(self, record_id: int | None) -> TraceRecord | None:
        if record_id is None:
            return None
        index = record_id - self.base_id
        return self.records[index] if 0 <= index < len(self.records) else None

    def after(self, record_id: int) -> list[TraceRecord]:
        """Records emitted after ``record_id`` (kept ones only)."""
        return self.records[max(0, record_id - self.base_id + 1) :]

    def truncate_from_step(self, step: int) -> None:
        """Drop the records of engine steps ``>= step`` (used when rewinding)."""
        cut = len(self.records)
        for i, record in enumerate(self.records):
            if record.step >= step:
                cut = i
                break
        del self.records[cut:]

    def push(self, record_id: int | None) -> None:
        self._cause.append(record_id)

    def pop(self) -> None:
        self._cause.pop()

    def clear(self) -> None:
        self.base_id += len(self.records)
        self.records.clear()
        self._cause.clear()

    def for_step(self, step: int) -> Iterator[TraceRecord]:
        return (r for r in self.records if r.step == step)
