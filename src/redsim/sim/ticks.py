"""Scheduled block ticks: port of ``LevelTicks`` / ``LevelChunkTicks`` / ``ScheduledTick``.

Source (paths relative to ``data/minecraft_src/client-src/``):

* ``net/minecraft/world/ticks/ScheduledTick.java``: ``DRAIN_ORDER`` (triggerTick, priority,
  subTickOrder), uniqueness by (type, pos).
* ``net/minecraft/world/ticks/LevelChunkTicks.java`` ``schedule`` L53: a tick for a
  (pos, type) still pending in the container is dropped.
* ``net/minecraft/world/ticks/LevelTicks.java`` ``tick`` L81: collect all due ticks (up to
  ``maxTicksToProcess``) into ``toRunThisTick`` first, then run them in order;
  ``willTickThisTick`` L208; ``hasScheduledTick`` L202.

Chunk containers are not modeled. With every due tick sharing ``triggerTick == gameTime``
the cross-container merge (``INTRA_TICK_DRAIN_ORDER``) and a single global ``DRAIN_ORDER``
coincide. Overdue ticks only arise when an earlier tick hit the 65 536 cap; the collector
reports them so a possible divergence is visible (doc/quirks.md Q-SCHED-OVERDUE).
"""

from __future__ import annotations

import heapq
from collections import deque
from dataclasses import dataclass
from enum import IntEnum

from redsim.core.pos import Pos


class TickPriority(IntEnum):
    """``net/minecraft/world/ticks/TickPriority.java`` (lower runs first)."""

    EXTREMELY_HIGH = -3
    VERY_HIGH = -2
    HIGH = -1
    NORMAL = 0
    LOW = 1
    VERY_LOW = 2
    EXTREMELY_LOW = 3


@dataclass(frozen=True, slots=True)
class ScheduledTick:
    block_id: str
    pos: Pos
    trigger_tick: int
    priority: TickPriority
    sub_tick: int

    @property
    def key(self) -> tuple[Pos, str]:
        """``ScheduledTick.UNIQUE_TICK_HASH`` identity: (pos, type)."""
        return (self.pos, self.block_id)

    @property
    def drain_order(self) -> tuple[int, int, int]:
        """``ScheduledTick.DRAIN_ORDER``."""
        return (self.trigger_tick, int(self.priority), self.sub_tick)


MAX_TICKS_PER_GAME_TICK = 65536  # ServerLevel.tick: blockTicks.tick(tick, 65536, ...)


class LevelTicks:
    """Pending scheduled ticks of one level."""

    def __init__(self) -> None:
        self._heap: list[tuple[tuple[int, int, int], ScheduledTick]] = []
        self._pending: dict[tuple[Pos, str], ScheduledTick] = {}
        self.to_run: deque[ScheduledTick] = deque()
        self._to_run_keys: set[tuple[Pos, str]] = set()
        self.overdue_collected = 0

    # --- scheduling ---------------------------------------------------------------------
    def schedule(self, tick: ScheduledTick) -> bool:
        """``LevelChunkTicks.schedule``. Returns False if dropped as a duplicate."""
        if tick.key in self._pending:
            return False
        self._pending[tick.key] = tick
        heapq.heappush(self._heap, (tick.drain_order, tick))
        return True

    def has_scheduled_tick(self, pos: Pos, block_id: str) -> bool:
        """``LevelTicks.hasScheduledTick``: pending in the container (not yet collected)."""
        return (pos, block_id) in self._pending

    def will_tick_this_tick(self, pos: Pos, block_id: str) -> bool:
        """``LevelTicks.willTickThisTick``: collected for this tick and not yet run."""
        return (pos, block_id) in self._to_run_keys

    # --- per-tick processing ------------------------------------------------------------
    def collect(self, current_tick: int, max_ticks: int = MAX_TICKS_PER_GAME_TICK) -> int:
        """``LevelTicks.collectTicks``: move due ticks into ``to_run`` in drain order."""
        collected = 0
        while self._heap and len(self.to_run) < max_ticks:
            order, tick = self._heap[0]
            if order[0] > current_tick:
                break
            heapq.heappop(self._heap)
            del self._pending[tick.key]
            if tick.trigger_tick < current_tick:
                self.overdue_collected += 1
            self.to_run.append(tick)
            self._to_run_keys.add(tick.key)
            collected += 1
        return collected

    def pop_next(self) -> ScheduledTick | None:
        """Next tick of ``runCollectedTicks`` (removed before it runs, like ``poll``)."""
        if not self.to_run:
            return None
        tick = self.to_run.popleft()
        self._to_run_keys.discard(tick.key)
        return tick

    def cleanup_after_tick(self) -> None:
        """``LevelTicks.cleanupAfterTick``."""
        self.to_run.clear()
        self._to_run_keys.clear()

    # --- inspection and persistence -----------------------------------------------------
    def pending(self) -> list[ScheduledTick]:
        """All pending (not collected) ticks in drain order."""
        return [tick for _, tick in sorted(self._heap)]

    def count(self) -> int:
        return len(self._pending)

    def clone(self) -> LevelTicks:
        other = LevelTicks()
        other._heap = list(self._heap)
        other._pending = dict(self._pending)
        other.to_run = deque(self.to_run)
        other._to_run_keys = set(self._to_run_keys)
        other.overdue_collected = self.overdue_collected
        return other

    def remove_at(self, pos: Pos) -> None:
        """Drop pending ticks at ``pos`` (editor deletions only, not a game mechanic)."""
        keys = [key for key in self._pending if key[0] == pos]
        for key in keys:
            del self._pending[key]
        self._heap = [(o, t) for o, t in self._heap if t.pos != pos]
        heapq.heapify(self._heap)
