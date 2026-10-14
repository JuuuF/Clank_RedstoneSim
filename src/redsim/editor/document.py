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

from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from redsim.core.pos import Pos, offset
from redsim.editor import sources
from redsim.editor.annotations import Sections
from redsim.editor.clipboard import Prefab, Region
from redsim.editor.document_common import EDIT_ROWS, FLOOR_HALF_SIZE, Vary, edit_row
from redsim.editor.document_history import EditBatch, EditError, HistoryOps, HistoryState
from redsim.editor.document_sequences import Pulse, SequenceOps
from redsim.editor.groups import Groups
from redsim.editor.lines import Lines
from redsim.editor.placement import PlaceRequest, placement_state
from redsim.io import save as save_io
from redsim.sim.engine import Action, ActionError, Engine
from redsim.sim.level import Level
from redsim.sim.timeline import Plan, Timeline
from redsim.world import blocks
from redsim.world.block import Block, BlockState
from redsim.world.blocks.container import ContainerBlockEntity, slot_limit
from redsim.world.rotation import default_pivot2, rotated_box


@dataclass
class Document(HistoryOps, SequenceOps):
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
    #: Timeline view (not saved; rebuilt as the history runs), in ticks since the base
    #: (tick 0): tick → step index at that tick boundary (after its edits), and recorded
    #: edit step index → tick.
    tick_steps: dict[int, int] = field(default_factory=dict)
    edit_ticks: dict[int, int] = field(default_factory=dict)
    #: Monitored blocks (saved) and their recorded values per tick (not saved).
    monitors: list[Pos] = field(default_factory=list)
    #: Named timeline markers (tick → name). Ticks before 0 can exist after "Set tick 0
    #: here" (kept so an undo brings them back); they are not shown or saved.
    markers: dict[int, str] = field(default_factory=dict)
    samples: dict[Pos, dict[int, int]] = field(default_factory=dict)
    #: Timeline lines of the sequence: groups of powered positions (saved).
    lines: Lines = field(default_factory=Lines)
    #: The other categories' timeline lines (Placed, Removed, …): groups of positions
    #: per category (saved).
    row_lines: dict[str, Lines] = field(default_factory=dict)
    #: The Minecraft save this document streams chunks from (``mcworld.stream.WorldStream``;
    #: not saved).
    world: Any = None
    _undo: list[HistoryState] = field(default_factory=list)
    _redo: list[HistoryState] = field(default_factory=list)
    _batch_depth: int = 0
    _batch_saved: bool = False

    def __post_init__(self) -> None:
        if self.timeline is None:
            self.timeline = Timeline(self.engine)
        self._observe()

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

    @property
    def tick(self) -> int:
        """Ticks since the base (tick 0, the build state)."""
        return self.history.tick()

    @property
    def end_tick(self) -> int:
        return max(self.history.end_tick(), self.tick)

    # ------------------------------------------------------------------ edits
    def _apply(self, action: Action, label: str) -> None:
        """Apply an edit. At tick 0 it changes the build state (not recorded, never
        replayed); later it is recorded at its tick. Edits at one tick form one batch."""
        if not self.can_edit:
            raise EditError("Finish the current tick before editing (edits happen between ticks).")
        history = self.history
        before = None if self._batch_saved else self._history_state()
        future = history.end_tick() - self.tick if history.position < history.end else 0
        index = history.position
        action = replace(action, label=label)
        try:
            if history.at_base:
                history.apply_to_base(action)
            else:
                history.apply(action)
        except ActionError as exc:
            raise EditError(str(exc)) from exc
        if before is not None:
            self._undo.append(replace(before, label=label))
            self._redo.clear()
            self._batch_saved = self._batch_depth > 0
        if future or history.at_base:
            self._forget_after(self.tick)
        if not history.at_base:
            self.edit_ticks[index] = self.tick
        if future:
            self.notice = f"Discarded the recorded {future} ticks after this point."
        self._changed()

    @contextmanager
    def batch(self) -> Iterator[None]:
        """Several edits as one undo step (e.g. a dragged line of blocks)."""
        self._batch_depth += 1
        try:
            yield
        finally:
            self._batch_depth -= 1
            if not self._batch_depth:
                self._batch_saved = False

    def place_many(
        self, positions: Iterable[Pos], block: Block, request: PlaceRequest, vary: Vary = None
    ) -> int:
        """Place ``block`` at each free position that can hold it, as one edit batch and one
        undo step; returns how many were placed. ``vary`` changes each placed state (the
        editor's turn/mirror/upside-down choice)."""
        placed = 0
        with self.batch():
            for pos in positions:
                if not self.state_at(pos).is_air:
                    continue
                state = placement_state(block, request, self.engine.level, pos)
                if state is not None and vary is not None:
                    state = vary(state)
                if state is None or not state.can_survive(self.engine.level, pos):
                    continue
                try:
                    self._apply(Action("place", pos, repr(state)), f"place {block.name}")
                except EditError:
                    continue
                placed += 1
        return placed

    def place(self, pos: Pos, block: Block, request: PlaceRequest, vary: Vary = None) -> None:
        state = placement_state(block, request, self.engine.level, pos)
        if state is not None and vary is not None:
            state = vary(state)
            if not state.can_survive(self.engine.level, pos):
                state = None
        if state is None:
            raise EditError(f"{block.name} cannot be placed there (needs support).")
        self._apply(Action("place", pos, repr(state)), f"place {block.name}")

    def break_block(self, pos: Pos) -> None:
        self._apply(Action("break", pos), f"break {self.state_at(pos).block.name}")

    def use(self, pos: Pos) -> None:
        self._apply(Action("use", pos), f"use {self.state_at(pos).block.name}")

    def place_source(
        self, pos: Pos, kind: str, strength: int, request: PlaceRequest, vary: Vary = None
    ) -> None:
        """Put a signal source of ``strength`` at ``pos``: the backing block, oriented like a
        player would place it, set with its block-entity data (``/setblock … {…}``)."""
        block = blocks.get(sources.KINDS[kind].block_id)
        if not self.state_at(pos).is_air:
            raise EditError(f"position {pos} is occupied")
        oriented = placement_state(block, request, self.engine.level, pos)
        if oriented is not None and vary is not None:
            oriented = vary(oriented)
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

    def projectile_hit(self, pos: Pos, strength: int, arrow: bool) -> None:
        """A projectile hitting a target block: it hits in the next tick's entity phase and
        powers the target for 20 ticks (arrow) or 8 (other projectiles)."""
        if not self.state_at(pos).is_(blocks.TARGET):
            raise EditError(f"No target block at {pos}.")
        payload = {"strength": strength, "ticks": 20 if arrow else 8}
        self._apply(Action("projectile_hit", pos, payload=payload), "projectile hit")

    def plate_visitors(self, pos: Pos, mobs: int, others: int, ticks: int) -> None:
        """Entities standing on a pressure plate (entities are not simulated): ``mobs``
        (players count) and ``others`` (items, …) from the next tick on, for ``ticks``
        ticks; the plate presses in the entity phase and releases at its next recheck
        after they leave. Replaces earlier visitors of the plate."""
        from redsim.world.blocks.pressure_plate import BasePressurePlateBlock

        if not isinstance(self.state_at(pos).block, BasePressurePlateBlock):
            raise EditError(f"No pressure plate at {pos}.")
        payload = {"mobs": mobs, "others": others, "ticks": ticks}
        self._apply(Action("plate_visitors", pos, payload=payload), "step on a plate")

    # ------------------------------------------------------------------ sequences

    def set_container_slot(self, pos: Pos, slot: int | None, item: str | None, count: int) -> None:
        """Set one slot of a barrel or hopper (``slot=None``: empty them all), as
        ``/setblock`` with the block entity's data, so comparators update; a hopper keeps
        its transfer cooldown."""
        entity = self.level.get_block_entity(pos, create=False)
        if not isinstance(entity, ContainerBlockEntity):
            raise EditError(f"No container at {pos}.")
        data = entity.to_json()
        entries = [e for e in data["Items"] if slot is not None and e["Slot"] != slot]
        if slot is not None and item is not None and count > 0:
            entries.append({"Slot": slot, "id": item, "count": min(count, slot_limit(item))})
        data["Items"] = sorted(entries, key=lambda e: int(e["Slot"]))
        state = repr(self.state_at(pos))
        label = "empty container" if slot is None else f"slot {slot}"
        self._apply(Action("setblock", pos, state, payload={"nbt": data}), label)

    def turn_page(self, pos: Pos, page: int) -> None:
        """A player turning a lectern's page (comparator update and a 2-tick pulse)."""
        self._apply(Action("lectern_page", pos, payload={"page": page}), f"turn to page {page}")

    def set_state(self, pos: Pos, state: BlockState) -> None:
        """An inspector edit: ``setblock``, keeping a piston whole: extending a piston base
        this way also puts its head in front (if there is room), as one undo step. (The
        head of a retracted base removes itself through its shape update.)"""
        from redsim.world.blocks.piston import PistonBaseBlock
        from redsim.world.properties import EXTENDED, FACING, PISTON_TYPE

        block = state.block
        if not isinstance(block, PistonBaseBlock) or not state.get(EXTENDED):
            self.setblock(pos, state)
            return
        facing = state.get(FACING)
        front = offset(pos, facing)
        with self.batch():
            self.setblock(pos, state)
            if self.state_at(front).is_air:
                sticky = block.id == "minecraft:sticky_piston"
                head = blocks.PISTON_HEAD.default_state.with_(FACING, facing).with_(
                    PISTON_TYPE, "sticky" if sticky else "normal"
                )
                self.setblock(front, head)

    def setblock(self, pos: Pos, state: BlockState) -> None:
        """Inspector edit: ``/setblock`` semantics (shape-adjusted state, neighbor updates)."""
        self._apply(Action("setblock", pos, repr(state)), f"set {state.block.name}")

    # ------------------------------------------------------------------ regions
    def copy(self, region: Region) -> Prefab:
        """Capture a region into the clipboard (air included, block-entity data kept)."""
        self.clipboard = Prefab.capture(self.engine.level, region)
        return self.clipboard

    def paste(self, origin: Pos, prefab: Prefab | None = None) -> None:
        """Place a prefab with ``/clone … strict`` semantics (no block updates: pasting is an
        editor operation, so budded components stay budded), minimum corner at ``origin``."""
        source = prefab or self.clipboard
        if source is None:
            raise EditError("The clipboard is empty.")
        payload = {**source.payload(), "strict": True}
        self._apply(Action("clone", origin, payload=payload), f"paste {source.name}")

    def clone_region(self, region: Region, offset: Pos, mode: str = "move") -> Region:
        """Move (``mode="move"``) or copy (``"force"``) a region in place by ``offset``, as
        ``/clone <low> <high> <low + offset> strict replace <mode>``: one action, one undo
        step, no block updates, scheduled ticks inside come along. Returns the region at
        its new place."""
        if offset == (0, 0, 0):
            raise EditError("The selection did not move.")
        low = (region.low[0] + offset[0], region.low[1] + offset[1], region.low[2] + offset[2])
        payload = {
            "begin": list(region.low),
            "end": list(region.high),
            "mode": mode,
            "strict": True,
        }
        size = "×".join(str(v) for v in region.size)
        label = f"{'move' if mode == 'move' else 'copy'} {size} selection"
        self._apply(Action("clone_region", low, payload=payload), label)
        high = (region.high[0] + offset[0], region.high[1] + offset[1], region.high[2] + offset[2])
        return Region(low, high)

    def transform_region(
        self,
        region: Region,
        quarter_turns: int = 0,
        mirror: str | None = None,
        pivot2: tuple[int, int] | None = None,
    ) -> Region:
        """Rotate (clockwise seen from above, around ``pivot2``: twice the x/z point;
        default the box center) and/or mirror (``"x"``: east-west, ``"z"``: north-south) a
        selection in place; block states turn too, no block updates, pending ticks move
        along. One undo step. Returns the new box."""
        pivot = pivot2 if pivot2 is not None else default_pivot2(region.low, region.high)
        payload = {
            "begin": list(region.low),
            "end": list(region.high),
            "quarter_turns": quarter_turns,
            "mirror": mirror,
            "pivot2": list(pivot),
        }
        label = f"rotate {quarter_turns * 90}°" if quarter_turns else f"flip {mirror}"
        self._apply(Action("transform_region", region.low, payload=payload), label)
        low, high = rotated_box(region.low, region.high, quarter_turns, pivot)
        return Region(low, high)

    def stack_region(self, region: Region, step: Pos, count: int) -> Region:
        """``count`` copies of a selection, each ``step`` further (no block updates). One
        undo step. Returns the box around the original and all copies."""
        if count < 1:
            raise EditError("Nothing to stack.")
        payload = {
            "begin": list(region.low),
            "end": list(region.high),
            "step": list(step),
            "count": count,
        }
        self._apply(Action("stack_region", region.low, payload=payload), f"stack ×{count}")
        far_low = tuple(region.low[i] + step[i] * count for i in range(3))
        far_high = tuple(region.high[i] + step[i] * count for i in range(3))
        return Region.from_corners(
            tuple(min(region.low[i], far_low[i]) for i in range(3)),  # type: ignore[arg-type]
            tuple(max(region.high[i], far_high[i]) for i in range(3)),  # type: ignore[arg-type]
        )

    def rotate_clipboard(self, quarter_turns: int = 1) -> None:
        if self.clipboard is not None:
            self.clipboard = self.clipboard.rotated(quarter_turns)

    def mirror_clipboard(self, axis: str) -> None:
        if self.clipboard is not None:
            self.clipboard = self.clipboard.mirrored(axis)

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

    # ------------------------------------------------------------------ world chunks
    def add_world_blocks(
        self, states: dict[Pos, BlockState], entities: dict[Pos, dict[str, Any]]
    ) -> None:
        """Blocks of newly loaded chunks (and their block entities' saved data): they join
        the current level and every stored one (keyframes, undo bases) as if they had
        always been there, without updates. Positions a level already has stay as they
        are. Not an edit: nothing to undo, the document is not changed by it."""
        history = self.history
        levels = {id(self.level): self.level}
        for snapshot in history.keyframes.values():
            levels[id(snapshot.level)] = snapshot.level
        for stored in (*self._undo, *self._redo):
            levels[id(stored.base.level)] = stored.base.level
        for level in levels.values():
            fresh = {pos: state for pos, state in states.items() if pos not in level.blocks}
            level.add_blocks(fresh)
            for pos, data in entities.items():
                state = fresh.get(pos)
                if state is None or not state.has_block_entity:
                    continue
                entity = state.block.new_block_entity(pos, state)
                if entity is not None:
                    entity.load_json(data)
                    level.set_block_entity(entity)
        self.revision += 1

    # ------------------------------------------------------------------ undo

    # ------------------------------------------------------------------ markers

    # ------------------------------------------------------------------ edit batches

    # ------------------------------------------------------------------ simulation

    def lines_of(self, row: str) -> Lines:
        """The timeline lines of category ``row`` (``EDIT_ROWS``): Powered or another."""
        if row == "power":
            return self.lines
        return self.row_lines.setdefault(row, Lines())

    # ------------------------------------------------------------------ files
    def save(self, path: Path | None = None) -> None:
        target = path or self.path
        if target is None:
            raise EditError("No file name given.")
        extra = dict(self.extra)
        extra["sections"] = self.sections.to_json()
        extra["groups"] = self.groups.to_json()
        extra["prefabs"] = {name: prefab.to_json() for name, prefab in self.prefabs.items()}
        extra["monitors"] = [list(pos) for pos in self.monitors]
        extra["line_groups"] = self.lines.to_json()
        extra["row_line_groups"] = {
            row: lines.to_json() for row, lines in self.row_lines.items() if lines.groups
        }
        history = self.history
        if history.inputs:  # the recorded edits (sequences too) and the build they start from
            base = Engine()
            base.restore(history.base)
            extra["history"] = {
                "base": save_io.engine_to_json(base),
                "plan": {
                    str(tick): [action.to_json() for action in actions]
                    for tick, actions in history.plan().items()
                },
                "end_tick": self.end_tick,
                "tick": self.tick,
            }
        else:
            extra.pop("history", None)
        extra["markers"] = {str(tick): name for tick, name in self.visible_markers().items()}
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
        monitors = [(int(x), int(y), int(z)) for x, y, z in extra.pop("monitors", [])]
        lines = Lines.from_json(extra.pop("line_groups", []))
        row_lines = {
            str(row): Lines.from_json(data)
            for row, data in extra.pop("row_line_groups", {}).items()
        }
        markers = {int(tick): str(name) for tick, name in extra.pop("markers", {}).items()}
        history = extra.pop("history", None)
        document = Document(
            engine=engine,
            sections=sections,
            path=path,
            extra=extra,
            groups=groups,
            prefabs=prefabs,
            monitors=monitors,
            markers=markers,
            lines=lines,
            row_lines=row_lines,
        )
        if isinstance(history, dict) and history.get("plan"):
            # Re-run the recorded edits from the saved build (the file's own state is
            # the result at the saved tick, recomputed here).
            base = save_io.engine_from_json(history["base"]).snapshot()
            plan: Plan = {
                int(tick): [Action.from_json(a) for a in actions]
                for tick, actions in history["plan"].items()
            }
            end, tick = int(history.get("end_tick", 0)), int(history.get("tick", 0))
            document._rebuild(HistoryState(base, plan, end, tick))
            document.dirty = False
        return document

    # ------------------------------------------------------------------ timeline view

    def toggle_monitor(self, pos: Pos) -> bool:
        """Add or remove a block from the timeline monitor; returns whether it is monitored."""
        if pos in self.monitors:
            self.monitors.remove(pos)
            self.samples.pop(pos, None)
            self._changed(dirty=True)
            return False
        self.monitors.append(pos)
        self._changed(dirty=True)
        return True

    def _changed(self, dirty: bool = True) -> None:
        self._observe()
        self.revision += 1
        if dirty:
            self.dirty = True


__all__ = [
    "Document",
    "EDIT_ROWS",
    "EditBatch",
    "EditError",
    "FLOOR_HALF_SIZE",
    "HistoryState",
    "Pulse",
    "Vary",
    "edit_row",
]
