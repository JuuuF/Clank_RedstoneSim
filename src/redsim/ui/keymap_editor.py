"""Settings → Keymap…: every action with its bindings, editable in the program (round 8:
no more editing the JSON file).

Bindings of a row are comma-separated text ("Ctrl+Z, Ctrl+Shift+Z"). "Record" captures
one key press (with its modifiers) and adds it; mouse bindings use the same text as the
file ("Shift+Wheel", "Ctrl+Right Click"). Conflicts are marked live; Save writes only the
changes from the defaults into the keymap file.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QEvent, QObject, Qt, Signal
from PySide6.QtGui import QColor, QKeyEvent
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from redsim.ui import theme
from redsim.ui.keymap import (
    ACTIONS,
    HOTKEY_GROUPS,
    MOUSE,
    SPECS,
    Keymap,
    binding_text,
    default_path,
    platform_defaults,
)

#: Columns of the table.
SECTION, ACTION, BINDINGS = range(3)


def split_bindings(text: str) -> list[str]:
    return [part.strip() for part in text.split(",") if part.strip()]


class KeymapEditor(QDialog):
    """Edit the keymap; ``applied`` carries the new keymap after Save."""

    applied = Signal(object)  # Keymap

    def __init__(self, keymap: Keymap, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Keymap")
        self.resize(760, 620)
        self._recording: int | None = None  # the row a key press is being captured for
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 12)
        layout.setSpacing(10)
        top = QHBoxLayout()
        self.filter = QLineEdit()
        self.filter.setPlaceholderText("Filter actions or keys, e.g. rotate, Wheel or Ctrl")
        self.filter.setClearButtonEnabled(True)
        self.filter.textChanged.connect(self._apply_filter)
        top.addWidget(self.filter, 1)
        layout.addLayout(top)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Section", "Action", "Bindings (comma-separated)"])
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(SECTION, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(ACTION, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(BINDINGS, QHeaderView.ResizeMode.Stretch)
        self.table.itemChanged.connect(lambda _item: self._check())
        self.table.installEventFilter(self)
        layout.addWidget(self.table, 1)
        self.status = QLabel("")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        buttons = QHBoxLayout()
        self.record = QPushButton("Record key")
        self.record.setToolTip("Press a key (with modifiers) to add it to the selected action")
        self.record.clicked.connect(self._start_recording)
        buttons.addWidget(self.record)
        reset_row = QPushButton("Reset action")
        reset_row.setToolTip("The selected action's default bindings")
        reset_row.clicked.connect(self._reset_row)
        buttons.addWidget(reset_row)
        reset_all = QPushButton("Reset all")
        reset_all.clicked.connect(self._reset_all)
        buttons.addWidget(reset_all)
        buttons.addStretch(1)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(cancel)
        self.save = QPushButton("Save")
        self.save.setDefault(True)
        self.save.clicked.connect(self._save)
        buttons.addWidget(self.save)
        layout.addLayout(buttons)
        self._fill(keymap)

    # ------------------------------------------------------------------ table
    def _fill(self, keymap: Keymap) -> None:
        section_of = {a: title for title, _, actions in HOTKEY_GROUPS for a in actions}
        self.table.blockSignals(True)
        self.table.setRowCount(len(ACTIONS))
        for row, spec in enumerate(ACTIONS):
            section = QTableWidgetItem(section_of.get(spec.id, "Other"))
            action = QTableWidgetItem(spec.title)
            for item in (section, action):
                item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            section.setForeground(QColor(theme.TEXT_DIM))
            action.setData(Qt.ItemDataRole.UserRole, spec.id)
            action.setToolTip(spec.id)
            bindings = QTableWidgetItem(", ".join(keymap.bindings(spec.id)))
            self.table.setItem(row, SECTION, section)
            self.table.setItem(row, ACTION, action)
            self.table.setItem(row, BINDINGS, bindings)
        self.table.blockSignals(False)
        self._check()

    def _cell(self, row: int, column: int) -> QTableWidgetItem:
        item = self.table.item(row, column)
        assert item is not None
        return item

    def action_at(self, row: int) -> str:
        return str(self._cell(row, ACTION).data(Qt.ItemDataRole.UserRole))

    def row_of(self, action: str) -> int:
        return next(r for r in range(self.table.rowCount()) if self.action_at(r) == action)

    def bindings_at(self, row: int) -> list[str]:
        return split_bindings(self._cell(row, BINDINGS).text())

    def set_bindings(self, action: str, bindings: list[str]) -> None:
        self._cell(self.row_of(action), BINDINGS).setText(", ".join(bindings))

    def edited(self) -> dict[str, list[str]]:
        """What the table says, as changes from the defaults."""
        result = {}
        for row in range(self.table.rowCount()):
            action, bindings = self.action_at(row), self.bindings_at(row)
            if tuple(bindings) != platform_defaults(action):
                result[action] = bindings
        return result

    def _apply_filter(self, text: str) -> None:
        needle = text.strip().lower()
        for row in range(self.table.rowCount()):
            haystack = (
                " ".join(self._cell(row, column).text().lower() for column in range(3))
                + " "
                + self.action_at(row)
            )
            self.table.setRowHidden(row, bool(needle) and needle not in haystack)

    # ------------------------------------------------------------------ checking
    def _check(self) -> Keymap:
        """Mark changed rows and report conflicts or invalid bindings."""
        keymap = Keymap(self.edited())
        problems = [w for w in keymap.warnings if "now belongs to" not in w]
        self.table.blockSignals(True)
        for row in range(self.table.rowCount()):
            action = self.action_at(row)
            changed = tuple(self.bindings_at(row)) != platform_defaults(action)
            bad = any(action in w or SPECS[action].title in w for w in problems)
            item = self._cell(row, BINDINGS)
            item.setForeground(
                QColor(theme.ACCENT if bad else theme.GOLD if changed else theme.TEXT)
            )
        self.table.blockSignals(False)
        if problems:
            self.status.setText(
                f"<span style='color:{theme.ACCENT}'>" + "<br>".join(problems) + "</span>"
            )
        else:
            count = len(self.edited())
            self.status.setText(
                f"<span style='color:{theme.TEXT_DIM}'>{count} change{'s' if count != 1 else ''} "
                f"from the defaults (gold). Saved to {default_path()}.</span>"
            )
        return keymap

    # ------------------------------------------------------------------ buttons
    def _selected_row(self) -> int | None:
        rows = self.table.selectionModel().selectedRows()
        return rows[0].row() if rows else None

    def _start_recording(self) -> None:
        row = self._selected_row()
        if row is None:
            self.status.setText("Select an action first.")
            return
        if SPECS[self.action_at(row)].kind == MOUSE:
            self.status.setText(
                "Mouse bindings are typed: e.g. Shift+Wheel, Ctrl+Right Click, Middle Drag."
            )
            self.table.editItem(self._cell(row, BINDINGS))
            return
        self._recording = row
        self.record.setText("Press a key…")
        self.table.setFocus()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if (
            self._recording is not None
            and watched is self.table
            and event.type() == QEvent.Type.KeyPress
            and isinstance(event, QKeyEvent)
        ):
            self.record_key(event.key(), _modifier_names(event.modifiers()), event.text())
            return True
        return super().eventFilter(watched, event)

    def record_key(self, key: int, modifiers: list[str], text: str = "") -> None:
        """A key press while recording: add it to the row (Esc cancels)."""
        if key == Qt.Key.Key_Escape and not modifiers:
            self._recording = None
            self.record.setText("Record key")
            return
        binding = binding_text(key, modifiers, text)
        if binding is None or self._recording is None:
            return  # a modifier alone: wait for the key
        row = self._recording
        bindings = self.bindings_at(row)
        if binding not in bindings:
            self.set_bindings(self.action_at(row), [*bindings, binding])
        self._recording = None
        self.record.setText("Record key")

    def _reset_row(self) -> None:
        row = self._selected_row()
        if row is not None:
            action = self.action_at(row)
            self.set_bindings(action, list(platform_defaults(action)))

    def _reset_all(self) -> None:
        self._fill(Keymap())

    def _save(self) -> None:
        keymap = self._check()
        problems = [w for w in keymap.warnings if "now belongs to" not in w]
        if problems:
            self.status.setText(
                f"<span style='color:{theme.ACCENT}'>Fix the marked bindings first: "
                + "<br>".join(problems)
                + "</span>"
            )
            return
        self.applied.emit(Keymap.save_changes(self.edited()))
        self.accept()


def _modifier_names(modifiers: Any) -> list[str]:
    names = []
    for flag, name in (
        (Qt.KeyboardModifier.ControlModifier, "Ctrl"),
        (Qt.KeyboardModifier.AltModifier, "Alt"),
        (Qt.KeyboardModifier.ShiftModifier, "Shift"),
        (Qt.KeyboardModifier.MetaModifier, "Meta"),
    ):
        if modifiers & flag:
            names.append(name)
    return names
