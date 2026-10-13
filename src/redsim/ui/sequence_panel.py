"""The Sequence tab: the power pulses of the document (ANIMATE mode adds them by clicking
blocks), each with its start tick, position, strength and duration, editable in place.

Pulses belong to positions, not blocks: whatever block is at the position while the pulse
runs receives the power (``Level.forced_power``). Changing a value re-runs the history
from tick 0 with the new sequence (one undo step).
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from redsim.core.pos import Pos
from redsim.editor.document import Document, Pulse
from redsim.ui import theme

EDIT_DELAY_MS = 450  # spin box changes are applied after this pause (one re-run)


class SequencePanel(QWidget):
    edit_requested = Signal(int, int, int, int)  # index, tick, strength, ticks
    delete_requested = Signal(int)  # index
    pulse_selected = Signal(object, int)  # Pos, tick

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        intro = QLabel(
            f"<small style='color:{theme.TEXT_DIM}'>ANIMATE mode (K, or hold Tab): scrub to "
            "a tick and click a block to power its position from then on for the ticks "
            "below; right click removes the pulse there. The position is powered, "
            "whatever block is there (pistons may move away).</small>"
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)
        form = QFormLayout()
        self.strength = QSpinBox()
        self.strength.setRange(1, 15)
        self.strength.setValue(15)
        self.strength.setToolTip("Signal strength of new pulses")
        self.duration = QSpinBox()
        self.duration.setRange(1, 10000)
        self.duration.setValue(2)
        self.duration.setSuffix(" ticks")
        self.duration.setToolTip("How long new pulses stay on")
        form.addRow("New pulses: strength", self.strength)
        form.addRow("Duration", self.duration)
        layout.addLayout(form)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Tick", "Position", "Strength", "Ticks", ""])
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.cellClicked.connect(self._clicked)
        layout.addWidget(self.table, 1)
        self._shown: list[Pulse] = []
        self._pending: dict[int, tuple[int, int, int]] = {}
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(EDIT_DELAY_MS)
        self._timer.timeout.connect(self._apply_pending)

    def show_document(self, document: Document) -> None:
        pulses = document.pulses()
        if pulses == self._shown:
            return
        self._shown = pulses
        self.table.setRowCount(len(pulses))
        for row, pulse in enumerate(pulses):
            boxes = []
            for column, (value, low, high) in (
                (0, (pulse.tick, 1, 1_000_000)),
                (2, (pulse.strength, 1, 15)),
                (3, (pulse.ticks, 1, 10_000)),
            ):
                box = QSpinBox()
                box.setRange(low, high)
                box.setValue(value)
                box.setFrame(False)
                self.table.setCellWidget(row, column, box)
                boxes.append(box)
            for box in boxes:
                box.valueChanged.connect(
                    lambda _=0, p=pulse, b=boxes: self._changed(p, b[0], b[1], b[2])
                )
            where = QTableWidgetItem(" ".join(str(v) for v in pulse.pos))
            where.setToolTip("Click: show it in the view and go to the pulse's tick")
            self.table.setItem(row, 1, where)
            remove = QPushButton("×")
            remove.setToolTip("Remove this pulse")
            remove.setFixedWidth(26)
            remove.clicked.connect(lambda _=False, i=pulse.index: self.delete_requested.emit(i))
            holder = QWidget()
            row_layout = QHBoxLayout(holder)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.addWidget(remove)
            self.table.setCellWidget(row, 4, holder)
        if not pulses:
            self.table.setRowCount(1)
            empty = QTableWidgetItem("No pulses yet.")
            empty.setForeground(Qt.GlobalColor.gray)
            self.table.setItem(0, 1, empty)

    def _changed(self, pulse: Pulse, tick: QSpinBox, strength: QSpinBox, ticks: QSpinBox) -> None:
        self._pending[pulse.index] = (tick.value(), strength.value(), ticks.value())
        self._timer.start()

    def _apply_pending(self) -> None:
        pending, self._pending = self._pending, {}
        for index, (tick, strength, ticks) in pending.items():
            self.edit_requested.emit(index, tick, strength, ticks)

    def _clicked(self, row: int, column: int) -> None:
        if 0 <= row < len(self._shown):
            pulse = self._shown[row]
            self.pulse_selected.emit(pulse.pos, pulse.tick)

    def pulse_at(self, pulses: list[Pulse], pos: Pos, tick: int) -> list[Pulse]:
        """The pulses at ``pos`` running at ``tick`` (or starting there)."""
        return [p for p in pulses if p.pos == pos and p.tick <= tick < p.tick + max(1, p.ticks)]
