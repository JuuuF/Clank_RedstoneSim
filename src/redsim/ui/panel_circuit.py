"""The Circuit tab: sections (colored labels), groups with ports and the prefab library."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QByteArray, QMimeData, QObject, QSize, Qt, Signal
from PySide6.QtGui import QColor, QDrag, QIcon
from PySide6.QtWidgets import (
    QAbstractItemView,
    QColorDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from redsim.editor.document import Document
from redsim.ui import theme
from redsim.ui.icons import prefab_pixmap
from redsim.ui.names import block_name
from redsim.ui.panel_widgets import _placeholder, _swatch


class SectionsPanel(QWidget):
    changed = Signal()

    def __init__(self, document: Document) -> None:
        super().__init__()
        self.document = document
        layout = QVBoxLayout(self)
        self.list = QListWidget()
        layout.addWidget(self.list)
        row = QHBoxLayout()
        add = QPushButton("Add…")
        add.clicked.connect(self._add)
        row.addWidget(add)
        color = QPushButton("Color…")
        color.clicked.connect(self._recolor)
        row.addWidget(color)
        remove = QPushButton("Remove")
        remove.clicked.connect(self._remove)
        row.addWidget(remove)
        layout.addLayout(row)
        hint = QLabel("Sections color the view only; they never affect the simulation.")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.refresh()

    def set_document(self, document: Document) -> None:
        self.document = document
        self.refresh()

    def refresh(self) -> None:
        """Rebuild the list (a color swatch, the name, the size), keeping the selection."""
        chosen = self._selected()
        self.list.clear()
        for name, section in self.document.sections.sections.items():
            item = QListWidgetItem(f"{name}  ({len(section.positions)} blocks)")
            item.setData(Qt.ItemDataRole.UserRole, name)
            item.setIcon(_swatch(section.color))
            self.list.addItem(item)
            if name == chosen:
                self.list.setCurrentItem(item)

    def _selected(self) -> str | None:
        item = self.list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _add(self) -> None:
        name, ok = QInputDialog.getText(self, "New section", "Name:")
        if ok and name:
            color = QColorDialog.getColor(QColor("#ff5555"), self, "Section color")
            if color.isValid():
                self.document.sections.add(name, color.name())
                self.changed.emit()
                self.refresh()

    def _recolor(self) -> None:
        name = self._selected()
        if name:
            section = self.document.sections.sections[name]
            color = QColorDialog.getColor(QColor(section.color), self, "Section color")
            if color.isValid():
                section.color = color.name()
                self.changed.emit()
                self.refresh()

    def _remove(self) -> None:
        name = self._selected()
        if name:
            self.document.sections.remove(name)
            self.changed.emit()
            self.refresh()


#: Drag and drop of a prefab from the list into the 3D view: the mime type and the size of
#: the previews in the list.
PREFAB_MIME = "application/x-redsim-prefab"
PREVIEW_SIZE = 56


class PrefabList(QListWidget):
    """The prefab library: a preview of each prefab; drag one into the 3D view to place
    it (owner, 2026-10-14)."""

    def __init__(self) -> None:
        super().__init__()
        self.setIconSize(QSize(PREVIEW_SIZE, PREVIEW_SIZE))
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)
        self.setSpacing(2)

    def startDrag(self, supported: Qt.DropAction) -> None:  # noqa: N802 - Qt override
        item = self.currentItem()
        if item is None or not item.flags() & Qt.ItemFlag.ItemIsEnabled:
            return
        data = QMimeData()
        data.setData(PREFAB_MIME, QByteArray(item.text().encode()))
        drag = QDrag(self)
        drag.setMimeData(data)
        icon = item.icon()
        if not icon.isNull():
            drag.setPixmap(icon.pixmap(PREVIEW_SIZE, PREVIEW_SIZE))
        drag.exec(Qt.DropAction.CopyAction)


class ContraptionsPanel(QObject):
    """Prefab library and groups with exposed ports: two pages (``prefab_page``,
    ``group_page``) that the window shows as tabs next to the sections."""

    save_prefab = Signal()
    load_prefab = Signal(str)
    delete_prefab = Signal(str)
    import_prefab = Signal()
    import_schematic = Signal()
    export_prefab = Signal(str)
    create_group = Signal()
    add_port = Signal(str)
    toggle_port = Signal(str, int)
    delete_group = Signal(str)
    go_to_group = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.prefab_page = prefab_page = QWidget()
        prefab_layout = QVBoxLayout(prefab_page)
        self.prefab_list = PrefabList()
        self.prefab_list.setToolTip(
            "Drag a prefab into the view to place it, or double-click it: it follows the "
            "cursor and a click places it as a group"
        )
        self.prefab_list.itemDoubleClicked.connect(lambda _: self._with_prefab(self.load_prefab))
        prefab_layout.addWidget(self.prefab_list)
        row = QHBoxLayout()
        for text, slot in (
            ("Save selection…", self.save_prefab.emit),
            ("Paste", lambda: self._with_prefab(self.load_prefab)),
            ("Delete", lambda: self._with_prefab(self.delete_prefab)),
        ):
            button = QPushButton(text)
            button.clicked.connect(slot)
            row.addWidget(button)
        prefab_layout.addLayout(row)
        row = QHBoxLayout()
        for text, slot, tip in (
            (
                "Import schematic…",
                self.import_schematic.emit,
                "A schematic from the library (or Browse… for a new one) becomes a prefab",
            ),
            ("Import file…", self.import_prefab.emit, "A prefab file (.json) or a schematic"),
            ("Export…", lambda: self._with_prefab(self.export_prefab), "As .json or a schematic"),
        ):
            button = QPushButton(text)
            button.setToolTip(tip)
            button.clicked.connect(slot)
            row.addWidget(button)
        prefab_layout.addLayout(row)
        hint = QLabel(
            "Select a box in SELECT mode (V), then Save selection… to keep it here. "
            "Copy and paste work like /clone; Del clears the box (like /fill air)."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {theme.TEXT_DIM};")
        prefab_layout.addWidget(hint)

        self.group_page = group_page = QWidget()
        group_layout = QVBoxLayout(group_page)
        self.group_list = QListWidget()
        self.group_list.setToolTip("Double-click a group to go there")
        self.group_list.itemDoubleClicked.connect(lambda _: self._with_group(self.go_to_group))
        group_layout.addWidget(self.group_list)
        row = QHBoxLayout()
        create = QPushButton("Group selection…")
        create.clicked.connect(self.create_group.emit)
        row.addWidget(create)
        port = QPushButton("Add port…")
        port.setToolTip("Expose the inspected block (Ctrl+click) as an input or output port")
        port.clicked.connect(lambda: self._with_group(self.add_port))
        row.addWidget(port)
        remove = QPushButton("Delete")
        remove.clicked.connect(lambda: self._with_group(self.delete_group))
        row.addWidget(remove)
        group_layout.addLayout(row)
        self.ports = QListWidget()
        self.ports.setToolTip("Double-click an input port to use (toggle) its block")
        self.ports.itemDoubleClicked.connect(self._port_clicked)
        group_layout.addWidget(self.ports)
        note = QLabel(
            "Groups only name parts of a circuit and expose ports; the internals still "
            "simulate block by block with unchanged timing."
        )
        note.setWordWrap(True)
        note.setStyleSheet(f"color: {theme.TEXT_DIM};")
        group_layout.addWidget(note)
        self.group_list.currentTextChanged.connect(lambda _: self._refresh_ports())
        self._document: Document | None = None

    def _with_prefab(self, signal: Any) -> None:
        item = self.prefab_list.currentItem()
        if item is not None and item.flags() & Qt.ItemFlag.ItemIsEnabled:  # not a placeholder
            signal.emit(item.text())

    def _with_group(self, signal: Any) -> None:
        item = self.group_list.currentItem()
        if item is not None and item.flags() & Qt.ItemFlag.ItemIsEnabled:
            signal.emit(item.text())

    def _port_clicked(self, item: QListWidgetItem) -> None:
        group = self.group_list.currentItem()
        if group is not None:
            self.toggle_port.emit(group.text(), self.ports.row(item))

    def show_document(self, document: Document) -> None:
        from redsim.editor.groups import port_reading

        self._document = document
        current_prefab = self.prefab_list.currentItem()
        selected = current_prefab.text() if current_prefab else None
        self.prefab_list.clear()
        for name in sorted(document.prefabs):
            item = QListWidgetItem(QIcon(prefab_pixmap(document.prefabs[name], PREVIEW_SIZE)), name)
            sx, sy, sz = document.prefabs[name].size
            item.setToolTip(f"{name}: {sx}×{sy}×{sz} · drag it into the view to place it")
            self.prefab_list.addItem(item)
            if name == selected:
                self.prefab_list.setCurrentRow(self.prefab_list.count() - 1)
        if not document.prefabs:
            empty = QListWidgetItem("No prefabs yet: select a box, then Save selection…")
            self.prefab_list.addItem(_placeholder(empty))
        current_group = self.group_list.currentItem()
        group_name = current_group.text() if current_group else None
        self.group_list.blockSignals(True)
        self.group_list.clear()
        for name in sorted(document.groups.groups):
            self.group_list.addItem(name)
            if name == group_name:
                self.group_list.setCurrentRow(self.group_list.count() - 1)
        if not document.groups.groups:
            empty = QListWidgetItem("No groups yet: select a box, then Group selection…")
            self.group_list.addItem(_placeholder(empty))
        self.group_list.blockSignals(False)
        self._refresh_ports(port_reading)

    def _refresh_ports(self, reading: Any = None) -> None:
        from redsim.editor.groups import port_reading

        reading = reading or port_reading
        self.ports.clear()
        item = self.group_list.currentItem()
        if self._document is None or item is None:
            return
        group = self._document.groups.groups.get(item.text())
        if group is None:
            return
        for port in group.ports:
            arrow = "→ in " if port.role == "input" else "out →"
            value = reading(self._document.level, port, block_name)
            x, y, z = port.pos
            self.ports.addItem(f"{arrow} {port.name} ({x} {y} {z}): {value}")
