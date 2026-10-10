"""An editable world: the engine plus annotations, undo history and file I/O.

All edits go through engine actions, so editor placement, breaking and using behave like a
player in the game (``Action("place" | "break" | "use")``). Inspector edits use
``/setblock`` semantics (``Action("setblock")``), as documented in the UI. Edits are only
possible between ticks, like player input in the game.

Undo/redo stores engine snapshots taken before each edit. Simulation steps are not undoable
here; rewinding the simulation belongs to the playback history (milestone 6).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from redsim.core.pos import Pos
from redsim.editor.annotations import Sections
from redsim.editor.placement import PlaceRequest, placement_state
from redsim.io import save as save_io
from redsim.sim.engine import Action, ActionError, Engine, EngineSnapshot, StepInfo
from redsim.sim.level import Level
from redsim.world import blocks
from redsim.world.block import Block, BlockState

FLOOR_HALF_SIZE = 16


class EditError(Exception):
    """An edit that cannot be applied (message is shown to the user)."""


@dataclass
class _UndoEntry:
    snapshot: EngineSnapshot
    sections: dict[str, Any]
    label: str


@dataclass
class Document:
    engine: Engine = field(default_factory=Engine)
    sections: Sections = field(default_factory=Sections)
    path: Path | None = None
    dirty: bool = False
    revision: int = 0
    extra: dict[str, Any] = field(default_factory=dict)
    _undo: list[_UndoEntry] = field(default_factory=list)
    _redo: list[_UndoEntry] = field(default_factory=list)

    # ------------------------------------------------------------------ creation
    @staticmethod
    def new_flat(floor_block: str = "minecraft:smooth_stone") -> Document:
        """A new world with a 32×32 floor at y=0 (placed without updates, like terrain)."""
        document = Document()
        state = blocks.parse_state(floor_block)
        for x in range(-FLOOR_HALF_SIZE, FLOOR_HALF_SIZE):
            for z in range(-FLOOR_HALF_SIZE, FLOOR_HALF_SIZE):
                document.engine.level.blocks[(x, 0, z)] = state
        return document

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
        entry = _UndoEntry(self.engine.snapshot(), self.sections.to_json(), label)
        try:
            self.engine.apply(action)
        except ActionError as exc:
            raise EditError(str(exc)) from exc
        self._undo.append(entry)
        self._redo.clear()
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
        if not self._undo or not self.can_edit:
            return False
        entry = self._undo.pop()
        self._redo.append(_UndoEntry(self.engine.snapshot(), self.sections.to_json(), entry.label))
        self.engine.restore(entry.snapshot)
        self.sections = Sections.from_json(entry.sections)
        self._changed()
        return True

    def redo(self) -> bool:
        if not self._redo or not self.can_edit:
            return False
        entry = self._redo.pop()
        self._undo.append(_UndoEntry(self.engine.snapshot(), self.sections.to_json(), entry.label))
        self.engine.restore(entry.snapshot)
        self.sections = Sections.from_json(entry.sections)
        self._changed()
        return True

    # ------------------------------------------------------------------ simulation
    def step(self) -> StepInfo:
        info = self.engine.step()
        self._changed(dirty=True)
        return info

    def run_tick(self) -> list[StepInfo]:
        steps = self.engine.run_tick()
        self._changed(dirty=True)
        return steps

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
