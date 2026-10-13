"""The main window's sequence actions (ANIMATE mode): add, remove and show power pulses;
the timeline's line groups."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from PySide6.QtGui import (
    QColor,
)
from PySide6.QtWidgets import (
    QColorDialog,
    QInputDialog,
)

from redsim.core.pos import Pos

if TYPE_CHECKING:
    from redsim.ui.main_window import MainWindow


class SequenceActions:
    """Part of ``MainWindow`` (a mixin; its methods run on it)."""

    def _add_pulse(self, pos: Pos) -> None:
        """ANIMATE click: power the position from the current tick (tick 1 at the build)."""
        view = cast("MainWindow", self)
        tick = max(1, view.document.tick)
        strength, ticks = view.sequence.strength.value(), view.sequence.duration.value()
        view._edit(view.document.add_pulse, pos, tick, strength, ticks)
        view.viewport.flash(pos)
        where = " ".join(str(v) for v in pos)
        start = "" if view.document.tick else " (tick 0 is the build: from tick 1)"
        view._message(
            f"Pulse at {where}: strength {strength} for {ticks} ticks from tick {tick}{start}."
        )
        view.tabs.setCurrentWidget(view.sequence)

    def _remove_pulse(self, pos: Pos) -> None:
        """ANIMATE right click: remove the pulses at the position running at this tick."""
        view = cast("MainWindow", self)
        found = view.sequence.pulse_at(view.document.pulses(), pos, view.document.tick)
        if not found:
            view._message("No pulse there at this tick.", error=True)
            return
        view._edit(view.document.delete_edits, [p.index for p in found])

    def _move_line(self, pos: Pos, group: int, row: int) -> None:
        """A Powered line dragged to another place (or chosen group)."""
        view = cast("MainWindow", self)
        view.document.lines.move(pos, group, row)
        view._lines_changed()

    def _lines_changed(self) -> None:
        view = cast("MainWindow", self)
        view.document.dirty = True
        view.document.revision += 1
        view._changed()

    def _new_line_group(self, pos: Pos | None = None) -> None:
        view = cast("MainWindow", self)
        name, ok = QInputDialog.getText(view, "New group", "Name of the group:", text="Inputs")
        if ok and name.strip():
            view.document.lines.add_group(name.strip(), [pos] if pos is not None else [])
            view._lines_changed()

    def _group_request(self, action: str, index: int) -> None:
        """The timeline's group actions (fold, rename, color, order, new, delete)."""
        view = cast("MainWindow", self)
        lines = view.document.lines
        if not 0 <= index < len(lines.groups):
            return
        group = lines.groups[index]
        if action == "toggle":
            group.collapsed = not group.collapsed
        elif action == "rename":
            name, ok = QInputDialog.getText(view, "Rename group", "Name:", text=group.name)
            if not ok or not name.strip():
                return
            group.name = name.strip()
        elif action == "color":
            color = QColorDialog.getColor(QColor(group.color), view, "Group color")
            if not color.isValid():
                return
            group.color = color.name()
        elif action in ("up", "down"):
            lines.move_group(index, -1 if action == "up" else 1)
        elif action == "new":
            view._new_line_group()
            return
        elif action == "delete":
            lines.remove_group(index)
        view._lines_changed()

    def _show_pulse(self, pos: Pos, tick: int) -> None:
        """A pulse clicked in the Sequence tab: go to its tick and flash its position."""
        view = cast("MainWindow", self)
        view.simulation.stop()
        view._finish_tick()
        view.document.seek_tick(tick)
        view.viewport.flash(pos)
        view._changed()
