"""The Diagnostics tab: why the selected block last changed (its chain of causes, back
across ticks to the action that started it), pending scheduled ticks, queued block events
and the last step's trace; clicking or hovering a block's row or coordinates shows it in
the view, a double click on a cause goes to its tick."""

from __future__ import annotations

import re
from typing import Any

from PySide6.QtCore import QEvent, QObject, QPoint, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QHeaderView,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
)

from redsim.core.pos import Pos
from redsim.editor.document import Document
from redsim.sim import trace as tr
from redsim.sim.causes import why
from redsim.ui import theme
from redsim.ui.names import block_name
from redsim.ui.panel_widgets import HoverWatch, _placeholder

_POSITION = re.compile(r"\(?\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*\)?")


def first_position(text: str) -> Pos | None:
    """The first block position written as ``(x, y, z)`` or ``x, y, z`` in a line."""
    match = _POSITION.search(text)
    return None if match is None else (int(match[1]), int(match[2]), int(match[3]))


class DiagnosticsPanel(QTabWidget):
    """Pending scheduled ticks, queued block events, and the last step's trace. Clicking a
    row or a trace line with coordinates asks for that block to be highlighted."""

    highlight_requested = Signal(object)  # Pos
    position_hovered = Signal(object)  # Pos | None
    tick_requested = Signal(object, int)  # Pos | None, tick: go there (a cause's tick)

    def __init__(self) -> None:
        super().__init__()
        self.setProperty("subtabs", True)  # second-level tabs (theme)
        self.why = QListWidget()
        self.why.setWordWrap(True)
        self.why.setToolTip(
            "Why the selected block last changed, newest first: each line was caused by the "
            "one below it.\nClick: show the block · double click: go to that tick"
        )
        self.addTab(self.why, "Why?")
        self.why.itemClicked.connect(self._event_clicked)
        self.why.itemDoubleClicked.connect(self._cause_double_clicked)
        self.why.setMouseTracking(True)
        self.why.itemEntered.connect(self._hover_item)
        HoverWatch(self.why.viewport(), lambda: None, self._unhover, self._why_moved)
        self.ticks = QTableWidget(0, 5)
        self.ticks.setHorizontalHeaderLabels(["At tick", "Block", "Pos", "Priority", "Sub-tick"])
        self.ticks.verticalHeader().setVisible(False)
        header = self.ticks.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setStretchLastSection(True)
        self.ticks.setShowGrid(False)
        self.ticks.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.addTab(self.ticks, "Scheduled ticks")
        self.events = QListWidget()
        self.addTab(self.events, "Block events")
        self.trace = QPlainTextEdit()
        self.trace.setReadOnly(True)
        self.trace.setPlaceholderText("Step a tick (Right) to see what it did, update by update.")
        self.trace.setStyleSheet(f"font-family: {theme.MONO_FAMILY}; font-size: 11px;")
        self.addTab(self.trace, "Last step trace")
        self.ticks.cellClicked.connect(self._tick_clicked)
        self.events.itemClicked.connect(self._event_clicked)
        self.trace.cursorPositionChanged.connect(self._trace_clicked)
        # Hovering a row or a trace line lights its block up in the view.
        self.ticks.setMouseTracking(True)
        self.ticks.cellEntered.connect(lambda row, _: self._hover_item(self.ticks.item(row, 0)))
        self.events.setMouseTracking(True)
        self.events.itemEntered.connect(self._hover_item)
        self.trace.viewport().setMouseTracking(True)
        self.trace.viewport().installEventFilter(self)
        HoverWatch(self.ticks.viewport(), lambda: None, self._unhover, self._ticks_moved)
        HoverWatch(self.events.viewport(), lambda: None, self._unhover, self._events_moved)

    def _unhover(self) -> None:
        self.position_hovered.emit(None)

    def _ticks_moved(self, point: QPoint) -> None:
        if self.ticks.rowAt(point.y()) < 0:  # below the last row
            self._unhover()

    def _why_moved(self, point: QPoint) -> None:
        if self.why.itemAt(point) is None:
            self._unhover()

    def _cause_double_clicked(self, item: QListWidgetItem) -> None:
        tick = item.data(Qt.ItemDataRole.UserRole + 1)
        if tick is not None:
            pos = item.data(Qt.ItemDataRole.UserRole)
            self.tick_requested.emit(tuple(pos) if pos is not None else None, int(tick))

    def _events_moved(self, point: QPoint) -> None:
        if self.events.itemAt(point) is None:
            self._unhover()

    def _hover_item(self, item: Any) -> None:
        pos = item.data(Qt.ItemDataRole.UserRole) if item is not None else None
        self.position_hovered.emit(tuple(pos) if pos is not None else None)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802
        if watched is self.trace.viewport():
            if event.type() == QEvent.Type.MouseMove:
                point = event.position().toPoint()  # type: ignore[attr-defined]
                line = self.trace.cursorForPosition(point).block().text()
                self.position_hovered.emit(first_position(line))
            elif event.type() == QEvent.Type.Leave:
                self.position_hovered.emit(None)
        return super().eventFilter(watched, event)

    def _tick_clicked(self, row: int, column: int) -> None:
        item = self.ticks.item(row, 0)
        pos = item.data(Qt.ItemDataRole.UserRole) if item is not None else None
        if pos is not None:
            self.highlight_requested.emit(tuple(pos))

    def _event_clicked(self, item: QListWidgetItem) -> None:
        pos = item.data(Qt.ItemDataRole.UserRole)
        if pos is not None:
            self.highlight_requested.emit(tuple(pos))

    def _trace_clicked(self) -> None:
        pos = first_position(self.trace.textCursor().block().text())
        if pos is not None:
            self.highlight_requested.emit(pos)

    def show_why(self, document: Document, pos: Pos | None) -> None:
        """The chain of causes of the selected block's last change."""
        self.why.clear()
        if pos is None:
            hint = "Select a block (click it, or E over it) to see why it last changed."
            self.why.addItem(_placeholder(QListWidgetItem(hint)))
            return
        name = block_name(document.state_at(pos).block.id)
        where = " ".join(str(v) for v in pos)
        causes = why(document.level.trace, pos, block_name)
        if not causes:
            text = (
                f"{name} at {where} has not changed since the build (tick 0), or it changed "
                "too long ago to be in the kept trace."
            )
            self.why.addItem(_placeholder(QListWidgetItem(text)))
            return
        header = QListWidgetItem(f"Why {name} at {where} changed at tick {causes[0].tick}:")
        header.setForeground(QColor(theme.GOLD))
        self.why.addItem(header)
        branch = 0
        for depth, cause in enumerate(causes):
            if cause.branch != branch:  # where a piston's power comes from
                branch = cause.branch
                title = QListWidgetItem("Where the piston's power comes from:")
                title.setForeground(QColor(theme.GOLD))
                self.why.addItem(title)
            at = " ".join(str(v) for v in cause.pos) if cause.pos is not None else "—"
            first = depth == 0 or (branch and causes[depth - 1].branch != branch)
            arrow = "" if first else "← "
            entry = QListWidgetItem(f"{arrow}tick {cause.tick} · {at} · {cause.text}")
            if cause.pos is not None:
                entry.setData(Qt.ItemDataRole.UserRole, list(cause.pos))
            entry.setData(Qt.ItemDataRole.UserRole + 1, cause.tick)
            self.why.addItem(entry)

    def show_state(
        self, document: Document, last_steps: list[Any], selected: Pos | None = None
    ) -> None:
        self.show_why(document, selected)
        level = document.level
        collected = list(level.block_ticks.to_run)
        pending = level.block_ticks.pending()
        rows = [("this tick", t) for t in collected] + [(str(t.trigger_tick), t) for t in pending]
        self.ticks.clearSpans()
        self.ticks.setRowCount(len(rows))
        for row, (when, tick) in enumerate(rows):
            values = [
                when,
                block_name(tick.block_id),
                " ".join(str(c) for c in tick.pos),
                tick.priority.name.replace("_", " ").lower(),
                str(tick.sub_tick),
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, list(tick.pos))
                item.setToolTip("Click: highlight it in the viewport")
                self.ticks.setItem(row, column, item)
        if not rows:
            self.ticks.setRowCount(1)
            self.ticks.setSpan(0, 0, 1, self.ticks.columnCount())
            self.ticks.setItem(0, 0, _placeholder(QTableWidgetItem("No scheduled ticks pending.")))
        self.events.clear()
        for pos, block_id, b0, b1 in level.block_events:
            entry = QListWidgetItem(f"{block_name(block_id)} at {pos}: ({b0}, {b1})")
            entry.setData(Qt.ItemDataRole.UserRole, list(pos))
            self.events.addItem(entry)
        if not level.block_events:
            empty = QListWidgetItem("No block events queued (pistons queue them).")
            self.events.addItem(_placeholder(empty))
        lines: list[str] = []
        trace = level.trace
        for step in last_steps[-40:]:
            lines.append(step.describe())
            if step.record is None:
                continue
            depth = {step.record: 0}
            for record in trace.after(step.record):
                if record.step != step.index:
                    break
                level_depth = depth.get(record.parent, 0) + 1 if record.parent is not None else 1
                depth[record.id] = level_depth
                if record.kind == tr.SHAPE_UPDATE and not record.detail.get("changed"):
                    continue  # unchanged shape updates are noise in this view
                lines.append("  " * level_depth + record.summary())
        self.trace.setPlainText("\n".join(lines[-2000:]))
