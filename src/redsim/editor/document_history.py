"""The document's history: running and stepping the simulation, seeking, undo and redo
(whole history states), edit batches moved, merged or deleted, tick 0, markers, and what
the timeline view records per tick."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any, cast

from redsim.editor.document_common import edit_row
from redsim.editor.monitor import monitor_value
from redsim.sim.engine import Action, EngineSnapshot, StepInfo
from redsim.sim.timeline import Plan

if TYPE_CHECKING:
    from redsim.editor.document import Document


class HistoryOps:
    """Part of ``Document`` (a mixin; its methods run on it)."""

    def _history_state(self) -> HistoryState:
        """The history as it stands, including recorded edits that a deferred re-run
        (``Document.deferred``) holds aside for now."""
        view = cast("Document", self)
        history = view.history
        plan, end_tick = history.plan(), view.end_tick
        kept = view._kept_future
        if kept is not None:
            future, kept_end = kept
            for tick, actions in sorted(future.items()):
                plan.setdefault(tick, []).extend(actions)
            end_tick = max(end_tick, kept_end)
        return HistoryState(history.base, plan, end_tick, view.tick)

    def undo(self) -> bool:
        """Undo the last edit (or edit batch, history change): the history is rebuilt
        without it, the simulation re-run, and the view returns to where it was made."""
        view = cast("Document", self)
        return view.undo_to(1)

    def undo_to(self, count: int) -> bool:
        """Undo the last ``count`` steps at once (one re-run of the simulation)."""
        view = cast("Document", self)
        if not view._undo or not view.can_edit or count < 1:
            return False
        current = state = view._history_state()
        for _ in range(min(count, len(view._undo))):
            previous = view._undo.pop()
            view._redo.append(
                replace(
                    state,
                    label=previous.label,
                    shift=previous.shift,
                    selection=previous.selection,
                )
            )
            view._shift_markers(previous.shift)
            if previous.selection is not None:
                view.restored_selection = previous.selection[0]
            state = previous
        # Keep the simulated length: the history is re-run without the edits.
        view._rebuild(replace(state, end_tick=max(state.end_tick, current.end_tick)))
        return True

    def redo(self) -> bool:
        view = cast("Document", self)
        if not view._redo or not view.can_edit:
            return False
        state = view._redo.pop()
        view._undo.append(
            replace(
                view._history_state(),
                label=state.label,
                shift=state.shift,
                selection=state.selection,
            )
        )
        view._shift_markers(-state.shift)
        if state.selection is not None:
            view.restored_selection = state.selection[1]
        view._rebuild(state)
        return True

    def set_marker(self, tick: int, name: str) -> None:
        """Name a tick on the timeline (Blender's markers); an empty name removes it."""
        view = cast("Document", self)
        if name:
            view.markers[tick] = name
        else:
            view.markers.pop(tick, None)
        view._changed(dirty=True)

    def visible_markers(self) -> dict[int, str]:
        view = cast("Document", self)
        return {tick: name for tick, name in sorted(view.markers.items()) if tick >= 0}

    def _shift_markers(self, delta: int) -> None:
        view = cast("Document", self)
        if delta:
            view.markers = {tick + delta: name for tick, name in view.markers.items()}

    def note_selection(self, before: Iterable[Any], after: Iterable[Any]) -> None:
        """Remember the selection boxes around the last edit (see ``HistoryState``)."""
        view = cast("Document", self)
        if view._undo:
            view._undo[-1] = replace(view._undo[-1], selection=(tuple(before), tuple(after)))

    @property
    def undo_labels(self) -> list[str]:
        """What each undo step reverts, the most recent first."""
        view = cast("Document", self)
        return [state.label for state in reversed(view._undo)]

    def _rebuild(self, state: HistoryState) -> list[tuple[int, Action, str]]:
        """Re-create the history from a base and an edit plan, re-running the simulation."""
        view = cast("Document", self)
        view.tick_steps, view.edit_ticks = {}, {}
        for values in view.samples.values():
            values.clear()
        history = view.history
        failures = history.rewrite(state.base, state.plan, state.end_tick, view._observe)
        view.edit_ticks = {i: t - history.base_time for i, t in history.input_times.items()}
        view.seek_tick(min(state.tick, view.end_tick))
        view._changed()
        return failures

    def edit_batches(self) -> list[EditBatch]:
        """The recorded edits grouped by tick and row (the timeline's keyframes)."""
        view = cast("Document", self)
        grouped: dict[tuple[int, str], list[int]] = {}
        for index in sorted(view.history.inputs):
            action = view.history.inputs[index]
            key = (view.edit_ticks.get(index, 0), edit_row(action))
            grouped.setdefault(key, []).append(index)
        return [
            EditBatch(
                tick,
                row,
                tuple(indices),
                tuple(view.history.inputs[i].label or view.history.inputs[i].kind for i in indices),
            )
            for (tick, row), indices in sorted(grouped.items())
        ]

    def _replan(self, new_ticks: dict[int, int | None], label: str) -> int:
        """Move recorded edits (index → new tick; None deletes) and rebuild the history.
        Tick 0 folds edits into the build state. Returns how many edits failed."""
        view = cast("Document", self)
        if not view.can_edit:
            raise EditError("Finish the current tick first.")
        history = view.history
        before = view._history_state()
        moved: list[tuple[int, int, Action]] = []
        for index in sorted(history.inputs):
            tick = new_ticks[index] if index in new_ticks else view.edit_ticks.get(index, 0)
            if tick is None:
                continue
            moved.append((max(0, tick), index, history.inputs[index]))
        plan: Plan = {}
        for tick, _, action in sorted(moved, key=lambda m: (m[0], m[1])):
            plan.setdefault(tick, []).append(action)
        failures = view._rebuild(HistoryState(before.base, plan, before.end_tick, before.tick))
        view._undo.append(replace(before, label=label))
        view._redo.clear()
        view.notice = f"{label}." + (
            f" {len(failures)} edits could not be applied there and were dropped."
            if failures
            else ""
        )
        return len(failures)

    def move_edits(self, indices: Iterable[int], delta: int) -> int:
        """Shift recorded edits by ``delta`` ticks (to tick 0 or earlier: into the build)."""
        view = cast("Document", self)
        new_ticks: dict[int, int | None] = {i: view.edit_ticks.get(i, 0) + delta for i in indices}
        return view._replan(new_ticks, f"Moved {len(new_ticks)} edits by {delta:+d} ticks")

    def merge_edits(self, indices: Iterable[int], tick: int | None = None) -> int:
        """Gather recorded edits into one tick (default: the earliest of them), keeping
        their order."""
        view = cast("Document", self)
        chosen = list(indices)
        if not chosen:
            return 0
        target = min(view.edit_ticks.get(i, 0) for i in chosen) if tick is None else tick
        where = "the build (tick 0)" if target == 0 else f"tick {target}"
        new_ticks: dict[int, int | None] = {i: target for i in chosen}
        return view._replan(new_ticks, f"Merged {len(chosen)} edits into {where}")

    def delete_edits(self, indices: Iterable[int]) -> int:
        view = cast("Document", self)
        new_ticks: dict[int, int | None] = {i: None for i in indices}
        return view._replan(new_ticks, f"Deleted {len(new_ticks)} edits")

    def set_tick_zero(self) -> None:
        """ "Set tick 0 here": the current state becomes the build (tick 0), e.g. after
        running a few ticks so a new redstone block has updated its circuit. The history
        before it goes; edits recorded later move along (their ticks shift) and the
        simulated length is kept. One undo step."""
        view = cast("Document", self)
        if not view.can_edit:
            raise EditError("Finish the current tick first.")
        history = view.history
        if history.at_base:
            view.notice = "This is already tick 0."
            return
        before = view._history_state()
        here = view.tick
        later: Plan = {}
        for index in sorted(history.inputs):
            tick = history.input_times[index] - history.base_time
            if tick > here or (tick == here and index >= history.position):
                later.setdefault(tick - here, []).append(history.inputs[index])
        end = max(0, before.end_tick - here)
        history.rebase()
        view._rebuild(HistoryState(history.base, later, end, 0))
        view._undo.append(replace(before, label=f"set tick {here} as tick 0", shift=here))
        view._redo.clear()
        view._shift_markers(-here)
        view.notice = f"Tick {here} is now tick 0 (the build)."

    def step(self) -> StepInfo:
        view = cast("Document", self)
        info = view.history.step()
        view._changed(dirty=True)
        return info

    def run_tick(self) -> list[StepInfo]:
        view = cast("Document", self)
        steps = view.history.run_tick() if view.can_edit else view.history.finish_tick()
        view._changed(dirty=True)
        return steps

    def run_tick_until(self, deadline: float) -> tuple[list[StepInfo], bool]:
        """Run the current tick until ``deadline`` (``time.perf_counter``); True once it
        is complete. Views refresh only at the boundary (``revision``): a half-run tick
        is never shown."""
        view = cast("Document", self)
        steps, done = view.history.run_tick_until(deadline)
        if done:
            view._changed(dirty=True)
        elif steps:
            view.dirty = True
        return steps, done

    def run_ticks(self, count: int) -> None:
        view = cast("Document", self)
        for _ in range(count):
            view.history.run_tick()
            view._observe()
        view._changed(dirty=True)

    def step_back(self) -> bool:
        view = cast("Document", self)
        if not view.history.can_step_back():
            return False
        view.history.step_back()
        view._changed()
        return True

    def tick_back(self) -> bool:
        view = cast("Document", self)
        if not view.history.can_step_back():
            return False
        view.history.tick_back()
        view._changed()
        return True

    def jump(self, where: str) -> bool:
        """Blender-like jumps: ``"start"`` (tick 0) / ``"end"`` of the recorded history, or
        the tick of the ``"previous"``/``"next"`` edit batch (after its edits). False if
        already there."""
        view = cast("Document", self)
        history = view.history
        position = history.position
        if where == "start":
            target = history.start
        elif where == "end":
            target = history.end
        else:
            ticks = sorted(set(view.edit_ticks.values()))
            if where == "previous":
                earlier = [t for t in ticks if t < view.tick]
                if earlier:
                    return view.seek_tick(max(earlier))
                target = history.start
            else:
                later = [t for t in ticks if t > view.tick]
                return bool(later) and view.seek_tick(min(later))
        if target == position:
            return False
        view.seek(target)
        return True

    def seek(self, step_index: int) -> None:
        view = cast("Document", self)
        view.history.seek(step_index)
        view._changed()

    def _observe(self) -> None:
        """Record where this tick boundary is in the history and sample monitored blocks."""
        view = cast("Document", self)
        engine, history = view.engine, view.history
        tick = view.tick
        if engine.at_tick_boundary():
            view.tick_steps[tick] = max(view.tick_steps.get(tick, -1), history.position)
            for pos in view.monitors:
                view.samples.setdefault(pos, {})[tick] = monitor_value(engine.level, pos)

    def _forget_after(self, tick: int) -> None:
        """An edit dropped the recorded future after ``tick``: drop what described it (and
        stale step positions, which the edit changed)."""
        view = cast("Document", self)
        view.tick_steps = {t: s for t, s in view.tick_steps.items() if t < tick}
        actions = set(view.history.action_indices())
        view.edit_ticks = {i: t for i, t in view.edit_ticks.items() if i in actions}
        for values in view.samples.values():
            for stale in [t for t in values if t > tick]:
                del values[stale]

    def seek_tick(self, tick: int) -> bool:
        """Scrub to a tick boundary of the recorded history (after that moment's edits)."""
        view = cast("Document", self)
        known = [t for t in view.tick_steps if t <= tick]
        if not known:
            return False
        view.seek(view.tick_steps[max(known)])
        return True


class EditError(Exception):
    """An edit that cannot be applied (message is shown to the user)."""


@dataclass(frozen=True)
class HistoryState:
    """Everything that defines the recorded history; undo and redo restore one."""

    base: EngineSnapshot
    plan: Plan
    end_tick: int
    tick: int  # where the user was
    #: On the undo stack: the edit made after this state (what undoing reverts); on the
    #: redo stack: the edit redoing re-applies.
    label: str = ""
    #: Ticks that edit moved tick 0 by ("Set tick 0 here"): markers move back on undo.
    shift: int = 0
    #: The editor's selection boxes before and after that edit (a move, turn or stack of
    #: the selection), so undo and redo take the selection along with the blocks.
    selection: tuple[tuple[Any, ...], tuple[Any, ...]] | None = None


@dataclass(frozen=True)
class EditBatch:
    """The edits of one row at one tick (one keyframe diamond)."""

    tick: int
    row: str
    indices: tuple[int, ...]
    labels: tuple[str, ...]
