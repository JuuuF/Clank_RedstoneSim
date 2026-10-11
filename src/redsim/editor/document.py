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

from redsim.core.pos import Pos
from redsim.editor import sources
from redsim.editor.annotations import Sections
from redsim.editor.clipboard import Prefab, Region
from redsim.editor.groups import Groups
from redsim.editor.monitor import monitor_value
from redsim.editor.placement import PlaceRequest, placement_state
from redsim.io import save as save_io
from redsim.sim.engine import Action, ActionError, Engine, EngineSnapshot, StepInfo
from redsim.sim.level import Level
from redsim.sim.timeline import Plan, Timeline
from redsim.world import blocks
from redsim.world.block import Block, BlockState
from redsim.world.blocks.container import ContainerBlockEntity, slot_limit
from redsim.world.rotation import default_pivot2, rotated_box

FLOOR_HALF_SIZE = 16


class EditError(Exception):
    """An edit that cannot be applied (message is shown to the user)."""


#: Timeline rows for recorded edits (color-coded in the UI).
EDIT_ROWS = ("build", "remove", "edit", "interact")


def edit_row(action: Action) -> str:
    """Which timeline row an edit belongs to: placing blocks, removing them, changing
    placed blocks (inspector, selections), or interacting like a player."""
    kind = action.kind
    if kind in ("use", "lectern_page", "projectile_hit", "container_item"):
        return "interact"
    if kind == "break":
        return "remove"
    if kind in ("fill", "setblock", "set_block"):
        if (action.state or "").split("[")[0] in ("minecraft:air", "air"):
            return "remove"
        return "build" if kind == "fill" or action.label.startswith("place") else "edit"
    if kind in ("place", "clone", "stack_region"):
        return "build"
    return "edit"


@dataclass(frozen=True)
class HistoryState:
    """Everything that defines the recorded history; undo and redo restore one."""

    base: EngineSnapshot
    plan: Plan
    end_tick: int
    tick: int  # where the user was


