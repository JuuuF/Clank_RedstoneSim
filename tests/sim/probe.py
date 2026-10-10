"""Test-only blocks that record what the engine does to them.

They are not registered in the block registry; ``Level`` only needs block instances.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from redsim.core.direction import Direction
from redsim.core.pos import Pos
from redsim.sim.level import Level
from redsim.world.block import Block, BlockState
from redsim.world.properties import integer

VALUE = integer("value", 0, 3)

Hook = Callable[[BlockState, Level, Pos], None]


class ProbeBlock(Block):
    """Logs hook calls as tuples into a shared list; behavior is injected per test."""

    properties = (VALUE,)

    def __init__(self, name: str, log: list[tuple[Any, ...]]) -> None:
        super().__init__(f"test:{name}")
        self.log = log
        self.on_neighbor: Hook | None = None
        self.on_tick: Hook | None = None
        self.on_event: Callable[[BlockState, Level, Pos, int, int], bool] | None = None
        self.on_shape: Callable[[BlockState, Direction], BlockState] | None = None
        self.log_place = False

    def neighbor_changed(
        self, state: BlockState, level: Level, pos: Pos, source: Block, moved_by_piston: bool
    ) -> None:
        self.log.append(("neighbor", self.name, pos, source.name))
        if self.on_neighbor is not None:
            self.on_neighbor(state, level, pos)

    def tick(self, state: BlockState, level: Level, pos: Pos) -> None:
        self.log.append(("tick", self.name, pos, level.game_time))
        if self.on_tick is not None:
            self.on_tick(state, level, pos)

    def trigger_event(self, state: BlockState, level: Level, pos: Pos, b0: int, b1: int) -> bool:
        self.log.append(("event", self.name, pos, (b0, b1)))
        if self.on_event is not None:
            return self.on_event(state, level, pos, b0, b1)
        return True

    def update_shape(
        self,
        state: BlockState,
        level: Level,
        pos: Pos,
        direction: Direction,
        neighbor_pos: Pos,
        neighbor: BlockState,
    ) -> BlockState:
        self.log.append(("shape", self.name, pos, direction.serialized))
        if self.on_shape is not None:
            return self.on_shape(state, direction)
        return state

    def on_place(
        self,
        state: BlockState,
        level: Level,
        pos: Pos,
        old_state: BlockState,
        moved_by_piston: bool,
    ) -> None:
        if self.log_place:
            self.log.append(("place", self.name, pos, state.get(VALUE)))

    def affect_neighbors_after_removal(
        self, state: BlockState, level: Level, pos: Pos, moved_by_piston: bool
    ) -> None:
        self.log.append(("removed", self.name, pos, moved_by_piston))
