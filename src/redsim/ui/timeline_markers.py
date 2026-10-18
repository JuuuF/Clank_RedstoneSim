"""The timeline's markers (Blender's): named ticks in a strip under the ruler's numbers.
Click a marker to select it and jump there, drag it to another tick, double-click it (or
F2) to rename it, Del to delete it; its right-click menu does these too, and a right
click elsewhere on the timeline adds one at that tick. Every change is an undo step. The
transport bar's marker buttons (``TimelineBar``) add one at the current tick, jump to the
previous or next one and list them all."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, cast

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QMenu, QToolTip

from redsim.ui import pixel_icons, theme

if TYPE_CHECKING:
    from redsim.ui.timeline import TimelineCanvas

#: How close (pixels) to a marker's flag a click picks it, besides its name.
FLAG_REACH = 6
#: How far (pixels) the mouse moves before a pressed marker is dragged.
DRAG_START = 4


class MarkerArea:
    """Part of ``TimelineCanvas`` (a mixin; its methods run on it)."""

    def set_markers(self, markers: dict[int, str]) -> None:
        """Markers get their own strip under the tick numbers while there are any."""
        view = cast("TimelineCanvas", self)
        view.markers = markers
        view.RULER_HEIGHT = type(view).RULER_HEIGHT + (view.MARKER_STRIP if markers else 0)
        if view.selected_marker not in markers:
            view.selected_marker = None

    def marker_at(self, x: float, y: float) -> int | None:
        """The marker whose flag or name (in the marker strip) is under the cursor: the
        nearest flag, else the name drawn on top."""
        view = cast("TimelineCanvas", self)
        top = type(view).RULER_HEIGHT - 2
        if not view.markers or x < view.LABEL_WIDTH or not top <= y <= view.RULER_HEIGHT:
            return None
        flags = [(abs(view._x(tick) - x), tick) for tick in view.markers]
        distance, tick = min(flags)
        if distance <= FLAG_REACH:
            return tick
        metrics = view.fontMetrics()
        named = [
            tick
            for tick, name in view.markers.items()
            if view._x(tick) < x <= view._x(tick) + 8 + metrics.horizontalAdvance(name)
        ]
        return max(named, default=None)

    def _paint_markers(self, painter: QPainter) -> None:
        """Markers: a gold flag at the bottom of the ruler with the name beside it, and a
        faint dotted line down through the rows; the selected one white, a dragged one
        where it would go (and faintly where it was)."""
        view = cast("TimelineCanvas", self)
        base = view.RULER_HEIGHT - 3  # the marker strip, below the tick numbers
        for tick, name in view.markers.items():
            selected = tick == view.selected_marker
            color = QColor("#ffffff" if selected else theme.GOLD)
            if tick == view._marker_drag_tick() and view._marker_to is not None:
                ghost = QColor(color)
                ghost.setAlpha(70)
                view._paint_marker(painter, view._x(tick), base, ghost, "")
                tick = view._marker_to
            x = view._x(tick)
            if x < view.LABEL_WIDTH - FLAG_REACH or x > view.width():
                continue
            line = QColor(color)
            line.setAlpha(140 if selected else 70)
            painter.setPen(QPen(line, 1, Qt.PenStyle.DotLine))
            painter.drawLine(QPointF(x, view.RULER_HEIGHT), QPointF(x, view.height()))
            view._paint_marker(painter, x, base, color, name)

    def _paint_marker(
        self, painter: QPainter, x: float, base: float, color: QColor, name: str
    ) -> None:
        """One marker's flag (a pin pointing down at its tick) and name."""
        pin = QPolygonF(
            [
                QPointF(x - 4, base - 8),
                QPointF(x + 4, base - 8),
                QPointF(x + 4, base - 4),
                QPointF(x, base),
                QPointF(x - 4, base - 4),
            ]
        )
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawPolygon(pin)
        if name:
            painter.setPen(color)
            painter.drawText(QPointF(x + 7, base), name)

    def _select_and_jump(self, tick: int) -> None:
        view = cast("TimelineCanvas", self)
        view.selected_marker = tick
        view.update()
        view.scrub.emit(max(view.start, min(view.end, tick)))

    def _marker_drag_tick(self) -> int | None:
        view = cast("TimelineCanvas", self)
        return view._marker_drag[0] if view._marker_drag is not None else None

    # ------------------------------------------------------------------ input

    def _marker_press(self, event: QMouseEvent) -> bool:
        """A press on a marker selects it (and nothing else): left starts a drag (or a
        click: jump there), right opens its menu. True if it was on a marker."""
        view = cast("TimelineCanvas", self)
        x, y = event.position().x(), event.position().y()
        tick = view.marker_at(x, y)
        if tick is None:
            if view.selected_marker is not None and event.button() == Qt.MouseButton.LeftButton:
                view.selected_marker = None
                view.update()
            return False
        view.selected_marker = tick
        view.selected, view.selected_events, view.selected_pulses = set(), set(), set()
        view.setFocus()
        view.update()
        if event.button() == Qt.MouseButton.RightButton:
            view._marker_menu(event.globalPosition().toPoint(), tick)
        elif event.button() == Qt.MouseButton.LeftButton:
            view._marker_drag, view._marker_to = (tick, x), None
        return True

    def _marker_move(self, event: QMouseEvent) -> bool:
        """Dragging a marker: where it would go, shown as it moves. True while dragging."""
        view = cast("TimelineCanvas", self)
        if view._marker_drag is None:
            return False
        tick, start_x = view._marker_drag
        x = event.position().x()
        if view._marker_to is None and abs(x - start_x) <= DRAG_START:
            return True
        to = max(0, tick + view.tick_at(x) - view.tick_at(start_x))
        view._marker_to = to
        view.setCursor(Qt.CursorShape.ClosedHandCursor)
        taken = view.markers.get(to) if to != tick else None
        text = (
            f"Tick {to} already has “{taken}”"
            if taken is not None
            else f"“{view.markers[tick]}” → tick {to} ({to - tick:+d})"
        )
        QToolTip.showText(event.globalPosition().toPoint(), text)
        view.update()
        return True

    def _marker_hover(self, event: QMouseEvent) -> bool:
        """The hand cursor and a hint over a marker. True if the cursor is on one."""
        view = cast("TimelineCanvas", self)
        x, y = event.position().x(), event.position().y()
        tick = view.marker_at(x, y)
        if tick is None:
            if y <= view.RULER_HEIGHT:
                view.unsetCursor()
            return False
        view.setCursor(Qt.CursorShape.OpenHandCursor)
        QToolTip.showText(
            event.globalPosition().toPoint(),
            f"Marker “{view.markers[tick]}” at tick {tick}\n"
            "Click: select and jump there · drag: move\n"
            "Double-click or F2: rename · Del: delete · right click: menu",
        )
        return True

    def _marker_release(self) -> bool:
        """The end of a press on a marker: move it where it was dragged, or after a plain
        click jump to it. True if a marker was pressed."""
        view = cast("TimelineCanvas", self)
        if view._marker_drag is None:
            return False
        tick, to = view._marker_drag[0], view._marker_to
        view._marker_drag, view._marker_to = None, None
        view.unsetCursor()
        if to is None:
            view._select_and_jump(tick)
        elif to != tick and to not in view.markers:
            view.selected_marker = to
            view.move_marker.emit(tick, to)
        view.update()
        return True

    def _marker_key(self, key: int) -> bool:
        """Del deletes the selected marker, F2 renames it. True if the key was used."""
        view = cast("TimelineCanvas", self)
        tick = view.selected_marker
        if tick is None or tick not in view.markers:
            return False
        if key in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            view.selected_marker = None
            view.delete_marker.emit(tick)
        elif key == Qt.Key.Key_F2:
            view.rename_marker.emit(tick)
        else:
            return False
        return True

    def _marker_menu(self, where: QPoint, tick: int) -> None:
        view = cast("TimelineCanvas", self)
        menu = QMenu(view)
        name = view.markers[tick]
        jump = menu.addAction(f"Jump to “{name}” (tick {tick})")
        jump.setIcon(pixel_icons.pixel_icon("marker"))
        jump.setEnabled(view.start <= tick <= view.end)
        jump.triggered.connect(lambda: view._select_and_jump(tick))
        menu.addAction("Rename… (F2, double-click)").triggered.connect(
            lambda: view.rename_marker.emit(tick)
        )
        here = view.current
        move = menu.addAction(f"Move to the current tick ({here})")
        move.setEnabled(here != tick and here not in view.markers)
        move.triggered.connect(lambda: view.move_marker.emit(tick, here))
        menu.addSeparator()
        remove = menu.addAction("Delete marker (Del)")
        remove.setIcon(pixel_icons.pixel_icon("delete"))
        remove.triggered.connect(lambda: view.delete_marker.emit(tick))
        menu.exec(where)