@dataclass(frozen=True)
class EditBatch:
    """The edits of one row at one tick (one keyframe diamond)."""

    tick: int
    row: str
    indices: tuple[int, ...]
    labels: tuple[str, ...]


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
    #: Timeline view (not saved; rebuilt as the history runs), in ticks since the base
    #: (tick 0): tick → step index at that tick boundary (after its edits), and recorded
    #: edit step index → tick.
    tick_steps: dict[int, int] = field(default_factory=dict)
    edit_ticks: dict[int, int] = field(default_factory=dict)
    #: Monitored blocks (saved) and their recorded values per tick (not saved).
    monitors: list[Pos] = field(default_factory=list)
    samples: dict[Pos, dict[int, int]] = field(default_factory=dict)
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
            self._undo.append(before)
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

    def place_many(self, positions: Iterable[Pos], block: Block, request: PlaceRequest) -> int:
        """Place ``block`` at each free position that can hold it, as one edit batch and one
        undo step; returns how many were placed."""
        placed = 0
        with self.batch():
            for pos in positions:
                if not self.state_at(pos).is_air:
                    continue
                state = placement_state(block, request, self.engine.level, pos)
                if state is None:
                    continue
                try:
                    self._apply(Action("place", pos, repr(state)), f"place {block.name}")
                except EditError:
                    continue
                placed += 1
        return placed

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

    def projectile_hit(self, pos: Pos, strength: int, arrow: bool) -> None:
        """A projectile hitting a target block: it hits in the next tick's entity phase and
        powers the target for 20 ticks (arrow) or 8 (other projectiles)."""
        if not self.state_at(pos).is_(blocks.TARGET):
            raise EditError(f"No target block at {pos}.")
        payload = {"strength": strength, "ticks": 20 if arrow else 8}
        self._apply(Action("projectile_hit", pos, payload=payload), "projectile hit")

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

    # ------------------------------------------------------------------ undo
    def _history_state(self) -> HistoryState:
        history = self.history
        return HistoryState(history.base, history.plan(), self.end_tick, self.tick)

    def undo(self) -> bool:
        """Undo the last edit (or edit batch, history change): the history is rebuilt
        without it, the simulation re-run, and the view returns to where it was made."""
        if not self._undo or not self.can_edit:
            return False
        current = self._history_state()
        self._redo.append(current)
        state = self._undo.pop()
        # Keep the simulated length: the history is re-run without the edit.
        self._rebuild(replace(state, end_tick=max(state.end_tick, current.end_tick)))
        return True

    def redo(self) -> bool:
        if not self._redo or not self.can_edit:
            return False
        self._undo.append(self._history_state())
        self._rebuild(self._redo.pop())
        return True

    def _rebuild(self, state: HistoryState) -> list[tuple[int, Action, str]]:
        """Re-create the history from a base and an edit plan, re-running the simulation."""
        self.tick_steps, self.edit_ticks = {}, {}
        for values in self.samples.values():
            values.clear()
        history = self.history
        failures = history.rewrite(state.base, state.plan, state.end_tick, self._observe)
        self.edit_ticks = {i: t - history.base_time for i, t in history.input_times.items()}
        self.seek_tick(min(state.tick, self.end_tick))
        self._changed()
        return failures

    # ------------------------------------------------------------------ edit batches
    def edit_batches(self) -> list[EditBatch]:
        """The recorded edits grouped by tick and row (the timeline's keyframes)."""
        grouped: dict[tuple[int, str], list[int]] = {}
        for index in sorted(self.history.inputs):
            action = self.history.inputs[index]
            key = (self.edit_ticks.get(index, 0), edit_row(action))
            grouped.setdefault(key, []).append(index)
        return [
            EditBatch(
                tick,
                row,
                tuple(indices),
                tuple(self.history.inputs[i].label or self.history.inputs[i].kind for i in indices),
            )
            for (tick, row), indices in sorted(grouped.items())
        ]

    def _replan(self, new_ticks: dict[int, int | None], label: str) -> int:
        """Move recorded edits (index → new tick; None deletes) and rebuild the history.
        Tick 0 folds edits into the build state. Returns how many edits failed."""
        if not self.can_edit:
            raise EditError("Finish the current tick first.")
        history = self.history
        before = self._history_state()
        moved: list[tuple[int, int, Action]] = []
        for index in sorted(history.inputs):
            tick = new_ticks[index] if index in new_ticks else self.edit_ticks.get(index, 0)
            if tick is None:
                continue
            moved.append((max(0, tick), index, history.inputs[index]))
        plan: Plan = {}
        for tick, _, action in sorted(moved, key=lambda m: (m[0], m[1])):
            plan.setdefault(tick, []).append(action)
        failures = self._rebuild(HistoryState(before.base, plan, before.end_tick, before.tick))
        self._undo.append(before)
        self._redo.clear()
        self.notice = f"{label}." + (
            f" {len(failures)} edits could not be applied there and were dropped."
            if failures
            else ""
        )
        return len(failures)

    def move_edits(self, indices: Iterable[int], delta: int) -> int:
        """Shift recorded edits by ``delta`` ticks (to tick 0 or earlier: into the build)."""
        new_ticks: dict[int, int | None] = {i: self.edit_ticks.get(i, 0) + delta for i in indices}
        return self._replan(new_ticks, f"Moved {len(new_ticks)} edits by {delta:+d} ticks")

    def merge_edits(self, indices: Iterable[int], tick: int | None = None) -> int:
        """Gather recorded edits into one tick (default: the earliest of them), keeping
        their order."""
        chosen = list(indices)
        if not chosen:
            return 0
        target = min(self.edit_ticks.get(i, 0) for i in chosen) if tick is None else tick
        where = "the build (tick 0)" if target == 0 else f"tick {target}"
        new_ticks: dict[int, int | None] = {i: target for i in chosen}
        return self._replan(new_ticks, f"Merged {len(chosen)} edits into {where}")

    def delete_edits(self, indices: Iterable[int]) -> int:
        new_ticks: dict[int, int | None] = {i: None for i in indices}
        return self._replan(new_ticks, f"Deleted {len(new_ticks)} edits")

    def set_tick_zero(self) -> None:
        """Make the current state the build state (tick 0); the history before it goes."""
        if not self.can_edit:
            raise EditError("Finish the current tick first.")
        self._undo.append(self._history_state())
        self._redo.clear()
        self.history.rebase()
        self.tick_steps, self.edit_ticks = {}, {}
        for values in self.samples.values():
            values.clear()
        self._changed()

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
            self._observe()
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

    def jump(self, where: str) -> bool:
        """Blender-like jumps: ``"start"`` (tick 0) / ``"end"`` of the recorded history, or
        the tick of the ``"previous"``/``"next"`` edit batch (after its edits). False if
        already there."""
        history = self.history
        position = history.position
        if where == "start":
            target = history.start
        elif where == "end":
            target = history.end
        else:
            ticks = sorted(set(self.edit_ticks.values()))
            if where == "previous":
                earlier = [t for t in ticks if t < self.tick]
                if earlier:
                    return self.seek_tick(max(earlier))
                target = history.start
            else:
                later = [t for t in ticks if t > self.tick]
                return bool(later) and self.seek_tick(min(later))
        if target == position:
            return False
        self.seek(target)
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
        extra["monitors"] = [list(pos) for pos in self.monitors]
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
        return Document(
            engine=engine,
            sections=sections,
            path=path,
            extra=extra,
            groups=groups,
            prefabs=prefabs,
            monitors=monitors,
        )

    # ------------------------------------------------------------------ timeline view
    def _observe(self) -> None:
        """Record where this tick boundary is in the history and sample monitored blocks."""
        engine, history = self.engine, self.history
        tick = self.tick
        if engine.at_tick_boundary():
            self.tick_steps[tick] = max(self.tick_steps.get(tick, -1), history.position)
            for pos in self.monitors:
                self.samples.setdefault(pos, {})[tick] = monitor_value(engine.level, pos)

    def _forget_after(self, tick: int) -> None:
        """An edit dropped the recorded future after ``tick``: drop what described it (and
        stale step positions, which the edit changed)."""
        self.tick_steps = {t: s for t, s in self.tick_steps.items() if t < tick}
        actions = set(self.history.action_indices())
        self.edit_ticks = {i: t for i, t in self.edit_ticks.items() if i in actions}
        for values in self.samples.values():
            for stale in [t for t in values if t > tick]:
                del values[stale]

    def seek_tick(self, tick: int) -> bool:
        """Scrub to a tick boundary of the recorded history (after that moment's edits)."""
        known = [t for t in self.tick_steps if t <= tick]
        if not known:
            return False
        self.seek(self.tick_steps[max(known)])
        return True

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
