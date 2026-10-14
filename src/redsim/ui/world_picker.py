"""The "Select World" screen, like the game's: Minecraft saves (from the game's saves
folders), simulation worlds (recently used ``.redsim.json`` files and the examples), and
any other file or folder through Browse…. Each row shows the world's icon (a save's
``icon.png``; for simulation worlds a thumbnail of the view, made when saving), its name,
and when it was last played or saved.

Minecraft saves are listed from their ``level.dat`` (name, last played, version) without
reading any chunks, so the screen opens at once.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QEvent, QSize, Qt
from PySide6.QtGui import QImage, QPaintEvent, QPalette, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from redsim.ui import game_gui, theme
from redsim.ui.game_gui import GameButton, GameTabs
from redsim.ui.icons import block_pixmap
from redsim.ui.preferences import config_dir

ICON = 64
MAX_RECENT = 30
SIMULATION, MINECRAFT = "simulation", "minecraft"


def minecraft_save_folders() -> list[Path]:
    """Where Minecraft keeps saves on this system (and the project's example saves)."""
    folders = [Path("data/minecraft_saves"), Path.home() / ".minecraft" / "saves"]
    if sys.platform == "darwin":
        folders.append(Path.home() / "Library" / "Application Support" / "minecraft" / "saves")
    appdata = os.environ.get("APPDATA")
    if appdata:
        folders.append(Path(appdata) / ".minecraft" / "saves")
    return [folder for folder in folders if folder.is_dir()]


# ---------------------------------------------------------------------- recent worlds
def recent_path() -> Path:
    return config_dir() / "recent_worlds.json"


def load_recent() -> list[dict[str, str]]:
    try:
        data = json.loads(recent_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [e for e in data if isinstance(e, dict) and "path" in e and "kind" in e]


def remember_world(path: Path, kind: str) -> None:
    """Put a world at the top of the recent list (opened or saved)."""
    entry = {"path": str(path.resolve()), "kind": kind}
    entries = [entry, *(e for e in load_recent() if e.get("path") != entry["path"])]
    try:
        recent_path().parent.mkdir(parents=True, exist_ok=True)
        recent_path().write_text(json.dumps(entries[:MAX_RECENT]) + "\n", encoding="utf-8")
    except OSError:
        pass


def thumbnail_path(world: Path) -> Path:
    digest = hashlib.sha1(str(world.resolve()).encode()).hexdigest()[:16]
    return config_dir() / "thumbnails" / f"{digest}.png"


def save_thumbnail(world: Path, image: QImage) -> None:
    """A square view of the world for the list (made when a simulation world is saved)."""
    if image.isNull():
        return
    side = min(image.width(), image.height())
    square = image.copy(
        (image.width() - side) // 2, (image.height() - side) // 2, side, side
    ).scaled(ICON * 2, ICON * 2, Qt.AspectRatioMode.IgnoreAspectRatio,
             Qt.TransformationMode.SmoothTransformation)  # fmt: skip
    path = thumbnail_path(world)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        square.save(str(path))
    except OSError:
        pass


# ---------------------------------------------------------------------- entries
@dataclass
class WorldEntry:
    kind: str  # MINECRAFT or SIMULATION
    path: Path
    name: str
    detail: str
    when: float  # last played / saved (seconds), for sorting
    icon: Path | None


def minecraft_entries() -> list[WorldEntry]:
    from redsim.mcworld import nbt

    entries = []
    for folder in minecraft_save_folders():
        for save in folder.iterdir():
            level = save / "level.dat"
            if not level.is_file():
                continue
            name, when, version = save.name, level.stat().st_mtime, ""
            try:
                data = nbt.read_file(level).get("Data", {})
                name = str(data.get("LevelName", save.name)) or save.name
                when = int(data.get("LastPlayed", when * 1000)) / 1000
                version = str(data.get("Version", {}).get("Name", ""))
            except (OSError, ValueError, KeyError, EOFError):
                pass
            icon = save / "icon.png"
            detail = f"{save.name} ({_date(when)})" + (f" · {version}" if version else "")
            entries.append(
                WorldEntry(MINECRAFT, save, name, detail, when, icon if icon.is_file() else None)
            )
    return sorted(entries, key=lambda e: -e.when)


def simulation_entries() -> list[WorldEntry]:
    entries, seen = [], set()
    candidates = [Path(e["path"]) for e in load_recent() if e.get("kind") == SIMULATION]
    candidates += sorted(Path("examples").glob("*.redsim.json"))
    for path in candidates:
        if not path.is_file() or path.resolve() in seen:
            continue
        seen.add(path.resolve())
        when = path.stat().st_mtime
        name = path.name.removesuffix(".redsim.json").removesuffix(".json")
        thumb = thumbnail_path(path)
        entries.append(
            WorldEntry(
                SIMULATION,
                path,
                name,
                f"{path.parent} ({_date(when)})",
                when,
                thumb if thumb.is_file() else None,
            )
        )
    return entries


def _date(seconds: float) -> str:
    return time.strftime("%d.%m.%y, %H:%M", time.localtime(seconds))


# ---------------------------------------------------------------------- the screen
class _Row(QWidget):
    def __init__(self, entry: WorldEntry) -> None:
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(10)
        icon = QLabel()
        icon.setFixedSize(ICON, ICON)
        pixmap = QPixmap(str(entry.icon)) if entry.icon is not None else QPixmap()
        if pixmap.isNull():
            block = (
                "minecraft:grass_block" if entry.kind == MINECRAFT else "minecraft:redstone_block"
            )
            pixmap = block_pixmap(block, ICON)
        icon.setPixmap(
            pixmap.scaled(
                ICON,
                ICON,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.FastTransformation,
            )  # fmt: skip
        )
        layout.addWidget(icon)
        text = QVBoxLayout()
        text.setSpacing(2)
        font = theme.PixelFont.load()
        name = QLabel()
        if font is not None:
            name.setPixmap(font.pixmap(entry.name, theme.TEXT, 2))
        else:
            name.setText(f"<b>{entry.name}</b>")
        text.addWidget(name)
        for line in (
            entry.detail,
            "Minecraft world" if entry.kind == MINECRAFT else "Simulation world",
        ):
            label = QLabel(line)
            label.setStyleSheet(f"color: {theme.TEXT_DIM};")
            text.addWidget(label)
        layout.addLayout(text, 1)


class WorldPicker(QDialog):
    """Choose a world to open: ``chosen`` is (kind, path) after ``exec``."""

    def __init__(self, parent: QWidget | None = None, tab: str = MINECRAFT) -> None:
        super().__init__(parent)
        self.setWindowTitle("Select World")
        self.resize(620, 560)
        self.chosen: tuple[str, Path] | None = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)
        title = QLabel()
        font = theme.PixelFont.load()
        if font is not None:
            title.setPixmap(font.pixmap("Select World", theme.TEXT, 3))
        else:
            title.setText("<b>Select World</b>")
        title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(title)
        self.search = QLineEdit()
        # The leading space keeps the text cursor off the placeholder's first letter
        # (together they read as a stray character).
        self.search.setPlaceholderText(" Type to search, ↑/↓ to choose, Enter to open")
        self.search.textChanged.connect(self._filter)
        self.search.returnPressed.connect(self._open)
        self.search.installEventFilter(self)  # ↑/↓ in the search box move in the list
        layout.addWidget(self.search)
        self.tabs = GameTabs()
        self.tabs.addTab("Minecraft saves")
        self.tabs.addTab("Simulation worlds")
        self.tabs.setCurrentIndex(0 if tab == MINECRAFT else 1)
        self.tabs.currentChanged.connect(lambda _: self._fill())
        layout.addWidget(self.tabs)
        self.list = QListWidget()
        self.list.setIconSize(QSize(ICON, ICON))
        self.list.setStyleSheet(
            f"QListWidget {{ background: {theme.SUNKEN}; }}"
            f"QListWidget::item:selected {{ background: {theme.WIDGET_HOVER};"
            " border: 2px solid #ffffff; }"
        )
        list_dirt = game_gui.dirt_brush(game_gui.LIST_SHADE)
        if list_dirt is not None:  # the game's look: dirt, darker under the list
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
        self.list.itemDoubleClicked.connect(lambda _: self._open())
        self.list.currentItemChanged.connect(lambda *_: self._update_buttons())
        layout.addWidget(self.list, 1)
        self.empty = QLabel()
        self.empty.setStyleSheet(f"color: {theme.TEXT_DIM};")
        self.empty.setWordWrap(True)
        layout.addWidget(self.empty)
        buttons = QHBoxLayout()
        self.open_button = GameButton("Play Selected World")
        self.open_button.setDefault(True)
        self.open_button.clicked.connect(self._open)
        browse = GameButton("Browse…")
        browse.setToolTip("Open another .redsim.json file or Minecraft save folder")
        browse.clicked.connect(self._browse)
        cancel = GameButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(self.open_button, 2)
        buttons.addWidget(browse, 1)
        buttons.addWidget(cancel, 1)
        layout.addLayout(buttons)
        self._entries: dict[str, list[WorldEntry]] = {}
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

    @property
    def kind(self) -> str:
        return MINECRAFT if self.tabs.currentIndex() == 0 else SIMULATION

    def entries(self, kind: str) -> list[WorldEntry]:
        if kind not in self._entries:
            self._entries[kind] = minecraft_entries() if kind == MINECRAFT else simulation_entries()
        return self._entries[kind]

    def _fill(self) -> None:
        self.list.clear()
        for entry in self.entries(self.kind):
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, entry)
            item.setSizeHint(QSize(0, ICON + 10))
            self.list.addItem(item)
            row = _Row(entry)
            row.setToolTip(str(entry.path.resolve()))
            self.list.setItemWidget(item, row)
        if self.list.count():
            self.list.setCurrentRow(0)
        if self.kind == MINECRAFT:
            folders = ", ".join(str(f) for f in minecraft_save_folders()) or "none found"
            self.empty.setText(f"Saves folders: {folders}")
        else:
            self.empty.setText("Recently opened or saved simulation worlds, and the examples.")
        self._filter(self.search.text())

    def _filter(self, text: str) -> None:
        needle = text.strip().lower()
        for row in range(self.list.count()):
            item = self.list.item(row)
            entry: WorldEntry = item.data(Qt.ItemDataRole.UserRole)
            hay = f"{entry.name} {entry.path.name}".lower()
            item.setHidden(bool(needle) and needle not in hay)
        current = self.list.currentItem()
        if current is None or current.isHidden():
            visible = [self.list.item(r) for r in range(self.list.count())]
            first = next((i for i in visible if not i.isHidden()), None)
            if first is not None:
                self.list.setCurrentItem(first)
        self._update_buttons()

    def _update_buttons(self) -> None:
        item = self.list.currentItem()
        self.open_button.setEnabled(item is not None and not item.isHidden())

    def _open(self) -> None:
        item = self.list.currentItem()
        if item is None or item.isHidden():
            return
        entry: WorldEntry = item.data(Qt.ItemDataRole.UserRole)
        self.chosen = (entry.kind, entry.path)
        self.accept()

    def _browse(self) -> None:
        """Another world: a Minecraft save folder or a simulation file (Qt's own dialog,
        which opens faster than the desktop's)."""
        options = QFileDialog.Option.DontUseNativeDialog
        if self.kind == MINECRAFT:
            start = next((str(f) for f in minecraft_save_folders()), str(Path.home()))
            folder = QFileDialog.getExistingDirectory(
                self, "Minecraft save folder", start, options | QFileDialog.Option.ShowDirsOnly
            )
            if folder:
                self.chosen = (MINECRAFT, Path(folder))
                self.accept()
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Simulation world",
            "",
            "Redstone simulator worlds (*.redsim.json *.json)",
            options=options,
        )
        if path:
            self.chosen = (SIMULATION, Path(path))
            self.accept()
