"""The "Select Schematic" screen: the schematic library (``io/schematic_library.py``) like
the game's world list. Each row shows a picture of the schematic, its name, its size and
block count, author and description, and where it came from. Browse… imports any other
file into the library; Open folder shows the library in the file manager; Delete removes
a library schematic.

Used by Region → Import schematic… (the chosen schematic follows the cursor to be pasted)
and the Prefabs panel's Import schematic… (it becomes a prefab).
"""

from __future__ import annotations

import time
from pathlib import Path

from PySide6.QtCore import QEvent, QSize, Qt, QUrl
from PySide6.QtGui import QDesktopServices, QPaintEvent, QPalette, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from redsim.io import schematic_library as library
from redsim.io.schematics import FILE_FILTER, read_schematic
from redsim.ui import game_gui, theme
from redsim.ui.game_gui import GameButton
from redsim.ui.icons import prefab_pixmap
from redsim.ui.preferences import config_dir

ICON = 72


def library_folder() -> Path:
    """The schematic library, next to the preferences (``schematics/``)."""
    return config_dir() / "schematics"


def preview(entry: library.SchematicEntry) -> QPixmap:
    """The schematic's picture: saved beside a library file once made."""
    if entry.preview.is_file():
        pixmap = QPixmap(str(entry.preview))
        if not pixmap.isNull():
            return pixmap
    try:
        pixmap = prefab_pixmap(read_schematic(entry.path), ICON * 2)
    except (OSError, ValueError, KeyError, IndexError, EOFError):
        return QPixmap()
    if entry.in_library:
        pixmap.save(str(entry.preview))
    return pixmap


class _Row(QWidget):
    def __init__(self, entry: library.SchematicEntry) -> None:
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(10)
        icon = QLabel()
        icon.setFixedSize(ICON, ICON)
        pixmap = preview(entry)
        if not pixmap.isNull():
            icon.setPixmap(
                pixmap.scaled(
                    ICON,
                    ICON,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )  # fmt: skip
            )
        layout.addWidget(icon)
        text = QVBoxLayout()
        text.setSpacing(2)
        name = QLabel()
        font = theme.PixelFont.load()
        if font is not None:
            name.setPixmap(font.pixmap(entry.name, theme.TEXT, 2))
        else:
            name.setText(f"<b>{entry.name}</b>")
        text.addWidget(name)
        sx, sy, sz = entry.size
        by = f" · by {entry.author}" if entry.author else ""
        lines = [f"{sx}×{sy}×{sz} · {entry.blocks} blocks{by}"]
        if entry.description:
            lines.append(entry.description)
        when = time.strftime("%d.%m.%y", time.localtime(entry.imported))
        where = "imported" if entry.in_library else "Minecraft folder"
        lines.append(f"{entry.path.name} · {where} {when}")
        for line in lines:
            label = QLabel(line)
            label.setStyleSheet(f"color: {theme.TEXT_DIM};")
            text.addWidget(label)
        layout.addLayout(text, 1)


