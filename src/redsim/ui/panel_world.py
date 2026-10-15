"""The World tab: what the command line (``redsim-cli``, doc/cli.md) keeps in a world
besides its blocks, shown in the editor: the notes, the labels (names of positions) and
the targets (acceptance tests), with a Check button that runs the targets exactly like
``redsim-cli WORLD check``. Clicking or hovering a label or an expectation shows its block
in the view. Editing them is done with the command line; the editor keeps them when it
saves."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from redsim.core.pos import Pos
from redsim.editor.document import Document
from redsim.ui import theme
from redsim.ui.names import block_name

PASS = QColor("#7ed321")
FAIL = QColor("#f05a4a")


class WorldPanel(QWidget):
    highlight_requested = Signal(object)  # Pos
    position_hovered = Signal(object)  # Pos | None

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        self.notes = QLabel()
        self.notes.setWordWrap(True)
        self.notes.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.notes)
        layout.addWidget(_heading("Labels"))
        self.labels = QTableWidget(0, 3)
        self.labels.setHorizontalHeaderLabels(["Name", "Position", "Block / note"])
        self.labels.verticalHeader().setVisible(False)
        self.labels.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.labels.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.labels.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.labels.setMouseTracking(True)
        self.labels.cellClicked.connect(self._label_clicked)
        self.labels.cellEntered.connect(self._label_hovered)
        self.labels.setToolTip("Labels name positions (@NAME in redsim-cli). Click: show the block")
        layout.addWidget(self.labels, 1)
        row = QHBoxLayout()
        row.addWidget(_heading("Targets"))
        row.addStretch(1)
        self.check_button = QPushButton("Check")
        self.check_button.setToolTip(
            "Run every target from the build in a copy of the world (redsim-cli check);\n"
            "the world and its timeline are not changed"
        )
        self.check_button.clicked.connect(self.check)
        row.addWidget(self.check_button)
        layout.addLayout(row)
        self.targets = QTreeWidget()
        self.targets.setHeaderHidden(True)
        self.targets.setMouseTracking(True)
        self.targets.itemClicked.connect(self._target_clicked)
        self.targets.itemEntered.connect(self._target_hovered)
        layout.addWidget(self.targets, 2)
        self.summary = QLabel()
        layout.addWidget(self.summary)
        self._document: Document | None = None
        self._shown: tuple[Any, ...] = ()
        #: Results of the last check: (target, case) → CaseResult.
        self._results: dict[tuple[str, str], Any] = {}

    # ------------------------------------------------------------------ showing
    def show_document(self, document: Document) -> None:
        """Refresh the lists (cheap; only when something changed)."""
        if document is not self._document:
            self._results = {}
        self._document = document
        key = (
            id(document),
            tuple(document.notes),
            tuple((n, lab.pos, lab.note) for n, lab in sorted(document.labels.items())),
            repr(document.targets),
            document.revision,
        )
        if key == self._shown:
            return
        self._shown = key
        if document.notes:
            self.notes.setText("<br>".join(f"• {_escape(n)}" for n in document.notes))
        else:
            self.notes.setText(
                f"<span style='color:{theme.TEXT_DIM}'>No notes. Notes, labels and targets "
                "are written with redsim-cli (doc/cli.md).</span>"
            )
        self.labels.setRowCount(0)
        for name, label in sorted(document.labels.items()):
            row = self.labels.rowCount()
            self.labels.insertRow(row)
            state = document.state_at(label.pos)
            what = "empty" if state.is_air else block_name(state.block.id)
            items = [f"@{name}", " ".join(str(v) for v in label.pos),
                     what + (f" — {label.note}" if label.note else "")]  # fmt: skip
            for column, text in enumerate(items):
                item = QTableWidgetItem(text)
                item.setData(Qt.ItemDataRole.UserRole, label.pos)
                self.labels.setItem(row, column, item)
        self.labels.resizeColumnsToContents()
        self._fill_targets(document)

    def _fill_targets(self, document: Document) -> None:
        self.targets.clear()
        passed = failed = 0
        for target in document.targets:
            top = QTreeWidgetItem([f"{target['name']}: {target.get('description', '')}"])
            self.targets.addTopLevelItem(top)
            for case in target["cases"]:
                result = self._results.get((target["name"], case["name"]))
                status = "" if result is None else ("PASS  " if result.passed else "FAIL  ")
                title = target["name"] if case["name"] == "main" else f"[{case['name']}]"
                child = QTreeWidgetItem([f"{status}{title}"])
                if result is not None:
                    child.setForeground(0, PASS if result.passed else FAIL)
                    passed += result.passed
                    failed += not result.passed
                top.addChild(child)
                for line in case["lines"]:
                    child.addChild(QTreeWidgetItem([line]))
                if result is not None:
                    for e in result.results:
                        if e.passed:
                            continue
                        seen = ", ".join(f"tick {t}: {v}" for t, v in list(e.observed.items())[:4])
                        item = QTreeWidgetItem([f"failed: {e.expectation.text}  (saw {seen})"])
                        item.setForeground(0, FAIL)
                        item.setData(0, Qt.ItemDataRole.UserRole, e.expectation.pos)
                        child.addChild(item)
                    if result.error:
                        child.addChild(QTreeWidgetItem([result.error]))
                child.setExpanded(result is not None and not result.passed)
            top.setExpanded(True)
        if not document.targets:
            self.summary.setText(
                f"<span style='color:{theme.TEXT_DIM}'>No targets yet: "
                "redsim-cli WORLD target new NAME …</span>"
            )
        elif passed or failed:
            self.summary.setText(f"{passed} passed, {failed} failed")
        else:
            self.summary.setText("Not checked yet")
        self.check_button.setEnabled(bool(document.targets))

    # ------------------------------------------------------------------ actions
    def check(self) -> None:
        """Run every target (``redsim.cli.targets.run_case``) and show the results."""
        from redsim.cli import commands  # noqa: F401  (registers the commands targets run)
        from redsim.cli.targets import run_case

        document = self._document
        if document is None:
            return
        document.flush()
        self._results = {}
        for target in document.targets:
            for case in target["cases"]:
                self._results[(target["name"], case["name"])] = run_case(
                    document, target["name"], case
                )
        self._shown = ()
        self.show_document(document)

    def _label_clicked(self, row: int, column: int) -> None:
        item = self.labels.item(row, column)
        if item is not None:
            self.highlight_requested.emit(item.data(Qt.ItemDataRole.UserRole))

    def _label_hovered(self, row: int, column: int) -> None:
        item = self.labels.item(row, column)
        self.position_hovered.emit(item.data(Qt.ItemDataRole.UserRole) if item else None)

    def _target_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        pos = self._position_of(item)
        if pos is not None:
            self.highlight_requested.emit(pos)

    def _target_hovered(self, item: QTreeWidgetItem, column: int) -> None:
        self.position_hovered.emit(self._position_of(item))

    def _position_of(self, item: QTreeWidgetItem) -> Pos | None:
        pos = item.data(0, Qt.ItemDataRole.UserRole)
        if pos is not None:
            return tuple(pos)
        text = item.text(0)
        if self._document is not None:
            for word in text.split():
                name = word.lstrip("@")
                if word.startswith("@") and name in self._document.labels:
                    return self._document.labels[name].pos
        return None


def _heading(text: str) -> QLabel:
    label = QLabel(f"<b>{text}</b>")
    return label


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
