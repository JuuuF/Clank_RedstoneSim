"""Blender-like timeline at the bottom of the window: transport controls, a tick ruler with
the recorded range, edit markers and the playhead, and monitor tracks.

Monitor tracks work like a logic analyzer: each monitored block (Inspector → Monitor) gets a
row showing its value (0-15) per tick (``redsim.editor.monitor``). Click or drag on the
ruler or tracks to scrub, wheel to zoom, middle-drag to pan; right-click a track's label
to remove it.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from PySide6.QtCore import QPoint, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPaintEvent, QPolygonF, QWheelEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QSpinBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from redsim.core.pos import Pos
from redsim.editor.document import Document

BACKGROUND = QColor(40, 43, 48)
RECORDED = QColor(58, 62, 69)
GRID = QColor(78, 83, 92)
TEXT = QColor(205, 208, 214)
EDIT = QColor(240, 196, 60)
PLAYHEAD = QColor(80, 150, 255)
SIGNAL = QColor(235, 60, 50)


@dataclass
class Track:
    pos: Pos
    label: str
    samples: dict[int, int]


class TimelineCanvas(QWidget):
    scrub = Signal(int)  # game tick
    remove_monitor = Signal(object)  # Pos

    LABEL_WIDTH = 150
    RULER_HEIGHT = 26
    ROW_HEIGHT = 18

    def __init__(self) -> None:
        super().__init__()
        self.view_start = 0.0
        self.view_span = 120.0
        self.start = 0
        self.end = 0
        self.current = 0
        self.edits: list[int] = []
        self.tracks: list[Track] = []
        self._scrubbing = False
        self._pan_from: tuple[int, float] | None = None
        self._last_scrub: int | None = None
        self.setMouseTracking(True)
        self._resize_to_tracks()

    # ------------------------------------------------------------------ data
    def set_data(
        self, start: int, end: int, current: int, edits: list[int], tracks: list[Track]
    ) -> None:
        self.start, self.end, self.current = start, end, current
        self.edits, self.tracks = edits, tracks
        self._resize_to_tracks()
        # Keep the playhead in view (Blender's "follow current frame").
        if not self.view_start <= current <= self.view_start + self.view_span * 0.95:
            self.view_start = max(min(start, current), current - self.view_span * 0.8)
        self.update()

    def _resize_to_tracks(self) -> None:
        self.setFixedHeight(self.RULER_HEIGHT + 6 + self.ROW_HEIGHT * max(1, len(self.tracks)))

    # ------------------------------------------------------------------ geometry
    def _x(self, tick: float) -> float:
        width = max(1, self.width() - self.LABEL_WIDTH)
        return self.LABEL_WIDTH + (tick - self.view_start) / self.view_span * width

    def tick_at(self, x: float) -> int:
        width = max(1, self.width() - self.LABEL_WIDTH)
        return round(self.view_start + (x - self.LABEL_WIDTH) / width * self.view_span)

    def _ruler_step(self) -> int:
        width = max(1, self.width() - self.LABEL_WIDTH)
        for step in (1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000):
            if step / self.view_span * width >= 46:
                return step
        return 20000

    # ------------------------------------------------------------------ painting
    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), BACKGROUND)
        height = self.height()
        x0, x1 = self._x(self.start), self._x(self.end)
        painter.fillRect(QRectF(x0, 0, max(1.0, x1 - x0), height), RECORDED)
        step = self._ruler_step()
        first = math.floor(self.view_start / step) * step
        tick = first
        painter.setPen(GRID)
        while tick <= self.view_start + self.view_span:
            x = self._x(tick)
            if x >= self.LABEL_WIDTH:
                painter.setPen(GRID)
                painter.drawLine(int(x), self.RULER_HEIGHT - 6, int(x), height)
                painter.setPen(TEXT)
                painter.drawText(int(x) + 3, 14, str(tick))
            tick += step
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(EDIT)
        for edit in self.edits:  # Blender-like keyframe diamonds
            x = self._x(edit)
            if x >= self.LABEL_WIDTH:
                y = self.RULER_HEIGHT - 4
                diamond = QPolygonF(
                    [
                        QPoint(int(x), y - 5),
                        QPoint(int(x) + 4, y),
                        QPoint(int(x), y + 5),
                        QPoint(int(x) - 4, y),
                    ]
                )
                painter.drawPolygon(diamond)
        self._paint_tracks(painter)
        painter.fillRect(QRectF(0, 0, self.LABEL_WIDTH, height), BACKGROUND)
        painter.setPen(TEXT)
        painter.drawText(8, 16, "tick")
        for row, track in enumerate(self.tracks):
            y = self.RULER_HEIGHT + 4 + row * self.ROW_HEIGHT
            painter.drawText(8, y + self.ROW_HEIGHT - 5, track.label)
        x = self._x(self.current)
        if x >= self.LABEL_WIDTH:
            painter.setPen(PLAYHEAD)
            painter.drawLine(int(x), 0, int(x), height)
            label = str(self.current)
            width = painter.fontMetrics().horizontalAdvance(label) + 8
            painter.fillRect(QRectF(x - width / 2, 1, width, 16), PLAYHEAD)
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(
                QRectF(x - width / 2, 1, width, 16), Qt.AlignmentFlag.AlignCenter, label
            )
        painter.end()

    def _paint_tracks(self, painter: QPainter) -> None:
        first = max(math.floor(self.view_start), self.start)
        last = min(math.ceil(self.view_start + self.view_span), self.end)
        for row, track in enumerate(self.tracks):
            top = self.RULER_HEIGHT + 4 + row * self.ROW_HEIGHT
            bottom = top + self.ROW_HEIGHT - 3
            painter.setPen(GRID)
            painter.drawLine(self.LABEL_WIDTH, bottom + 1, self.width(), bottom + 1)
            painter.setPen(Qt.PenStyle.NoPen)
            for tick in range(first, last + 1):
                value = track.samples.get(tick)
                if not value:
                    continue
                left, right = self._x(tick), self._x(tick + 1)
                level = value / 15
                bar = (bottom - top) * max(level, 0.12)
                color = QColor(SIGNAL)
                color.setAlphaF(0.35 + 0.65 * level)
                painter.fillRect(QRectF(left, bottom - bar, max(1.0, right - left), bar), color)

    # ------------------------------------------------------------------ input
    def mousePressEvent(self, event: QMouseEvent) -> None:
        x, y = event.position().x(), event.position().y()
        if event.button() == Qt.MouseButton.MiddleButton:
            self._pan_from = (int(x), self.view_start)
        elif event.button() == Qt.MouseButton.RightButton and x < self.LABEL_WIDTH:
            row = int((y - self.RULER_HEIGHT - 4) // self.ROW_HEIGHT)
            if 0 <= row < len(self.tracks):
                self.remove_monitor.emit(self.tracks[row].pos)
        elif event.button() == Qt.MouseButton.LeftButton and x >= self.LABEL_WIDTH:
            self._scrubbing = True
            self._scrub_to(x)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        x = event.position().x()
        if self._scrubbing:
            self._scrub_to(x)
        elif self._pan_from is not None:
            start_x, start_view = self._pan_from
            width = max(1, self.width() - self.LABEL_WIDTH)
            self.view_start = start_view - (x - start_x) / width * self.view_span
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._scrubbing = False
        self._pan_from = None
        self._last_scrub = None

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
            widget.setText(text)
            widget.setToolTip(tip)
            widget.clicked.connect(slot)
            row.addWidget(widget)
            return widget

        button("⏮", "Jump to start (Shift+Left)", lambda: self.jump.emit("start"))
        button("◆◀", "Previous edit (Down)", lambda: self.jump.emit("previous"))
        button("◀", "Tick back (Left); Ctrl+Left: one engine step", self.tick_back.emit)
        self.play = QToolButton()
        self.play.setText("▶")
        self.play.setCheckable(True)
        self.play.setToolTip("Run / pause (Space)")
        self.play.toggled.connect(self._toggled)
        row.addWidget(self.play)
        button("▶|", "Step one tick (Right); Ctrl+Right or E: one engine step", self.step_tick.emit)
        button("▶◆", "Next edit (Up)", lambda: self.jump.emit("next"))
        button("⏭", "Jump to end (Shift+Right)", lambda: self.jump.emit("end"))
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
        self.play.setText("⏸" if on else "▶")
        self.play_toggled.emit(on)

    def show_status(self, document: Document) -> None:
        engine, history = document.engine, document.history
        ahead = history.end - history.position
        future = f" · {ahead} recorded steps ahead" if ahead else ""
        self.status.setText(
            f"tick <b>{engine.game_time}</b> · {engine.phase.value} · next: "
            f"{engine.peek_next_step()} · step {history.position}/{history.end}{future}"
        )
        tracks = [
            Track(pos, f"{document.state_at(pos).block.name} {pos}", document.samples.get(pos, {}))
            for pos in document.monitors
        ]
        start = min(document.tick_steps) if document.tick_steps else engine.game_time
        edits = sorted(set(document.edit_ticks.values()))
        end = max(document.end_tick, engine.game_time)
        self.canvas.set_data(start, end, engine.game_time, edits, tracks)
