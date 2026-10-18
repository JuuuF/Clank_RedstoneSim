"""The main window's time actions: the run loop (paced by the wall clock, heavy ticks in
parts), stepping, seeking, tick 0, timeline edits and markers, undo and redo."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, cast

from PySide6.QtWidgets import (
    QInputDialog,
)

from redsim.ui.window_common import (
    HISTORY_MENU_SIZE,
    PLAY_INTERVAL_MS,
    RUN_BUDGET_SECONDS,
    STEP_BUDGET_SECONDS,
    history_label,
)

if TYPE_CHECKING:
    from redsim.ui.main_window import MainWindow


class TimeActions:
    """Part of ``MainWindow`` (a mixin; its methods run on it)."""

    def _play(self, on: bool) -> None:
        view = cast("MainWindow", self)
        if on:
            now = time.monotonic()
            view.pacer.rate = view.simulation.speed.value()
            view.pacer.start(now)
            view.tick_rate.reset(now)
            view.viewport.frame_rate.reset(now)
            view.play_timer.start(PLAY_INTERVAL_MS)
            view._glide(view.pacer.rate)
            if not view.simulation.backwards and not view.simulation.warp.isChecked():
                # Moving blocks are drawn between ticks (the game's partial tick).
                view.viewport.tick_fraction = lambda: view.pacer.fraction(time.monotonic())
            view.viewport.update()
        else:
            view.play_timer.stop()
            view.viewport.tick_fraction = None
            view._finish_tick()  # stopped mid-tick: finish it
            view.simulation.canvas.set_running(None)  # snap to the exact tick
            view._changed()

    def _glide(self, rate: float) -> None:
        """Let the timeline's playhead glide at ``rate`` ticks per second."""
        view = cast("MainWindow", self)
        sign = -1.0 if view.simulation.backwards else 1.0
        view.simulation.canvas.set_running(sign * rate)

    def _speed(self, tps: int) -> None:
        view = cast("MainWindow", self)
        view.pacer.set_rate(tps, time.monotonic())

    def _play_tick(self) -> None:
        """Run the ticks that are due by the wall clock (decoupled from drawing).

        Rendering happens at most once per frame afterwards, however many ticks ran, so the
        simulation keeps its rate even when drawing is slow.
        """
        view = cast("MainWindow", self)
        start = time.monotonic()
        warp = view.simulation.warp.isChecked()
        due = 1 << 30 if warp else view.pacer.due(start)
        # Heavy ticks run in parts (engine steps within a short budget) so frames keep
        # coming between them; the view only ever shows complete ticks.
        budget = RUN_BUDGET_SECONDS if warp else STEP_BUDGET_SECONDS
        deadline = time.perf_counter() + budget
        ran = 0
        while ran < due or not view.document.can_edit:
            if view.simulation.backwards:
                if not view.document.tick_back():
                    view.simulation.stop()  # back at tick 0
                    break
                view.last_steps = []
            else:
                steps, done = view.document.run_tick_until(deadline)
                view._tick_steps.extend(steps)
                if not done:
                    break  # mid-tick: continue on the next call, after a frame
                view.last_steps, view._tick_steps = view._tick_steps, []
            ran += 1
            if time.perf_counter() > deadline:
                break
        if not warp:
            view.pacer.ran(ran)
        if ran:  # nothing changed otherwise: no repaint
            now = time.monotonic()
            view.tick_rate.record(now, ran)
            measured = view.tick_rate.rate(now)
            view._glide(measured if measured > 0 else view.pacer.rate)
            view._changed(running=True)

    def _step_tick(self) -> None:
        view = cast("MainWindow", self)
        view.last_steps = view.document.run_tick()
        view._changed()

    def _step_event(self) -> None:
        view = cast("MainWindow", self)
        view.last_steps = [view.document.step()]
        view._changed()

    def _rewound(self, moved: bool) -> None:
        view = cast("MainWindow", self)
        view.simulation.stop()
        view.last_steps = []
        if not moved:
            view._message("Already at the start of the recorded history.")
        view._changed()

    def _jump(self, where: str) -> None:
        view = cast("MainWindow", self)
        view.simulation.stop()
        if not view.document.jump(where):
            none = {"previous_marker": "No marker before", "next_marker": "No marker after"}
            view._message(
                f"{none[where]} tick {view.document.tick}." if where in none else "Already there."
            )
        view.last_steps = []
        view._changed()

    def _tick_back(self) -> None:
        view = cast("MainWindow", self)
        view._rewound(view.document.tick_back())

    def _step_back(self) -> None:
        view = cast("MainWindow", self)
        view._rewound(view.document.step_back())

    def _seek(self, step_index: int) -> None:
        view = cast("MainWindow", self)
        view.simulation.stop()
        view.document.seek(step_index)
        view.last_steps = []
        view._changed()

    def _finish_tick(self) -> None:
        """Complete a tick the run loop left half-run (edits happen between ticks)."""
        view = cast("MainWindow", self)
        if not view.document.can_edit:
            view._tick_steps.extend(view.document.run_tick())
            view.last_steps, view._tick_steps = view._tick_steps, []

    def _set_tick_zero(self) -> None:
        view = cast("MainWindow", self)
        view._history_edit(view.document.set_tick_zero)

    def _history_edit(self, function: Any, *args: Any) -> None:
        """Keyframe operations re-run the history; the run stops first."""
        view = cast("MainWindow", self)
        view.simulation.stop()
        view.last_steps = []
        view._edit(function, *args)

    def _scrub(self, tick: int) -> None:
        view = cast("MainWindow", self)
        view.simulation.stop()
        if view.document.seek_tick(tick):
            view.last_steps = []
            view._changed()

    def _undo(self) -> None:
        view = cast("MainWindow", self)
        view.simulation.stop()
        if not view.document.undo():
            view._message("Nothing to undo.")
        view._changed()

    def _fill_history_menu(self) -> None:
        """Edit → Undo History: the latest steps, newest first; choosing one undoes it and
        everything after it (like Blender's undo history)."""
        view = cast("MainWindow", self)
        menu = view._history_menu
        menu.clear()
        labels = view.document.undo_labels
        if not labels:
            menu.addAction("Nothing to undo").setEnabled(False)
            return
        for count, label in enumerate(labels[:HISTORY_MENU_SIZE], start=1):
            action = menu.addAction(history_label(label))
            action.setToolTip(f"Undo {count} step{'s' if count > 1 else ''}")
            action.triggered.connect(lambda _=False, n=count: view._undo_to(n))
        if len(labels) > HISTORY_MENU_SIZE:
            menu.addAction(f"… {len(labels) - HISTORY_MENU_SIZE} older steps").setEnabled(False)

    def _add_marker(self) -> None:
        """A marker at the current tick (Ctrl+M, the timeline's Marker button)."""
        view = cast("MainWindow", self)
        view._add_marker_at(view.document.tick)

    def _add_marker_at(self, tick: int) -> None:
        """Name ``tick``: a new marker, or renaming the one already there."""
        view = cast("MainWindow", self)
        if tick in view.document.markers:
            view._rename_marker(tick)
            return
        name, ok = QInputDialog.getText(
            view, "Add marker", f"Name of the marker at tick {tick}:", text=f"tick {tick}"
        )
        if ok:
            view._name_marker(tick, name.strip() or f"tick {tick}")
            view.simulation.canvas.selected_marker = tick

    def _rename_marker(self, tick: int) -> None:
        view = cast("MainWindow", self)
        current = view.document.markers.get(tick, "")
        name, ok = QInputDialog.getText(view, "Rename marker", f"Tick {tick}:", text=current)
        if ok and name.strip():  # an empty name keeps the old one (Del deletes)
            view._name_marker(tick, name.strip())

    def _name_marker(self, tick: int, name: str) -> None:
        """Set, rename (or with an empty name delete) the marker at ``tick``."""
        view = cast("MainWindow", self)
        old = view.document.markers.get(tick)
        view.document.set_marker(tick, name)
        if not name and old is not None:
            view._message(f"Deleted the marker “{old}” (Ctrl+Z brings it back).")
        view._changed()

    def _move_marker(self, tick: int, to: int) -> None:
        view = cast("MainWindow", self)
        if not view.document.move_marker(tick, to):
            view._message(f"Tick {to} already has a marker.")
        view._changed()

    def _undo_to(self, count: int) -> None:
        view = cast("MainWindow", self)
        view.simulation.stop()
        if view.document.undo_to(count):
            view._message(f"Undid {count} step{'s' if count > 1 else ''}.")
        view._changed()

    def _redo(self) -> None:
        view = cast("MainWindow", self)
        if not view.document.redo():
            view._message("Nothing to redo.")
        view._changed()
