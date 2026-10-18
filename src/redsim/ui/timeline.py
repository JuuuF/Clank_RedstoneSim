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
import time
from dataclasses import dataclass

from PySide6.QtCore import QEvent, QPoint, QPointF, QRectF, Qt, QTimer, Signal
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
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QToolButton,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

from redsim.core.pos import Pos
from redsim.editor.document import EDIT_ROWS, Document, EditBatch, Pulse, edit_row
from redsim.editor.lines import BLOCKS_GROUP, LineGroup
from redsim.ui import pixel_icons, theme
from redsim.ui.icons import block_pixmap
from redsim.ui.names import block_name
from redsim.ui.timeline_common import (
    BACKGROUND,
    COMPACT,
    GLIDE_LOOKAHEAD,
    GRID,
    PLAYHEAD,
    RECORDED,
    ROW_COLORS,
    ROW_TITLES,
    RULER,
    SIGNAL,
    TEXT,
    TEXT_DIM,
)
from redsim.ui.timeline_lines import EditEvent, LineArea, _Line
from redsim.ui.timeline_markers import MarkerArea, fill_marker_menu


@dataclass
class Track:
    pos: Pos
    label: str
    samples: dict[int, int]
    block: str = ""  # block id, for the row's icon


class TimelineCanvas(MarkerArea, LineArea, QWidget):
    scrub = Signal(int)  # tick (since tick 0)
    remove_monitor = Signal(object)  # Pos
    add_marker = Signal(int)  # tick
    rename_marker = Signal(int)  # tick
    delete_marker = Signal(int)  # tick
    move_marker = Signal(int, int)  # tick, new tick
    move_edits = Signal(object, int)  # step indices, delta ticks
    merge_edits = Signal(object, object)  # step indices, target tick (None: earliest)
    delete_edits = Signal(object)  # step indices
    set_tick_zero = Signal()
    pulses_changed = Signal(object)  # [(index, tick, strength, ticks, pos)]
    pulses_deleted = Signal(object)  # [index]
    pulses_muted = Signal(object, bool)  # [index], muted (bypassed, kept in the timeline)
    position_hovered = Signal(object)  # Pos | None: a line's block, to show in the view
    pulse_added = Signal(object, int)  # Pos, tick
    line_moved = Signal(str, object, int, int)  # category, Pos, group, row
    #: action ("toggle", "rename", "color", …), category, group
    group_request = Signal(str, str, int)
    line_group_new = Signal(str, object)  # category, Pos: a new group holding this line

    LABEL_WIDTH = 180
    INDENT = 12
    RULER_HEIGHT = 26  # grows by MARKER_STRIP while there are markers (their names)
    MARKER_STRIP = 14
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
        self.pulse_spans: list[tuple[int, int]] = []  # sequence pulses: (start, ticks)
        self.pulses: list[Pulse] = []
        self.events: list[EditEvent] = []
        self.groups: dict[str, list[LineGroup]] = {}  # each category's line groups
        self.names: dict[Pos, str] = {}  # block names for the per-block lines
        self.expanded: set[str] = set()  # categories showing their per-block lines
        self.lines: list[_Line] = []
        self._tops: list[int] = []
        #: A block line being reordered: (its category, its position, the press y).
        self._line_drag: tuple[str, Pos, float] | None = None
        self._drop_y: float | None = None
        #: Selected pulses (their edit indices); Del deletes them, a drag moves them all.
        self.selected_pulses: set[int] = set()
        #: A drag of the selected pulses: (the pulse pressed, "move" | "resize", press
        #: x, its line among the Powered lines), and the offset so far (ticks, lines).
        self._pulse_drag: tuple[Pulse, str, float, int] | None = None
        self._drag_offset: tuple[int, int] = (0, 0)
        self._pulse_additive = False
        self._hovered_pos: Pos | None = None
        self.selected: set[tuple[int, str]] = set()  # (tick, row)
        #: Single edits selected on the per-block lines (their step indices), and after
        #: moving them, where they went (row, position, tick: indices change on a move).
        self.selected_events: set[int] = set()
        self._moved_events: set[tuple[str, Pos, int]] = set()
        self.tracks: list[Track] = []
        self._scrubbing = False
        self._pan_from: tuple[int, float] | None = None
        self._last_scrub: int | None = None
        self._drag_from: tuple[float, float] | None = None  # press point in the edit rows
        self._dragging_edits = False
        self._drag_delta = 0
        self._band: QRectF | None = None
        self.setMouseTracking(True)
        self._hover_tick: int | None = None  # a track's tick under the cursor
        self.markers: dict[int, str] = {}  # tick → name (Blender-style markers)
        self.selected_marker: int | None = None
        #: A pressed marker: (its tick, the press x); and where dragging it would put it.
        self._marker_drag: tuple[int, float] | None = None
        self._marker_to: int | None = None
        # While playing, the playhead glides between the ticks the panels show (they are
        # refreshed a few times a second) instead of jumping: ticks per second (negative
        # when playing backwards) and where the glide started (tick, time).
        self._glide_rate: float | None = None
        self._glide_base = (0.0, 0.0)
        self._glide_timer = QTimer(self)
        self._glide_timer.setInterval(16)
        self._glide_timer.timeout.connect(self.update)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self._build_lines()
        self._resize_to_tracks()

    # ------------------------------------------------------------------ data
    def set_data(
        self,
        start: int,
        end: int,
        current: int,
        batches: list[EditBatch],
        tracks: list[Track],
        pulse_spans: list[tuple[int, int]] | None = None,
        pulses: list[Pulse] | None = None,
        events: list[EditEvent] | None = None,
        groups: dict[str, list[LineGroup]] | None = None,
        names: dict[Pos, str] | None = None,
    ) -> None:
        if self._glide_rate is not None:  # carry on from where the playhead is shown
            now = time.monotonic()
            shown = self.shown_tick(now)
            gap = self._glide_gap()
            self._glide_base = (min(max(shown, current - gap), current + gap), now)
        self.start, self.end, self.current = start, end, current
        self.batches, self.tracks = batches, tracks
        self.pulse_spans = pulse_spans or []
        self.pulses = pulses or []
        self.selected_pulses &= {pulse.index for pulse in self.pulses}
        self.events = events or []
        if self._moved_events:
            moved, self._moved_events = self._moved_events, set()
            self.selected_events = {e.index for e in self.events if (e.row, e.pos, e.tick) in moved}
        else:
            self.selected_events &= {e.index for e in self.events}
        self.groups = groups or {}
        self.names = names or {}
        self._build_lines()
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
        """The selected keyframes' edits and the single edits selected on block lines."""
        chosen = {i for b in self.batches if (b.tick, b.row) in self.selected for i in b.indices}
        return sorted(chosen | self.selected_events)

    def _selected_ticks(self) -> set[int]:
        ticks = {tick for tick, _ in self.selected}
        return ticks | {e.tick for e in self.events if e.index in self.selected_events}

    # ------------------------------------------------------------------ geometry
    def _x(self, tick: float) -> float:
        width = max(1, self.width() - self.LABEL_WIDTH)
        return self.LABEL_WIDTH + (tick - self.view_start) / self.view_span * width

    def tick_at(self, x: float) -> int:
        width = max(1, self.width() - self.LABEL_WIDTH)
        return round(self.view_start + (x - self.LABEL_WIDTH) / width * self.view_span)

    def column_at(self, x: float) -> int:
        """The tick whose column (a track sample spans [tick, tick + 1)) is under ``x``."""
        width = max(1, self.width() - self.LABEL_WIDTH)
        return math.floor(self.view_start + (x - self.LABEL_WIDTH) / width * self.view_span)

    def _row_top(self, row: int) -> int:
        """The top of category ``EDIT_ROWS[row]``'s line."""
        name = EDIT_ROWS[row]
        for line, top in zip(self.lines, self._tops, strict=True):
            if line.kind == "category" and line.row == name:
                return top
        return self.RULER_HEIGHT + row * self.EDIT_ROW_HEIGHT

    def _tracks_top(self) -> int:
        bottom = self._tops[-1] + self.EDIT_ROW_HEIGHT if self._tops else self.RULER_HEIGHT
        return bottom + 2

    def _edit_row_at(self, y: float) -> int | None:
        index = self._line_at(y)
        if index is None or self.lines[index].kind != "category":
            return None
        return EDIT_ROWS.index(self.lines[index].row)

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
        if self._hover_tick is not None and self.tracks:  # the hovered tick column
            left, right = self._x(self._hover_tick), self._x(self._hover_tick + 1)
            top = self._tracks_top()
            column = QRectF(left, top, max(1.0, right - left), self.height() - top)
            painter.fillRect(column, QColor(255, 255, 255, 22))
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
        metrics = painter.fontMetrics()
        for line, top in zip(self.lines, self._tops, strict=True):
            left = 4 + line.depth * self.INDENT
            if line.expandable:  # ▸ / ▾
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(TEXT_DIM)
                cx, cy = left + 3.5, top + self.EDIT_ROW_HEIGHT / 2
                arrow = (
                    [QPointF(cx - 3, cy - 2), QPointF(cx + 3, cy - 2), QPointF(cx, cy + 2)]
                    if line.expanded
                    else [QPointF(cx - 2, cy - 3), QPointF(cx + 2, cy), QPointF(cx - 2, cy + 3)]
                )
                painter.drawPolygon(QPolygonF(arrow))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(line.color)
            if line.kind == "category":
                painter.drawEllipse(QRectF(left + 10, top + 4, 7, 7))
            elif line.kind == "group":
                painter.drawRoundedRect(QRectF(left + 10, top + 3, 9, 9), 2, 2)
            else:
                painter.drawRect(QRectF(left + 2, top + 2, 3, self.EDIT_ROW_HEIGHT - 4))
            painter.setPen(TEXT if line.kind != "block" else TEXT_DIM)
            text_x = left + (24 if line.kind != "block" else 10)
            if line.kind == "block":  # the position bright, what is there now dim
                painter.setPen(TEXT)
                painter.drawText(text_x, top + self.EDIT_ROW_HEIGHT - 3, line.title)
                detail_x = text_x + metrics.horizontalAdvance(line.title) + 6
                detail = metrics.elidedText(
                    line.detail, Qt.TextElideMode.ElideRight, self.LABEL_WIDTH - detail_x - 4
                )
                painter.setPen(TEXT_DIM)
                painter.drawText(detail_x, top + self.EDIT_ROW_HEIGHT - 3, detail)
                continue
            title = metrics.elidedText(
                line.title, Qt.TextElideMode.ElideRight, self.LABEL_WIDTH - text_x - 4
            )
            painter.drawText(text_x, top + self.EDIT_ROW_HEIGHT - 3, title)
        if self._line_drag is not None and self._drop_y is not None:  # where it will go
            painter.setPen(QPen(QColor(255, 255, 255), 2))
            painter.drawLine(QPointF(4, self._drop_y), QPointF(self.width(), self._drop_y))
        for row, track in enumerate(self.tracks):
            y = self._tracks_top() + row * self.ROW_HEIGHT
            text_x = 8
            if track.block:
                painter.drawPixmap(6, y + 2, block_pixmap(track.block, 14))
                text_x = 24
            # The position right-aligned and dim, the name shortened to what is left.
            metrics = painter.fontMetrics()
            where = " ".join(str(c) for c in track.pos)
            where_x = self.LABEL_WIDTH - 6 - metrics.horizontalAdvance(where)
            name = metrics.elidedText(
                track.label, Qt.TextElideMode.ElideRight, where_x - text_x - 6
            )
            painter.drawText(text_x, y + self.ROW_HEIGHT - 5, name)
            painter.setPen(TEXT_DIM)
            painter.drawText(where_x, y + self.ROW_HEIGHT - 5, where)
            painter.setPen(TEXT)
        self._paint_markers(painter)
        shown = self.shown_tick()
        x = self._x(shown)
        if x >= self.LABEL_WIDTH:
            painter.setPen(PLAYHEAD)
            painter.drawLine(QPointF(x, 0), QPointF(x, height))
            label = str(math.floor(shown))
            width = max(20, painter.fontMetrics().horizontalAdvance(label) + 10)
            left = max(x - width / 2, float(self.LABEL_WIDTH))  # tick 0 sits at the edge
            badge = QRectF(left, 1, width, 17)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(PLAYHEAD)
            painter.drawRoundedRect(badge, 4, 4)
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(badge, Qt.AlignmentFlag.AlignCenter, label)
        painter.end()

    def set_running(self, rate: float | None) -> None:
        """Playing at ``rate`` ticks per second (negative: backwards), or None: paused, the
        playhead snaps to the exact tick."""
        if rate is None:
            self._glide_rate = None
            self._glide_timer.stop()
        else:
            if self._glide_rate is None:
                self._glide_base = (float(self.current), time.monotonic())
            self._glide_rate = rate
            self._glide_timer.start()
        self.update()

    def _glide_gap(self) -> float:
        """How far the shown playhead may run ahead of (or behind) the known tick."""
        return max(1.0, abs(self._glide_rate or 0.0) * GLIDE_LOOKAHEAD)

    def shown_tick(self, now: float | None = None) -> float:
        """Where the playhead is drawn: the tick when paused, else gliding."""
        rate = self._glide_rate
        if rate is None:
            return float(self.current)
        base, since = self._glide_base
        moved = base + ((now if now is not None else time.monotonic()) - since) * rate
        gap = self._glide_gap()
        return min(max(moved, self.current - gap), self.current + gap)

    def _paint_edit_rows(self, painter: QPainter) -> None:
        painter.setPen(GRID)
        for line, top in zip(self.lines, self._tops, strict=True):
            if line.kind != "block":  # groups and categories are separated by a line
                painter.drawLine(self.LABEL_WIDTH, top, self.width(), top)
            else:
                band = QColor(line.color)
                band.setAlpha(14)
                painter.fillRect(
                    QRectF(self.LABEL_WIDTH, top, self.width(), self.EDIT_ROW_HEIGHT), band
                )
        bottom = self._tracks_top() - 2
        painter.drawLine(self.LABEL_WIDTH, bottom, self.width(), bottom)
        self._paint_block_lines(painter)
        shift = self._drag_delta if self._dragging_edits else 0
        # Sequence pulses: how long each stays on, as a bar on the Powered row.
        power_y = self._row_top(EDIT_ROWS.index("power")) + self.EDIT_ROW_HEIGHT / 2
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 70, 70, 110))
        for start, length in self.pulse_spans:
            left = max(float(self.LABEL_WIDTH), self._x(start))
            right = self._x(start + length)
            if right > left:
                painter.drawRoundedRect(QRectF(left, power_y - 3, right - left, 6), 2, 2)
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
        if self._marker_press(event):
            return
        index = self._line_at(y)
        if index is not None and self._line_press(event, self.lines[index], self._tops[index]):
            return
        if button == Qt.MouseButton.RightButton:
            if x < self.LABEL_WIDTH and y >= self._tracks_top():
                row = int((y - self._tracks_top()) // self.ROW_HEIGHT)
                if 0 <= row < len(self.tracks):
                    self.remove_monitor.emit(self.tracks[row].pos)
                return
            batch = self._batch_at(x, y)
            if batch is not None and (batch.tick, batch.row) not in self.selected:
                self.selected, self.selected_events = {(batch.tick, batch.row)}, set()
                self.update()
            self._context_menu(
                event.globalPosition().toPoint(), self._edit_row_at(y), self.tick_at(x)
            )
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
                    self.selected, self.selected_events = {key}, set()
                self._drag_from = (x, y)
                self._dragging_edits = False
                self._drag_delta = 0
            else:
                if not additive:
                    self.selected, self.selected_events = set(), set()
                self._band = QRectF(x, y, 0, 0)
                self._drag_from = (x, y)
            self.update()
            return
        self._scrubbing = True
        self._scrub_to(x)

    # ------------------------------------------------------------------ lines

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        x, y = event.position().x(), event.position().y()
        self._hover_position(y)
        if self._marker_move(event):
            return
        if self._pulse_drag is not None:
            pulse, mode, start_x, start_line = self._pulse_drag
            dt = self.tick_at(x) - self.tick_at(start_x)
            dl = self._drag_offset[1]
            index = self._line_at(y)
            if mode == "move" and index is not None:
                line = self.lines[index]
                order = self._power_positions()
                if line.kind == "block" and line.row == "power" and line.pos in order:
                    dl = order.index(line.pos) - start_line
            self._drag_offset = (dt, dl)
            tick, ticks, pos = self._previewed(pulse)
            where = " ".join(str(v) for v in pos)
            QToolTip.showText(
                event.globalPosition().toPoint(), f"tick {tick} · {ticks} ticks · at {where}"
            )
            self.update()
            return
        if self._line_drag is not None:
            target = self._drop_target(self._line_drag[0], y)
            self._drop_y = target[2] if target is not None else None
            self.update()
            return
        index = self._line_at(y)
        if index is not None and x >= self.LABEL_WIDTH:
            line = self.lines[index]
            hit = (
                self._pulse_hit(line, x, self._tops[index])
                if line.kind == "block" and line.row == "power"
                else None
            )
            shape = (
                Qt.CursorShape.SizeHorCursor
                if hit is not None and hit[1] == "resize"
                else Qt.CursorShape.OpenHandCursor
                if hit is not None
                else Qt.CursorShape.ArrowCursor
            )
            edits = self._event_hit(line, x) if hit is None else []
            if edits:
                shape = Qt.CursorShape.OpenHandCursor
            self.setCursor(shape)
            if edits:
                where = " ".join(map(str, edits[0].pos))
                labels = "\n".join(e.label for e in edits[:12])
                QToolTip.showText(
                    event.globalPosition().toPoint(),
                    f"{ROW_TITLES[line.row]} at tick {edits[0].tick} ({where}):\n{labels}\n"
                    "Drag to move only these edits to another tick (Shift: select more)",
                )
                return
            if hit is not None:
                pulse = hit[0]
                QToolTip.showText(
                    event.globalPosition().toPoint(),
                    f"Pulse at {' '.join(map(str, pulse.pos))}: tick {pulse.tick}, "
                    f"{pulse.ticks} ticks, strength {pulse.strength}\n"
                    "Drag to move, drag its end to change the duration, right click to delete",
                )
                return
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
        elif self._drag_from is not None and (self.selected or self.selected_events):
            delta = self.tick_at(x) - self.tick_at(self._drag_from[0])
            if abs(x - self._drag_from[0]) > 4 or self._dragging_edits:
                self._dragging_edits = True
                earliest = min(self._selected_ticks())
                self._drag_delta = max(delta, -earliest)
                QToolTip.showText(event.globalPosition().toPoint(), f"{self._drag_delta:+d} ticks")
                self.update()
        elif self._marker_hover(event):
            return
        else:
            batch = self._batch_at(x, y)
            reading = self.track_reading(x, y)
            hover = self.column_at(x) if reading is not None else None
            if hover != self._hover_tick:  # the hovered tick column of a track
                self._hover_tick = hover
                self.update()
            if batch is not None:
                self._hover_batch(batch)
                lines = list(batch.labels[:12])
                if len(batch.labels) > 12:
                    lines.append(f"… {len(batch.labels) - 12} more")
                title = f"{ROW_TITLES[batch.row]} at tick {batch.tick}: {len(batch.labels)} edits"
                QToolTip.showText(event.globalPosition().toPoint(), "\n".join([title, *lines]))
            elif reading is not None:
                QToolTip.showText(event.globalPosition().toPoint(), reading)
            else:
                QToolTip.hideText()

    def _hover_batch(self, batch: EditBatch) -> None:
        """A hovered diamond lights up the block of its first edit (F goes there)."""
        first = batch.indices[0] if batch.indices else None
        pos = next((event.pos for event in self.events if event.index == first), None)
        if pos is not None and pos != self._hovered_pos:
            self._hovered_pos = pos
            self.position_hovered.emit(pos)

    def track_reading(self, x: float, y: float) -> str | None:
        """The monitored value under the cursor: "Redstone Lamp 4 1 -2 · tick 23: 15"."""
        if x < self.LABEL_WIDTH or y < self._tracks_top():
            return None
        row = int((y - self._tracks_top()) // self.ROW_HEIGHT)
        if not 0 <= row < len(self.tracks):
            return None
        tick = self.column_at(x)
        if not self.start <= tick <= self.end:
            return None
        track = self.tracks[row]
        where = " ".join(str(c) for c in track.pos)
        value = track.samples.get(tick)
        shown = "not recorded" if value is None else str(value)
        return f"{track.label} {where} · tick {tick}: {shown}"

    def leaveEvent(self, event: object) -> None:
        if self._hovered_pos is not None:
            self._hovered_pos = None
            self.position_hovered.emit(None)
        if self._hover_tick is not None:
            self._hover_tick = None
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._marker_release():
            return
        if self._pulse_drag is not None:
            pressed = self._pulse_drag[0]
            changes = []
            if self._drag_offset != (0, 0):
                for pulse in self.pulses:
                    if pulse.index in self.selected_pulses:
                        tick, ticks, pos = self._previewed(pulse)
                        if (tick, ticks, pos) != (pulse.tick, pulse.ticks, pulse.pos):
                            changes.append((pulse.index, tick, pulse.strength, ticks, pos))
            elif not self._pulse_additive:  # a plain click: just this pulse
                self.selected_pulses = {pressed.index}
            self._pulse_drag, self._drag_offset = None, (0, 0)
            if changes:
                self.pulses_changed.emit(changes)
            self.update()
            return
        if self._line_drag is not None:
            row, pos = self._line_drag[0], self._line_drag[1]
            target = self._drop_target(row, event.position().y())
            self._line_drag, self._drop_y = None, None
            if target is not None:
                self.line_moved.emit(row, pos, target[0], target[1])
            self.update()
            return
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
            delta = self._drag_delta
            chosen = self.selected_indices()
            self._moved_events = {
                (e.row, e.pos, max(0, e.tick + delta))
                for e in self.events
                if e.index in self.selected_events
            }
            self.selected = {(tick + delta, row) for tick, row in self.selected}
            self._dragging_edits = False
            self.move_edits.emit(chosen, delta)
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
        chosen = self.selected or self.selected_events or self.selected_pulses
        if event.type() == QEvent.Type.ShortcutOverride:
            key = event.key()  # type: ignore[attr-defined]
            marker_keys = (Qt.Key.Key_Delete, Qt.Key.Key_Backspace, Qt.Key.Key_F2)
            if (chosen and key in (*marker_keys[:2], Qt.Key.Key_M, Qt.Key.Key_0)) or (
                self.selected_marker is not None and key in marker_keys
            ):
                event.accept()
                return True
        return super().event(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        """A double click on a marker renames it."""
        tick = self.marker_at(event.position().x(), event.position().y())
        if tick is not None and event.button() == Qt.MouseButton.LeftButton:
            self._marker_drag, self._marker_to = None, None
            self.rename_marker.emit(tick)
            return
        LineArea.mouseDoubleClickEvent(self, event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if self._marker_key(event.key()):
            return
        if self.selected_pulses and event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.pulses_deleted.emit(sorted(self.selected_pulses))
            self.selected_pulses = set()
        elif self.selected_pulses and event.key() == Qt.Key.Key_0:  # Ableton: (de)activate
            chosen = [p for p in self.pulses if p.index in self.selected_pulses]
            self.pulses_muted.emit([p.index for p in chosen], not all(p.muted for p in chosen))
        elif (self.selected or self.selected_events) and event.key() in (
            Qt.Key.Key_Delete,
            Qt.Key.Key_Backspace,
        ):
            indices = self.selected_indices()
            self.selected, self.selected_events = set(), set()
            self.delete_edits.emit(indices)
        elif (self.selected or self.selected_events) and event.key() == Qt.Key.Key_M:
            self.merge_edits.emit(self.selected_indices(), None)
        else:
            super().keyPressEvent(event)

    def _context_menu(self, where: QPoint, row: int | None, tick: int) -> None:
        menu = QMenu(self)
        tick = max(0, tick)
        name = self.markers.get(tick)
        marker = menu.addAction(
            f"Add marker at tick {tick}…" if name is None else f"Rename marker “{name}”…"
        )
        marker.setIcon(pixel_icons.pixel_icon("marker"))
        marker.triggered.connect(lambda: self.add_marker.emit(tick))
        menu.addSeparator()
        chosen = self.selected_indices()
        ticks = self._selected_ticks()
        merge = menu.addAction("Merge selected into the earliest tick (M)")
        merge.setEnabled(len(ticks) > 1)
        merge.setIcon(pixel_icons.pixel_icon("previous"))
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
        delete.setIcon(pixel_icons.pixel_icon("delete"))
        delete.triggered.connect(lambda: self.delete_edits.emit(chosen))
        menu.addSeparator()
        zero = menu.addAction("Set tick 0 here (the current state becomes the build)")
        zero.setIcon(pixel_icons.pixel_icon("tick_zero"))
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
    #: "start" | "end" | "previous" | "next" | "previous_marker" | "next_marker"
    jump = Signal(str)
    set_tick_zero = Signal()
    add_marker = Signal()  # at the current tick
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
                widget.setStyleSheet(COMPACT)
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
        self.reverse.setStyleSheet(COMPACT)
        self.reverse.setIcon(pixel_icons.pixel_icon("reverse"))
        self.reverse.setCheckable(True)
        self.reverse.setToolTip("Play backwards / pause (Ctrl+Shift+Space)")
        self.reverse.toggled.connect(self._reverse_toggled)
        row.addWidget(self.reverse)
        self.play = QToolButton()
        self.play.setIconSize(pixel_icons.ICON_SIZE)
        self.play.setStyleSheet(COMPACT)
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
        zero.setIcon(pixel_icons.pixel_icon("tick_zero"))
        zero.setIconSize(pixel_icons.ICON_SIZE)
        zero.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        row.addSpacing(8)
        button(
            "previous_marker",
            "Previous marker (Ctrl+Shift+Left)",
            lambda: self.jump.emit("previous_marker"),
        )
        # Click: add a marker here; the arrow: every marker, rename and delete.
        self.marker_button = QToolButton()
        self.marker_button.setIcon(pixel_icons.pixel_icon("marker"))
        self.marker_button.setIconSize(pixel_icons.ICON_SIZE)
        self.marker_button.setText("Marker")
        self.marker_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.marker_button.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        self.marker_button.setToolTip(
            "Add a marker at the current tick (Ctrl+M).\n"
            "The arrow lists the markers: jump to one, rename or delete it."
        )
        self.marker_button.clicked.connect(self.add_marker.emit)
        self.marker_menu = QMenu(self.marker_button)
        self.marker_menu.aboutToShow.connect(self._fill_marker_menu)
        self.marker_button.setMenu(self.marker_menu)
        row.addWidget(self.marker_button)
        button(
            "next_marker", "Next marker (Ctrl+Shift+Right)", lambda: self.jump.emit("next_marker")
        )
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
        # The canvas grows with its lines; the bar is resizable (the window's splitter)
        # and scrolls when the lines do not fit.
        self.scroller = QScrollArea()
        self.scroller.setWidget(self.canvas)
        self.scroller.setWidgetResizable(True)
        self.scroller.setFrameShape(QFrame.Shape.NoFrame)
        self.scroller.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        layout.addWidget(self.scroller, 1)

    def _fill_marker_menu(self) -> None:
        fill_marker_menu(self.marker_menu, self.canvas, self.add_marker.emit)

    def preferred_height(self) -> int:
        """The transport row and all of the canvas (every line) without scrolling."""
        layout = self.layout()
        first = layout.itemAt(0) if layout is not None else None
        transport = first.sizeHint().height() if first is not None else 40
        return transport + self.canvas.height() + 4

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
                block_name(document.state_at(pos).block.id),
                document.samples.get(pos, {}),
                document.state_at(pos).block.id,
            )
            for pos in document.monitors
        ]
        self.canvas.set_markers(document.visible_markers())
        pulses = document.pulses()
        spans = [(pulse.tick, pulse.ticks) for pulse in pulses]
        inputs = document.history.inputs
        events = [
            EditEvent(index, t, edit_row(inputs[index]), inputs[index].pos, inputs[index].label)
            for index, t in document.edit_ticks.items()
            if index in inputs
        ]
        document.lines.sync(pulse.pos for pulse in pulses)
        in_order = sorted(events, key=lambda e: (e.tick, e.index))
        for row in EDIT_ROWS:  # the other categories: positions in order of their edits
            if row != "power":
                positions_of_row = (e.pos for e in in_order if e.row == row)
                document.lines_of(row).sync(positions_of_row, BLOCKS_GROUP, ROW_COLORS[row].name())
        positions = {pulse.pos for pulse in pulses} | {event.pos for event in events}
        labels = {lab.pos: f"@{name} " for name, lab in sorted(document.labels.items())}
        names = {  # what is at each line's position at the current tick (and its label)
            pos: labels.get(pos, "") + ("empty" if state.is_air else block_name(state.block.id))
            for pos in positions
            for state in (document.state_at(pos),)
        }
        self.canvas.set_data(
            0,
            end,
            tick,
            document.edit_batches(),
            tracks,
            spans,
            pulses,
            events,
            {row: document.lines_of(row).groups for row in EDIT_ROWS},
            names,
        )


__all__ = [
    "EditEvent",
    "GLIDE_LOOKAHEAD",
    "ROW_COLORS",
    "ROW_TITLES",
    "TimelineBar",
    "TimelineCanvas",
    "Track",
]
