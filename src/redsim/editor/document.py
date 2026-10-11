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
from redsim.editor import sources
from redsim.editor.annotations import Sections
from redsim.editor.clipboard import Prefab, Region
from redsim.editor.groups import Groups
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
    groups: Groups = field(default_factory=Groups)
    prefabs: dict[str, Prefab] = field(default_factory=dict)
    clipboard: Prefab | None = None

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

    def place_source(self, pos: Pos, kind: str, strength: int, request: PlaceRequest) -> None:
        """Put a signal source of ``strength`` at ``pos``: the backing block, oriented like a
        player would place it, set with its block-entity data (``/setblock … {…}``)."""
        block = blocks.get(sources.KINDS[kind].block_id)
        if not self.state_at(pos).is_air:
            raise EditError(f"position {pos} is occupied")
        oriented = placement_state(block, request, self.engine.level, pos)
        if oriented is None or not oriented.can_survive(self.engine.level, pos):
            raise EditError(f"{block.name} cannot be placed there (needs support).")
        self._set_source(pos, kind, strength, oriented)

    def set_source(self, pos: Pos, kind: str, strength: int) -> None:
        """Change a source's strength or swap its backing block in place (keeps facing)."""
        self._set_source(pos, kind, strength, self.state_at(pos))

    def _set_source(self, pos: Pos, kind: str, strength: int, oriented: BlockState) -> None:
        text, nbt = sources.source_setblock(kind, strength, oriented)
        actual = sources.nearest_strength(kind, strength)
        payload = {"nbt": nbt} if nbt is not None else None
        label = f"{sources.KINDS[kind].title} source {actual}"
        self._apply(Action("setblock", pos, text, payload=payload), label)
        if actual != strength:
            self.notice = f"{sources.KINDS[kind].title} cannot give {strength}; using {actual}."

    def turn_page(self, pos: Pos, page: int) -> None:
        """A player turning a lectern's page (comparator update and a 2-tick pulse)."""
        self._apply(Action("lectern_page", pos, payload={"page": page}), f"turn to page {page}")

    def setblock(self, pos: Pos, state: BlockState) -> None:
        """Inspector edit: ``/setblock`` semantics (shape-adjusted state, neighbor updates)."""
        self._apply(Action("setblock", pos, repr(state)), f"set {state.block.name}")

    # ------------------------------------------------------------------ regions
    def copy(self, region: Region) -> Prefab:
        """Capture a region into the clipboard (air included, block-entity data kept)."""
        self.clipboard = Prefab.capture(self.engine.level, region)
        return self.clipboard

    def paste(self, origin: Pos, prefab: Prefab | None = None) -> None:
        """Place a prefab with ``/clone`` semantics, its minimum corner at ``origin``."""
        source = prefab or self.clipboard
        if source is None:
            raise EditError("The clipboard is empty.")
        self._apply(Action("clone", origin, payload=source.payload()), f"paste {source.name}")

    def clone_region(self, region: Region, offset: Pos, mode: str = "move") -> Region:
        """Move (``mode="move"``) or copy (``"force"``) a region in place by ``offset``, as
        ``/clone <low> <high> <low + offset> replace <mode>``: one action, one undo step,
        scheduled ticks inside come along. Returns the region at its new place."""
        if offset == (0, 0, 0):
            raise EditError("The selection did not move.")
        low = (region.low[0] + offset[0], region.low[1] + offset[1], region.low[2] + offset[2])
        payload = {"begin": list(region.low), "end": list(region.high), "mode": mode}
        size = "×".join(str(v) for v in region.size)
        label = f"{'move' if mode == 'move' else 'copy'} {size} selection"
        self._apply(Action("clone_region", low, payload=payload), label)
        high = (region.high[0] + offset[0], region.high[1] + offset[1], region.high[2] + offset[2])
        return Region(low, high)

    def rotate_clipboard(self, quarter_turns: int = 1) -> None:
        if self.clipboard is not None:
            self.clipboard = self.clipboard.rotated(quarter_turns)

    def fill(self, region: Region, state: BlockState) -> None:
        """``/fill`` in replace mode (used to delete a region with air)."""
        action = Action("fill", region.low, repr(state), payload={"to": list(region.high)})
        self._apply(action, f"fill {state.block.name}")

    def save_prefab(self, name: str, region: Region) -> Prefab:
        prefab = Prefab.capture(self.engine.level, region, name)
        self.prefabs[name] = prefab
        self._changed()
        return prefab

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
        extra["groups"] = self.groups.to_json()
        extra["prefabs"] = {name: prefab.to_json() for name, prefab in self.prefabs.items()}
        save_io.save(target, self.engine, extra)
        self.path = target
        self.dirty = False

    @staticmethod
    def open(path: Path) -> Document:
        engine, extra = save_io.load(path)
        raw_sections = extra.pop("sections", None)
        sections = Sections.from_json(raw_sections) if raw_sections is not None else Sections()
        groups = Groups.from_json(extra.pop("groups", []))
        prefabs = {name: Prefab.from_json(data) for name, data in extra.pop("prefabs", {}).items()}
        return Document(
            engine=engine,
            sections=sections,
            path=path,
            extra=extra,
            groups=groups,
            prefabs=prefabs,
        )

    def _changed(self, dirty: bool = True) -> None:
        self.revision += 1
        if dirty:
            self.dirty = True