def fill_marker_menu(menu: QMenu, view: TimelineCanvas, add: Callable[[], None]) -> None:
    """The transport bar's marker menu: add at the current tick (``add``), rename or
    delete the selected marker (else the one at the current tick), and every marker to
    jump to."""
    menu.clear()
    menu.setToolTipsVisible(True)
    here = view.current
    at_here = view.markers.get(here)
    adding = menu.addAction(f"Add marker at tick {here}… (Ctrl+M)")
    adding.setIcon(pixel_icons.pixel_icon("marker"))
    adding.setEnabled(at_here is None)
    adding.triggered.connect(add)
    target = view.selected_marker if view.selected_marker in view.markers else None
    if target is None and at_here is not None:
        target = here
    name = f" “{view.markers[target]}”" if target is not None else ""
    rename = menu.addAction(f"Rename marker{name}…")
    remove = menu.addAction(f"Delete marker{name}")
    remove.setIcon(pixel_icons.pixel_icon("delete"))
    for action in (rename, remove):
        action.setEnabled(target is not None)
        action.setToolTip("The selected marker, else the one at the current tick")
    if target is not None:
        rename.triggered.connect(lambda: view.rename_marker.emit(target))
        remove.triggered.connect(lambda: view.delete_marker.emit(target))
    menu.addSeparator()
    if not view.markers:
        menu.addAction("No markers yet").setEnabled(False)
    for tick, marker in view.markers.items():
        jump = menu.addAction(f"{tick}  ·  {marker}")
        jump.setCheckable(True)
        jump.setChecked(tick == here)
        jump.setEnabled(view.start <= tick <= view.end)
        jump.setToolTip("Jump here")
        jump.triggered.connect(lambda _=False, t=tick: view._select_and_jump(t))
