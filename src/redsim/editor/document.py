"""An editable world: the engine plus annotations, undo history and file I/O.

All edits go through engine actions, so editor placement, breaking and using behave like a
player in the game (``Action("place" | "break" | "use")``). Inspector edits use
``/setblock`` semantics (``Action("setblock")``), as documented in the UI. Edits are only
possible between ticks, like player input in the game.

History is one linear timeline (``redsim.sim.timeline``): every step and every edit is
recorded, and the user can seek to any earlier step. Undo rewinds to just before the most
recent edit; redo replays forward through the next one. Editing at an earlier point starts
a new branch (the old future is dropped). Section annotations are not part of the timeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from redsim.core.pos import Pos
from redsim.editor.annotations import Sections
from redsim.editor.placement import PlaceRequest, placement_state
from redsim.io import save as save_io
from redsim.sim.engine import Action, ActionError, Engine, StepInfo
from redsim.sim.level import Level
from redsim.sim.timeline import Timeline
from redsim.world import blocks
from redsim.world.block import Block, BlockState

FLOOR_HALF_SIZE = 16


class EditError(Exception):
    """An edit that cannot be applied (message is shown to the user)."""


@dataclass
class Document:
    engine: Engine = field(default_factory=Engine)
    sections: Sections = field(default_factory=Sections)
    path: Path | None = None
    dirty: bool = False
    revision: int = 0
    extra: dict[str, Any] = field(default_factory=dict)
    timeline: Timeline | None = None
    notice: str = ""

    def __post_init__(self) -> None:
        if self.timeline is None:
            self.timeline = Timeline(self.engine)

    @property
    def history(self) -> Timeline:
        assert self.timeline is not None
        return self.timeline

    # ------------------------------------------------------------------ creation
    @staticmethod
    def new_flat(floor_block: str = "minecraft:smooth_stone") -> Document:
        """A new world with a 32×32 floor at y=0 (placed without updates, like terrain)."""
        engine = Engine()
        state = blocks.parse_state(floor_block)
        for x in range(-FLOOR_HALF_SIZE, FLOOR_HALF_SIZE):
            for z in range(-FLOOR_HALF_SIZE, FLOOR_HALF_SIZE):
                engine.level.blocks[(x, 0, z)] = state
        return Document(engine=engine)

    @property
    def level(self) -> Level:
        return self.engine.level

    def state_at(self, pos: Pos) -> BlockState:
        return self.engine.level.get_block_state(pos)

    @property
    def can_edit(self) -> bool:
        return self.engine.at_tick_boundary()

    # ------------------------------------------------------------------ edits
    def _apply(self, action: Action, label: str) -> None:
        if not self.can_edit:
            raise EditError("Finish the current tick before editing (edits happen between ticks).")
        discarded = self.history.end - self.history.position
        try:
            self.history.apply(action)
        except ActionError as exc:
            raise EditError(str(exc)) from exc
        self.notice = f"Discarded {discarded} recorded later steps." if discarded else ""
        self._changed()

    def place(self, pos: Pos, block: Block, request: PlaceRequest) -> None:
        state = placement_state(block, request, self.engine.level, pos)
        if state is None:
            raise EditError(f"{block.name} cannot be placed there (needs support).")
        self._apply(Action("place", pos, repr(state)), f"place {block.name}")

    def break_block(self, pos: Pos) -> None:
        self._apply(Action("break", pos), f"break {self.state_at(pos).block.name}")

    def use(self, pos: Pos) -> None:
        self._apply(Action("use", pos), f"use {self.state_at(pos).block.name}")

    def setblock(self, pos: Pos, state: BlockState) -> None:
        """Inspector edit: ``/setblock`` semantics (shape-adjusted state, neighbor updates)."""
        self._apply(Action("setblock", pos, repr(state)), f"set {state.block.name}")

    def assign_section(self, pos: Pos, name: str | None) -> None:
        self.sections.assign(pos, name)
        self._changed()

    @staticmethod
    def is_usable(block: Block) -> bool:
        """Whether right-clicking the block does something (``useWithoutItem`` override)."""
        return type(block).use_without_item is not Block.use_without_item

    # ------------------------------------------------------------------ undo
    def undo(self) -> bool:
        """Rewind to just before the most recent edit (simulation steps after it go too)."""
        target = self.history.undo_target()
        if target is None:
            return False
        self.history.seek(target)
        self._changed()
        return True

    def redo(self) -> bool:
        """Replay forward through the next recorded edit."""
        target = self.history.redo_target()
        if target is None:
            return False
        self.history.seek(target)
        self._changed()
        return True

    # ------------------------------------------------------------------ simulation
    def step(self) -> StepInfo:
        info = self.history.step()
        self._changed(dirty=True)
        return info

    def run_tick(self) -> list[StepInfo]:
        steps = self.history.run_tick() if self.can_edit else self.history.finish_tick()
        self._changed(dirty=True)
        return steps

    def run_ticks(self, count: int) -> None:
        for _ in range(count):
            self.history.run_tick()
        self._changed(dirty=True)

    def step_back(self) -> bool:
        if not self.history.can_step_back():
            return False
        self.history.step_back()
        self._changed()
        return True

    def tick_back(self) -> bool:
        if not self.history.can_step_back():
            return False
        self.history.tick_back()
        self._changed()
        return True

    def seek(self, step_index: int) -> None:
        self.history.seek(step_index)
        self._changed()

    # ------------------------------------------------------------------ files
    def save(self, path: Path | None = None) -> None:
        target = path or self.path
        if target is None:
            raise EditError("No file name given.")
        extra = dict(self.extra)
        extra["sections"] = self.sections.to_json()
        save_io.save(target, self.engine, extra)
        self.path = target
        self.dirty = False

    @staticmethod
    def open(path: Path) -> Document:
        engine, extra = save_io.load(path)
        sections = (
            Sections.from_json(extra.pop("sections", {})) if "sections" in extra else Sections()
        )
        return Document(engine=engine, sections=sections, path=path, extra=extra)

    def _changed(self, dirty: bool = True) -> None:
        self.revision += 1
        if dirty:
            self.dirty = True