class SchematicPicker(QDialog):
    """Choose a schematic: ``chosen`` is its path (in the library) after ``exec``."""

    def __init__(self, parent: QWidget | None = None, action: str = "Import") -> None:
        super().__init__(parent)
        self.setWindowTitle("Select Schematic")
        self.resize(640, 580)
        self.folder = library_folder()
        self.chosen: Path | None = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)
        title = QLabel()
        font = theme.PixelFont.load()
        if font is not None:
            title.setPixmap(font.pixmap("Select Schematic", theme.TEXT, 3))
        else:
            title.setText("<b>Select Schematic</b>")
        title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(title)
        self.search = QLineEdit()
        self.search.setPlaceholderText(" Type to search, ↑/↓ to choose, Enter to pick")
        self.search.textChanged.connect(self._filter)
        self.search.returnPressed.connect(self._pick)
        self.search.installEventFilter(self)
        layout.addWidget(self.search)
        self.list = QListWidget()
        self.list.setIconSize(QSize(ICON, ICON))
        list_dirt = game_gui.dirt_brush(game_gui.LIST_SHADE)
        if list_dirt is not None:
            self.search.setStyleSheet(game_gui.TEXT_FIELD_STYLE)
            self.list.setStyleSheet(
                "QListWidget { background: transparent; border: none; }"
                "QListWidget::item { background: transparent; }"
                "QListWidget::item:selected { background: rgba(0, 0, 0, 160);"
                " border: 2px solid #ffffff; }"
            )
            palette = self.list.viewport().palette()
            palette.setBrush(QPalette.ColorRole.Base, list_dirt)
            self.list.viewport().setPalette(palette)
            self.list.viewport().setAutoFillBackground(True)
        self.list.itemDoubleClicked.connect(lambda _: self._pick())
        self.list.currentItemChanged.connect(lambda *_: self._update_buttons())
        layout.addWidget(self.list, 1)
        self.note = QLabel()
        self.note.setStyleSheet(f"color: {theme.TEXT_DIM};")
        self.note.setWordWrap(True)
        layout.addWidget(self.note)
        buttons = QHBoxLayout()
        self.pick_button = GameButton(action)
        self.pick_button.setDefault(True)
        self.pick_button.clicked.connect(self._pick)
        browse = GameButton("Browse…")
        browse.setToolTip("Import another schematic file into the library")
        browse.clicked.connect(self._browse)
        folder = GameButton("Open folder")
        folder.setToolTip(f"Show the library folder ({self.folder})")
        folder.clicked.connect(self._open_folder)
        self.delete_button = GameButton("Delete")
        self.delete_button.clicked.connect(self._delete)
        cancel = GameButton("Cancel")
        cancel.clicked.connect(self.reject)
        for button, stretch in (
            (self.pick_button, 2), (browse, 1), (folder, 1), (self.delete_button, 1), (cancel, 1),
        ):  # fmt: skip
            buttons.addWidget(button, stretch)
        layout.addLayout(buttons)
        self._fill()
        self.search.setFocus()

    def paintEvent(self, event: QPaintEvent) -> None:
        game_gui.paint_dirt(self)

    def eventFilter(self, watched: object, event: QEvent) -> bool:
        if watched is self.search and event.type() == QEvent.Type.KeyPress:
            key = event.key()  # type: ignore[attr-defined]
            if key in (Qt.Key.Key_Up, Qt.Key.Key_Down):
                rows = [r for r in range(self.list.count()) if not self.list.item(r).isHidden()]
                if rows:
                    current = self.list.currentRow()
                    at = rows.index(current) if current in rows else 0
                    at = max(0, min(len(rows) - 1, at + (1 if key == Qt.Key.Key_Down else -1)))
                    self.list.setCurrentRow(rows[at])
                return True
        return super().eventFilter(watched, event)  # type: ignore[arg-type]

    def _fill(self, select: Path | None = None) -> None:
        self.list.clear()
        others = library.minecraft_schematic_folders()
        for entry in library.entries(self.folder, others):
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, entry)
            item.setSizeHint(QSize(0, ICON + 12))
            self.list.addItem(item)
            row = _Row(entry)
            row.setToolTip(f"{entry.path.resolve()}\nfrom {entry.source}")
            self.list.setItemWidget(item, row)
            if select is not None and entry.path == select:
                self.list.setCurrentItem(item)
        if self.list.currentItem() is None and self.list.count():
            self.list.setCurrentRow(0)
        found = ", ".join(str(f) for f in others)
        self.note.setText(
            f"Library: {self.folder}"
            + (f" · also listed: {found}" if found else "")
            + ("" if self.list.count() else " · empty: Browse… imports a schematic")
        )
        self._filter(self.search.text())

    def _filter(self, text: str) -> None:
        needle = text.strip().lower()
        for row in range(self.list.count()):
            item = self.list.item(row)
            entry: library.SchematicEntry = item.data(Qt.ItemDataRole.UserRole)
            hay = f"{entry.name} {entry.path.name} {entry.author} {entry.description}".lower()
            item.setHidden(bool(needle) and needle not in hay)
        self._update_buttons()

    def _entry(self) -> library.SchematicEntry | None:
        item = self.list.currentItem()
        if item is None or item.isHidden():
            return None
        entry: library.SchematicEntry = item.data(Qt.ItemDataRole.UserRole)
        return entry

    def _update_buttons(self) -> None:
        entry = self._entry()
        self.pick_button.setEnabled(entry is not None)
        self.delete_button.setEnabled(entry is not None and entry.in_library)

    def _pick(self) -> None:
        entry = self._entry()
        if entry is None:
            return
        try:  # a Minecraft folder's file: copied into the library first
            self.chosen = entry.path if entry.in_library else library.add(self.folder, entry.path)
        except (OSError, ValueError, KeyError, IndexError, EOFError) as exc:
            QMessageBox.critical(self, "Cannot read the schematic", f"{entry.path.name}: {exc}")
            return
        self.accept()

    def _browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Import schematic", "", FILE_FILTER)
        if not path:
            return
        try:
            added = library.add(self.folder, Path(path))
        except (OSError, ValueError, KeyError, IndexError, EOFError) as exc:
            QMessageBox.critical(self, "Cannot read the schematic", f"{Path(path).name}: {exc}")
            return
        self._fill(select=added)

    def _open_folder(self) -> None:
        self.folder.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.folder)))

    def _delete(self) -> None:
        entry = self._entry()
        if entry is None or not entry.in_library:
            return
        answer = QMessageBox.question(
            self, "Delete schematic", f"Delete “{entry.name}” from the library?"
        )
        if answer == QMessageBox.StandardButton.Yes:
            library.remove(entry.path)
            self._fill()
