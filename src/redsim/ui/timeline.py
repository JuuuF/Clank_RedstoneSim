"""Blender-like timeline at the bottom of the window: transport controls, a tick ruler with
the recorded range, edit markers and the playhead, and monitor tracks.

Ticks count from the build (tick 0). Recorded edits are keyframe diamonds in four
color-coded rows (placed, removed, changed, used blocks), one per tick and row: click or
drag a band to select, drag to move them in time, M merges, Del deletes, the right-click
menu also moves them into the build or makes the current tick the new tick 0. Monitor
tracks work like a logic analyzer: each monitored block (Inspector → Monitor) gets a row
showing its value (0-15) per tick (``redsim.editor.monitor``). Click or drag on the ruler
or tracks to scrub, wheel to zoom, middle-drag to pan; right-click a track's label to
remove it.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from PySide6.QtCore import QEvent, QPoint, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPen,
    QPolygonF,
    QWheelEvent,
)
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QMenu,
    QSizePolicy,
    QSpinBox,
    QToolButton,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

from redsim.core.pos import Pos
from redsim.editor.document import EDIT_ROWS, Document, EditBatch
from redsim.ui import pixel_icons, theme
from redsim.ui.names import block_name

BACKGROUND = QColor(theme.PANEL)
RECORDED = QColor(theme.WIDGET)
GRID = QColor(theme.LINE)
TEXT = QColor(theme.TEXT)
TEXT_DIM = QColor(theme.TEXT_DIM)
RULER = QColor(theme.SUNKEN)
ROW_COLORS = {
    "build": QColor(110, 200, 95),
    "remove": QColor(235, 85, 70),
    "edit": QColor(95, 150, 255),
    "interact": QColor(240, 196, 60),
}
ROW_TITLES = {"build": "Placed", "remove": "Removed", "edit": "Changed", "interact": "Used"}
PLAYHEAD = QColor(theme.ACCENT)
SIGNAL = QColor(theme.ACCENT)


@dataclass
class Track:
    pos: Pos
    label: str
    samples: dict[int, int]


class TimelineCanvas(QWidget):
    scrub = Signal(int)  # tick (since tick 0)
    remove_monitor = Signal(object)  # Pos
    move_edits = Signal(object, int)  # step indices, delta ticks
    merge_edits = Signal(object, object)  # step indices, target tick (None: earliest)
    delete_edits = Signal(object)  # step indices
    set_tick_zero = Signal()

    LABEL_WIDTH = 150
    RULER_HEIGHT = 26
    EDIT_ROW_HEIGHT = 15
    ROW_HEIGHT = 18

    def __init__(self) -> None:
        super().__init__()
        self.view_start = 0.0
        self.view_span = 120.0
        self.start = 0
        self.end = 0
        self.current = 0
        self.batches: list[EditBatch] = []
        self.selected: set[tuple[int, str]] = set()  # (tick, row)
        self.tracks: list[Track] = []
        self._scrubbing = False
        self._pan_from: tuple[int, float] | None = None
        self._last_scrub: int | None = None
        self._drag_from: tuple[float, float] | None = None  # press point in the edit rows
        self._dragging_edits = False
        self._drag_delta = 0
        self._band: QRectF | None = None
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self._resize_to_tracks()

    # ------------------------------------------------------------------ data
    def set_data(
        self,
        start: int,
        end: int,
        current: int,
        batches: list[EditBatch],
        tracks: list[Track],
    ) -> None:
        self.start, self.end, self.current = start, end, current
        self.batches, self.tracks = batches, tracks
        present = {(b.tick, b.row) for b in batches}
        self.selected &= present
        self._resize_to_tracks()
        # Keep the playhead in view (Blender's "follow current frame").
        if not self.view_start <= current <= self.view_start + self.view_span * 0.95:
            self.view_start = max(min(start, current) - 2, current - self.view_span * 0.8)
        self.update()

    def _resize_to_tracks(self) -> None:
        self.setFixedHeight(self._tracks_top() + 4 + self.ROW_HEIGHT * max(1, len(self.tracks)))

    def selected_indices(self) -> list[int]:
        return sorted(
            i for b in self.batches if (b.tick, b.row) in self.selected for i in b.indices
        )

    # ------------------------------------------------------------------ geometry
    def _x(self, tick: float) -> float:
        width = max(1, self.width() - self.LABEL_WIDTH)
        return self.LABEL_WIDTH + (tick - self.view_start) / self.view_span * width

    def tick_at(self, x: float) -> int:
        width = max(1, self.width() - self.LABEL_WIDTH)
        return round(self.view_start + (x - self.LABEL_WIDTH) / width * self.view_span)

    def _row_top(self, row: int) -> int:
        return self.RULER_HEIGHT + row * self.EDIT_ROW_HEIGHT

    def _tracks_top(self) -> int:
        return self._row_top(len(EDIT_ROWS)) + 2

    def _edit_row_at(self, y: float) -> int | None:
        row = int((y - self.RULER_HEIGHT) // self.EDIT_ROW_HEIGHT)
        return row if 0 <= row < len(EDIT_ROWS) and y >= self.RULER_HEIGHT else None

    def _batch_at(self, x: float, y: float) -> EditBatch | None:
        row = self._edit_row_at(y)
        if row is None:
            return None
        best, best_dx = None, 7.0
        for batch in self.batches:
            if batch.row != EDIT_ROWS[row]:
                continue
            dx = abs(self._x(batch.tick) - x)
            if dx <= best_dx:
                best, best_dx = batch, dx
        return best

    def _ruler_step(self) -> int:
        width = max(1, self.width() - self.LABEL_WIDTH)
        for step in (1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000):
            if step / self.view_span * width >= 46:
                return step
        return 20000

    # ------------------------------------------------------------------ painting
    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), BACKGROUND)
        height = self.height()
        x0, x1 = self._x(self.start), self._x(self.end)
        painter.fillRect(QRectF(x0, 0, max(1.0, x1 - x0), height), RECORDED)
        painter.fillRect(QRectF(0, 0, self.width(), self.RULER_HEIGHT - 2), RULER)
        step = self._ruler_step()
        tick = math.floor(self.view_start / step) * step
        while tick <= self.view_start + self.view_span:
            x = self._x(tick)
            if x >= self.LABEL_WIDTH:
                painter.setPen(GRID)
                painter.drawLine(int(x), self.RULER_HEIGHT - 6, int(x), height)
                painter.setPen(TEXT_DIM)
                label = str(tick)
                half = painter.fontMetrics().horizontalAdvance(label) / 2
                painter.drawText(QPointF(max(x - half, self.LABEL_WIDTH + 2.0), 14), label)
            tick += step
        self._paint_edit_rows(painter)
        self._paint_tracks(painter)
        painter.fillRect(QRectF(0, 0, self.LABEL_WIDTH, height), BACKGROUND)
        painter.fillRect(QRectF(0, 0, self.LABEL_WIDTH, self.RULER_HEIGHT - 2), RULER)
        painter.setPen(TEXT)
        # The current tick, like Blender's current frame field: "TICK 34 / 120".
        x = 8 + theme.draw_text(painter, 8, 6, "TICK", theme.TEXT_DIM, 1, False) + 5
        x += theme.draw_text(painter, x, 3, str(self.current), theme.GOLD, 2)
        if self.end > self.current:
            theme.draw_text(painter, x + 4, 6, f"/ {self.end}", theme.TEXT_DIM, 1, False)
        elif self.current == 0:
            theme.draw_text(painter, x + 4, 6, "BUILD", theme.TEXT_DIM, 1, False)
        for row, name in enumerate(EDIT_ROWS):
            top = self._row_top(row)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(ROW_COLORS[name])
            painter.drawEllipse(QRectF(10, top + 4, 7, 7))
            painter.setPen(TEXT)
            painter.drawText(22, top + self.EDIT_ROW_HEIGHT - 3, ROW_TITLES[name])
        for row, track in enumerate(self.tracks):
            y = self._tracks_top() + row * self.ROW_HEIGHT
            painter.drawText(8, y + self.ROW_HEIGHT - 5, track.label)
        x = self._x(self.current)
        if x >= self.LABEL_WIDTH:
            painter.setPen(PLAYHEAD)
            painter.drawLine(int(x), 0, int(x), height)
            label = str(self.current)
            width = max(20, painter.fontMetrics().horizontalAdvance(label) + 10)
            left = max(x - width / 2, float(self.LABEL_WIDTH))  # tick 0 sits at the edge
            badge = QRectF(left, 1, width, 17)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(PLAYHEAD)
            painter.drawRoundedRect(badge, 4, 4)
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(badge, Qt.AlignmentFlag.AlignCenter, label)
        painter.end()

    def _paint_edit_rows(self, painter: QPainter) -> None:
        painter.setPen(GRID)
        for row in range(len(EDIT_ROWS) + 1):
            line = self._row_top(row)
            painter.drawLine(self.LABEL_WIDTH, line, self.width(), line)
        shift = self._drag_delta if self._dragging_edits else 0
        for batch in self.batches:
            key = (batch.tick, batch.row)
            selected = key in self.selected
            tick = batch.tick + (shift if selected else 0)
            x = self._x(max(0, tick))
            if x < self.LABEL_WIDTH:
                continue
            y = self._row_top(EDIT_ROWS.index(batch.row)) + self.EDIT_ROW_HEIGHT / 2
            size = 5 if len(batch.indices) == 1 else 6.5
            diamond = QPolygonF(
                [
                    QPointF(x, y - size),
                    QPointF(x + size, y),
                    QPointF(x, y + size),
                    QPointF(x - size, y),
                ]
            )
            painter.setBrush(ROW_COLORS[batch.row])
            painter.setPen(QPen(QColor(255, 255, 255), 1.6) if selected else QPen(BACKGROUND, 1))
            painter.drawPolygon(diamond)
            if len(batch.indices) > 1 and self.view_span < 400:
                painter.setPen(TEXT)
                painter.drawText(QPointF(x + size + 2, y + 4), str(len(batch.indices)))
        if self._band is not None:
            painter.setPen(QPen(PLAYHEAD, 1, Qt.PenStyle.DashLine))
            painter.setBrush(QColor(80, 150, 255, 40))
            painter.drawRect(self._band)

    def _paint_tracks(self, painter: QPainter) -> None:
        first = max(math.floor(self.view_start), self.start)
        last = min(math.ceil(self.view_start + self.view_span), self.end)
        for row, track in enumerate(self.tracks):
            top = self._tracks_top() + row * self.ROW_HEIGHT
            bottom = top + self.ROW_HEIGHT - 3
            painter.setPen(GRID)
            painter.drawLine(self.LABEL_WIDTH, bottom + 1, self.width(), bottom + 1)
            # One step waveform per track (a logic analyzer's trace): a filled outline,
            # so neighboring ticks join without seams, and a bright top edge.
            height = bottom - top
            trace: list[QPointF] = []
            for tick in range(first, last + 1):
                value = track.samples.get(tick) or 0
                y = bottom - (height * max(value / 15, 0.12) if value else 0.0)
                trace += [QPointF(self._x(tick), y), QPointF(self._x(tick + 1), y)]
            if not trace:
                continue
            ends = [QPointF(self._x(first), bottom), QPointF(self._x(last + 1), bottom)]
            outline = QPolygonF([ends[0], *trace, ends[1]])
            fill = QColor(SIGNAL)
            fill.setAlphaF(0.45)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(fill)
            painter.drawPolygon(outline)
            painter.setPen(QPen(QColor(SIGNAL).lighter(140), 1.5))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPolyline(QPolygonF(trace))

    # ------------------------------------------------------------------ input
    def mousePressEvent(self, event: QMouseEvent) -> None:
        x, y = event.position().x(), event.position().y()
        button = event.button()
        if button == Qt.MouseButton.MiddleButton:
            self._pan_from = (int(x), self.view_start)
            return
        if button == Qt.MouseButton.RightButton:
            if x < self.LABEL_WIDTH and y >= self._tracks_top():
                row = int((y - self._tracks_top()) // self.ROW_HEIGHT)
                if 0 <= row < len(self.tracks):
                    self.remove_monitor.emit(self.tracks[row].pos)
                return
            batch = self._batch_at(x, y)
            if batch is not None and (batch.tick, batch.row) not in self.selected:
                self.selected = {(batch.tick, batch.row)}
                self.update()
            self._context_menu(event.globalPosition().toPoint(), self._edit_row_at(y))
            return
        if button != Qt.MouseButton.LeftButton or x < self.LABEL_WIDTH:
            return
        if self._edit_row_at(y) is not None:
            batch = self._batch_at(x, y)
            additive = bool(
                event.modifiers()
                & (Qt.KeyboardModifier.ShiftModifier | Qt.KeyboardModifier.ControlModifier)
            )
            if batch is not None:
                key = (batch.tick, batch.row)
                if additive:
                    self.selected ^= {key}
                elif key not in self.selected:
                    self.selected = {key}
                self._drag_from = (x, y)
                self._dragging_edits = False
                self._drag_delta = 0
            else:
                if not additive:
                    self.selected = set()
                self._band = QRectF(x, y, 0, 0)
                self._drag_from = (x, y)
            self.update()
            return
        self._scrubbing = True
        self._scrub_to(x)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        x, y = event.position().x(), event.position().y()
        if self._scrubbing:
            self._scrub_to(x)
        elif self._pan_from is not None:
            start_x, start_view = self._pan_from
            width = max(1, self.width() - self.LABEL_WIDTH)
            self.view_start = start_view - (x - start_x) / width * self.view_span
            self.update()
        elif self._band is not None and self._drag_from is not None:
            fx, fy = self._drag_from
            self._band = QRectF(QPointF(min(fx, x), min(fy, y)), QPointF(max(fx, x), max(fy, y)))
            self.update()
        elif self._drag_from is not None and self.selected:
            delta = self.tick_at(x) - self.tick_at(self._drag_from[0])
            if abs(x - self._drag_from[0]) > 4 or self._dragging_edits:
                self._dragging_edits = True
                earliest = min(tick for tick, _ in self.selected)
                self._drag_delta = max(delta, -earliest)
                self.update()
        else:
            batch = self._batch_at(x, y)
            if batch is not None:
                lines = list(batch.labels[:12])
                if len(batch.labels) > 12:
                    lines.append(f"… {len(batch.labels) - 12} more")
                title = f"{ROW_TITLES[batch.row]} at tick {batch.tick}: {len(batch.labels)} edits"
                QToolTip.showText(event.globalPosition().toPoint(), "\n".join([title, *lines]))
            else:
                QToolTip.hideText()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._band is not None:
            band = self._band
            if band.width() < 3 and band.height() < 3:
                self._scrub_to(band.x())
            else:
                for batch in self.batches:
                    point = QPointF(
                        self._x(batch.tick),
                        self._row_top(EDIT_ROWS.index(batch.row)) + self.EDIT_ROW_HEIGHT / 2,
                    )
                    if band.contains(point):
                        self.selected.add((batch.tick, batch.row))
            self._band = None
        elif self._dragging_edits and self._drag_delta:
            self.move_edits.emit(self.selected_indices(), self._drag_delta)
            self.selected = {(tick + self._drag_delta, row) for tick, row in self.selected}
        self._dragging_edits = False
        self._drag_delta = 0
        self._drag_from = None
        self._scrubbing = False
        self._pan_from = None
        self._last_scrub = None
        self.update()

    def event(self, event: QEvent) -> bool:
        # Delete and M act on selected keyframes when the timeline has focus (before the
        # window's shortcuts see them).
        if event.type() == QEvent.Type.ShortcutOverride and self.selected:
            key = event.key()  # type: ignore[attr-defined]
            if key in (Qt.Key.Key_Delete, Qt.Key.Key_M, Qt.Key.Key_Backspace):
                event.accept()
                return True
        return super().event(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if self.selected and event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.delete_edits.emit(self.selected_indices())
            self.selected = set()
        elif self.selected and event.key() == Qt.Key.Key_M:
            self.merge_edits.emit(self.selected_indices(), None)
        else:
            super().keyPressEvent(event)

    def _context_menu(self, where: QPoint, row: int | None) -> None:
        menu = QMenu(self)
        chosen = self.selected_indices()
        ticks = {tick for tick, _ in self.selected}
        merge = menu.addAction("Merge selected into the earliest tick (M)")
        merge.setEnabled(len(ticks) > 1)
        merge.triggered.connect(lambda: self.merge_edits.emit(chosen, None))
        if row is not None:
            name = EDIT_ROWS[row]
            everything = [i for b in self.batches if b.row == name for i in b.indices]
            merge_row = menu.addAction(f"Merge all {ROW_TITLES[name].lower()} edits")
            merge_row.setEnabled(len({b.tick for b in self.batches if b.row == name}) > 1)
            merge_row.triggered.connect(lambda: self.merge_edits.emit(everything, None))
        bake = menu.addAction("Move selected into the build (tick 0)")
        bake.setEnabled(bool(chosen))
        bake.triggered.connect(lambda: self.merge_edits.emit(chosen, 0))
        delete = menu.addAction("Delete selected (Del)")
        delete.setEnabled(bool(chosen))
        delete.triggered.connect(lambda: self.delete_edits.emit(chosen))
        menu.addSeparator()
        zero = menu.addAction("Set tick 0 here (the current state becomes the build)")
        zero.triggered.connect(self.set_tick_zero.emit)
        menu.exec(where)

    def wheelEvent(self, event: QWheelEvent) -> None:
        steps = event.angleDelta().y() / 120.0
        if not steps:
            return
        anchor = self.tick_at(event.position().x())
        span = min(200000.0, max(10.0, self.view_span * 1.25**-steps))
        ratio = (anchor - self.view_start) / self.view_span
        self.view_start = anchor - ratio * span
        self.view_span = span
        self.update()

    def _scrub_to(self, x: float) -> None:
        tick = max(self.start, min(self.end, self.tick_at(x)))
        if tick != self._last_scrub:
            self._last_scrub = tick
            self.scrub.emit(tick)


class TimelineBar(QWidget):
    """Transport controls, speed and status above the timeline canvas."""

    play_toggled = Signal(bool)
    step_tick = Signal()
    step_event = Signal()
    tick_back = Signal()
    step_back = Signal()
    jump = Signal(str)  # "start" | "end" | "previous" | "next"
    set_tick_zero = Signal()
    speed_changed = Signal(int)

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        row = QHBoxLayout()
        row.setContentsMargins(6, 2, 6, 2)
        layout.addLayout(row)

        def button(text: str, tip: str, slot: object) -> QToolButton:
            widget = QToolButton()
            if text in pixel_icons.ICONS:
                widget.setIcon(pixel_icons.pixel_icon(text))
                widget.setIconSize(pixel_icons.ICON_SIZE)
            else:
                widget.setText(text)
            widget.setToolTip(tip)
            widget.clicked.connect(slot)
            row.addWidget(widget)
            return widget

        button("start", "Jump to start (Shift+Left)", lambda: self.jump.emit("start"))
        button("previous", "Previous edit (Down)", lambda: self.jump.emit("previous"))
        button("back", "Tick back (Left); Ctrl+Left: one engine step", self.tick_back.emit)
        self.reverse = QToolButton()
        self.reverse.setIconSize(pixel_icons.ICON_SIZE)
        self.reverse.setIcon(pixel_icons.pixel_icon("reverse"))
        self.reverse.setCheckable(True)
        self.reverse.setToolTip("Play backwards / pause (Ctrl+Shift+Space)")
        self.reverse.toggled.connect(self._reverse_toggled)
        row.addWidget(self.reverse)
        self.play = QToolButton()
        self.play.setIconSize(pixel_icons.ICON_SIZE)
        self.play.setIcon(pixel_icons.pixel_icon("play"))
        self.play.setCheckable(True)
        self.play.setToolTip("Run / pause (Space)")
        self.play.toggled.connect(self._toggled)
        row.addWidget(self.play)
        button(
            "step", "Step one tick (Right); Ctrl+Right or E: one engine step", self.step_tick.emit
        )
        button("next", "Next edit (Up)", lambda: self.jump.emit("next"))
        button("end", "Jump to end (Shift+Right)", lambda: self.jump.emit("end"))
        row.addSpacing(8)
        zero = button(
            "Set tick 0 here",
            "Make the current state the build (tick 0), e.g. after a few ticks let a new "
            "block update its circuit. Later edits move along. (Ctrl+0)",
            self.set_tick_zero.emit,
        )
        zero.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        row.addSpacing(12)
        row.addWidget(QLabel("ticks/s"))
        self.speed = QSpinBox()
        self.speed.setRange(1, 1000)
        self.speed.setValue(20)
        self.speed.valueChanged.connect(self.speed_changed.emit)
        row.addWidget(self.speed)
        self.warp = QCheckBox("Warp")
        self.warp.setToolTip("Run as many ticks as possible (normal event order is kept)")
        row.addWidget(self.warp)
        row.addSpacing(12)
        self.status = QLabel("")
        self.status.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        row.addWidget(self.status, 1)
        self.canvas = TimelineCanvas()
        layout.addWidget(self.canvas)

    def _toggled(self, on: bool) -> None:
        self.play.setIcon(pixel_icons.pixel_icon("pause" if on else "play"))
        if on and self.reverse.isChecked():
            self.reverse.blockSignals(True)
            self.reverse.setChecked(False)
            self.reverse.setIcon(pixel_icons.pixel_icon("reverse"))
            self.reverse.blockSignals(False)
        self.play_toggled.emit(on)

    def _reverse_toggled(self, on: bool) -> None:
        """Backwards playback uses the same run loop, ticking back instead of forward."""
        self.reverse.setIcon(pixel_icons.pixel_icon("pause" if on else "reverse"))
        if on and self.play.isChecked():
            self.play.blockSignals(True)
            self.play.setChecked(False)
            self.play.setIcon(pixel_icons.pixel_icon("play"))
            self.play.blockSignals(False)
        self.play_toggled.emit(on)

    @property
    def backwards(self) -> bool:
        return self.reverse.isChecked()

    def stop(self) -> None:
        for button in (self.play, self.reverse):
            button.setChecked(False)

    def show_status(self, document: Document) -> None:
        engine = document.engine
        tick, end = document.tick, document.end_tick
        self.status.setText(f"<span style='color:{theme.TEXT_DIM}'>{engine.phase.value}</span>")
        self.status.setToolTip(
            ("Tick 0 is the build: edits change it.\n" if tick == 0 else "")
            + (f"Recorded up to tick {end}.\n" if end > tick else "")
            + f"Phase: {engine.phase.value}\nNext: {engine.peek_next_step()}"
        )
        tracks = [
            Track(
                pos,
                f"{block_name(document.state_at(pos).block.id)} {pos}",
                document.samples.get(pos, {}),
            )
            for pos in document.monitors
        ]
        self.canvas.set_data(0, end, tick, document.edit_batches(), tracks)
