"""The "Builds in this world" screen: the builds an index of the opened save found
(``mcworld/index.py``), most redstone first; choosing one takes the camera there (the
chunks around it stream in)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPaintEvent
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from redsim.mcworld.index import Build
from redsim.ui import game_gui, theme
from redsim.ui.game_gui import GameButton
from redsim.ui.names import block_name


def describe(build: Build) -> str:
    """One line about a build: where, how big, what it is made of."""
    x, y, z = (round(v) for v in build.center)
    sx, sy, sz = build.size
    parts = ", ".join(f"{block_name(block_id)} ×{n}" for block_id, n in build.top_parts())
    redstone = f"{build.redstone} redstone parts" if build.redstone else "no redstone"
    return f"{x} {y} {z} · {sx}×{sy}×{sz} · {redstone} · {parts}"


class BuildsDialog(QDialog):
    """Choose a build to go to: ``chosen`` after ``exec``."""

    def __init__(self, builds: list[Build], world: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Builds in this world")
        self.resize(720, 420)
        self.chosen: Build | None = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        title = QLabel()
        font = theme.PixelFont.load()
        heading = f"Builds in {world}"
        if font is not None:
            title.setPixmap(font.pixmap(heading, theme.TEXT, 2))
        else:
            title.setText(f"<b>{heading}</b>")
        title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(title)
        self.list = QListWidget()
        self.list.setWordWrap(True)
        for build in builds:
            item = QListWidgetItem(describe(build))
            item.setData(Qt.ItemDataRole.UserRole, build)
            item.setToolTip(
                f"From {build.low} to {build.high}, {build.blocks} placed blocks in "
                f"{build.chunks} chunks"
            )
            self.list.addItem(item)
        if builds:
            self.list.setCurrentRow(0)
        else:
            self.list.addItem("No builds found: only terrain and nature.")
        self.list.itemDoubleClicked.connect(lambda _: self._go())
        layout.addWidget(self.list, 1)
        buttons = QHBoxLayout()
        go = GameButton("Go there")
        go.setDefault(True)
        go.setEnabled(bool(builds))
        go.clicked.connect(self._go)
        close = GameButton("Close")
        close.clicked.connect(self.reject)
        buttons.addWidget(go, 2)
        buttons.addWidget(close, 1)
        layout.addLayout(buttons)
        if game_gui.available():
            self.list.setStyleSheet(
                "QListWidget { background: rgba(0, 0, 0, 120); border: none; color: #e0e0e0; }"
                "QListWidget::item { padding: 4px; }"
                "QListWidget::item:selected { background: rgba(0, 0, 0, 160);"
                " border: 2px solid #ffffff; }"
            )

    def paintEvent(self, event: QPaintEvent) -> None:
        game_gui.paint_dirt(self)

    def _go(self) -> None:
        item = self.list.currentItem()
        build = item.data(Qt.ItemDataRole.UserRole) if item is not None else None
        if isinstance(build, Build):
            self.chosen = build
            self.accept()
