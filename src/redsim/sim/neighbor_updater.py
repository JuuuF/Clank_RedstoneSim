"""Port of ``CollectingNeighborUpdater`` (``net/minecraft/world/level/redstone/``).

``addAndRun`` (L68): when nothing is running, push the update and run the loop now;
otherwise append it to ``addedThisLayer`` and return. ``runUpdates`` (L87): push the
layer onto the stack in reverse, then run sub-updates of the top record until one of them
adds something or the record is exhausted. The result is a depth-first order in which no
handler is ever re-entered. See doc/mechanics/neighbor-updates.md.

Orientation (experimental redstone) is always null in default worlds and is omitted.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from redsim.core.direction import NEIGHBOR_UPDATE_ORDER, Direction
from redsim.core.pos import Pos, offset
from redsim.sim import trace as tr

if TYPE_CHECKING:
    from redsim.sim.level import Level
    from redsim.world.block import Block, BlockState

#: ``SharedConstants.MAX_CHAINED_NEIGHBOR_UPDATES`` (server.properties default).
MAX_CHAINED_NEIGHBOR_UPDATES = 1_000_000


class _Update:
    """``CollectingNeighborUpdater.NeighborUpdates``."""

    __slots__ = ("cause",)

    def __init__(self, cause: int | None) -> None:
        self.cause = cause

    def run_next(self, level: Level) -> bool:
        raise NotImplementedError


class _ShapeUpdate(_Update):
    __slots__ = ("direction", "neighbor_state", "pos", "neighbor_pos", "flags", "limit")

    def __init__(
        self,
        cause: int | None,
        direction: Direction,
        neighbor_state: BlockState,
        pos: Pos,
        neighbor_pos: Pos,
        flags: int,
        limit: int,
    ) -> None:
        super().__init__(cause)
        self.direction = direction
        self.neighbor_state = neighbor_state
        self.pos = pos
        self.neighbor_pos = neighbor_pos
        self.flags = flags
        self.limit = limit

    def run_next(self, level: Level) -> bool:
        level.execute_shape_update(
            self.cause,
            self.direction,
            self.pos,
            self.neighbor_pos,
            self.neighbor_state,
            self.flags,
            self.limit,
        )
        return False


class _SimpleNeighborUpdate(_Update):
    __slots__ = ("pos", "source")

    def __init__(self, cause: int | None, pos: Pos, source: Block) -> None:
        super().__init__(cause)
        self.pos = pos
        self.source = source

    def run_next(self, level: Level) -> bool:
        state = level.get_block_state(self.pos)
        level.execute_neighbor_update(self.cause, state, self.pos, self.source, False, "single")
        return False


class _FullNeighborUpdate(_Update):
    __slots__ = ("state", "pos", "source", "moved_by_piston")

    def __init__(
        self, cause: int | None, state: BlockState, pos: Pos, source: Block, moved_by_piston: bool
    ) -> None:
        super().__init__(cause)
        self.state = state
        self.pos = pos
        self.source = source
        self.moved_by_piston = moved_by_piston

    def run_next(self, level: Level) -> bool:
        level.execute_neighbor_update(
            self.cause, self.state, self.pos, self.source, self.moved_by_piston, "full"
        )
        return False


class _MultiNeighborUpdate(_Update):
    __slots__ = ("source_pos", "source", "skip", "idx")

    def __init__(
        self, cause: int | None, source_pos: Pos, source: Block, skip: Direction | None
    ) -> None:
        super().__init__(cause)
        self.source_pos = source_pos
        self.source = source
        self.skip = skip
        self.idx = 0
        if NEIGHBOR_UPDATE_ORDER[0] is skip:
            self.idx += 1

    def run_next(self, level: Level) -> bool:
        direction = NEIGHBOR_UPDATE_ORDER[self.idx]
        self.idx += 1
        neighbor_pos = offset(self.source_pos, direction)
        state = level.get_block_state(neighbor_pos)
        level.execute_neighbor_update(
            self.cause, state, neighbor_pos, self.source, False, "multi", self.source_pos
        )
        if self.idx < len(NEIGHBOR_UPDATE_ORDER) and NEIGHBOR_UPDATE_ORDER[self.idx] is self.skip:
            self.idx += 1
        return self.idx < len(NEIGHBOR_UPDATE_ORDER)


class CollectingNeighborUpdater:
    def __init__(self, level: Level, max_chained: int = MAX_CHAINED_NEIGHBOR_UPDATES) -> None:
        self.level = level
        self.max_chained = max_chained
        self.stack: list[_Update] = []
        self.added_this_layer: list[_Update] = []
        self.count = 0
        self.skipped = 0

    @property
    def running(self) -> bool:
        return self.count > 0

    def _cause(self) -> int | None:
        return self.level.trace.current_cause

    # --- NeighborUpdater interface ------------------------------------------------------
    def shape_update(
        self,
        direction: Direction,
        neighbor_state: BlockState,
        pos: Pos,
        neighbor_pos: Pos,
        flags: int,
        limit: int,
    ) -> None:
        self._add_and_run(
            pos,
            _ShapeUpdate(self._cause(), direction, neighbor_state, pos, neighbor_pos, flags, limit),
        )

    def neighbor_changed(self, pos: Pos, source: Block) -> None:
        self._add_and_run(pos, _SimpleNeighborUpdate(self._cause(), pos, source))

    def neighbor_changed_full(
        self, state: BlockState, pos: Pos, source: Block, moved_by_piston: bool
    ) -> None:
        self._add_and_run(
            pos, _FullNeighborUpdate(self._cause(), state, pos, source, moved_by_piston)
        )

    def update_neighbors_at_except_from_facing(
        self, pos: Pos, source: Block, skip: Direction | None
    ) -> None:
        self._add_and_run(pos, _MultiNeighborUpdate(self._cause(), pos, source, skip))

    # --- CollectingNeighborUpdater internals --------------------------------------------
    def _add_and_run(self, pos: Pos, update: _Update) -> None:
        running_already = self.count > 0
        too_many = self.max_chained >= 0 and self.count >= self.max_chained
        self.count += 1
        if not too_many:
            if running_already:
                self.added_this_layer.append(update)
            else:
                self.stack.append(update)
        else:
            self.skipped += 1
            if self.count - 1 == self.max_chained:
                self.level.trace.emit(
                    tr.NOTE, pos, info="Too many chained neighbor updates. Skipping the rest."
                )
        if not running_already:
            self._run_updates()

    def _run_updates(self) -> None:
        try:
            while self.stack or self.added_this_layer:
                for update in reversed(self.added_this_layer):
                    self.stack.append(update)
                self.added_this_layer.clear()
                next_updates = self.stack[-1]
                while not self.added_this_layer:
                    if not next_updates.run_next(self.level):
                        self.stack.pop()
                        break
        finally:
            self.stack.clear()
            self.added_this_layer.clear()
            self.count = 0
