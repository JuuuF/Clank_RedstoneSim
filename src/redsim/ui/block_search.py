"""Quick block search (Ctrl+Space, ``/`` or Shift twice), like Blender's search or Rider's
"search everywhere": type a few letters, pick with Enter, and build with it.

``rank_blocks`` is plain Python: letters must appear in order (fuzzy), and matches at the
start of the name or of a word rank first; with an empty query the recently used blocks
come first.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor, QKeyEvent, QPainter
from PySide6.QtWidgets import (
    QFrame,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QVBoxLayout,
    QWidget,
)

from redsim.ui import theme
from redsim.ui.icons import block_icon
from redsim.ui.inventory import all_blocks, block_label
from redsim.world import blocks


def _score(query: str, text: str) -> int | None:
    """Lower is better; None if the letters of ``query`` do not appear in order."""
    if not query:
        return 0
    if text.startswith(query):
        return 0
    words = text.replace("_", " ").split()
    if any(word.startswith(query) for word in words):
        return 1
    if query in text:
        return 2
    position, gaps = 0, 0
    for letter in query:
        found = text.find(letter, position)
        if found < 0:
            return None
        gaps += found - position
        position = found + 1
    return 3 + gaps


def rank_blocks(query: str, recent: list[str]) -> list[tuple[str, str]]:
    """(block id, folder path) matches for ``query``, best first."""
    query = query.strip().lower()
    entries = all_blocks()
    scored = []
    for order, (block_id, path) in enumerate(entries):
        text = f"{block_label(block_id)} {block_id.split(':')[-1]}".lower()
        score = _score(query, text)
        if score is None:
            score = _score(query, path.lower())
            if score is None:
                continue
            score += 10  # a folder match ranks after name matches
        recency = recent.index(block_id) if block_id in recent else len(recent)
        scored.append(((score, recency if not query else 0, order), block_id, path))
    scored.sort()
    return [(block_id, path) for _, block_id, path in scored]


#: Item data: the block's inventory folder, drawn dim and right-aligned.
CATEGORY_ROLE = Qt.ItemDataRole.UserRole + 1


class _CategoryDelegate(QStyledItemDelegate):
    """The default row (icon, name), plus the folder on the right in dim text."""

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: Any) -> None:
        super().paint(painter, option, index)
        category = index.data(CATEGORY_ROLE)
        if not category:
            return
        painter.save()
        painter.setPen(QColor(theme.TEXT_DIM))
        rect = option.rect.adjusted(0, 0, -10, 0)  # type: ignore[attr-defined]
        align = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        painter.drawText(rect, align, category)
        painter.restore()


class BlockSearch(QFrame):
    """A popup over the viewport: a search field and the matching blocks."""

    chosen = Signal(object)  # Block

    def __init__(self, parent: QWidget, recent: list[str]) -> None:
        super().__init__(parent, Qt.WindowType.Popup)
        self.recent = recent
        self.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        self.field = QLineEdit()
        self.field.setPlaceholderText("Search blocks… (Enter builds with it, Esc closes)")
        self.field.textChanged.connect(self._filter)
        self.field.installEventFilter(self)
        layout.addWidget(self.field)
        self.results = QListWidget()
        self.results.setIconSize(QSize(28, 28))
        self.results.setItemDelegate(_CategoryDelegate(self.results))
        self.results.itemActivated.connect(self._choose)
        layout.addWidget(self.results)
        self.resize(380, 360)
        self._filter("")

    def _filter(self, text: str) -> None:
        self.results.clear()
        for block_id, path in rank_blocks(text, self.recent):
            label = block_label(block_id)
            recent = " · recent" if block_id in self.recent and not text else ""
            item = QListWidgetItem(block_icon(blocks.get(block_id), 28), label)
            item.setData(Qt.ItemDataRole.UserRole, block_id)
            item.setData(CATEGORY_ROLE, f"{path}{recent}")
            self.results.addItem(item)
        if self.results.count():
            self.results.setCurrentRow(0)

    def eventFilter(self, watched: object, event: object) -> bool:
        # Up/Down/Enter in the search field move through and pick from the list.
        if (
            watched is self.field
            and isinstance(event, QKeyEvent)
            and event.type() == QKeyEvent.Type.KeyPress
        ):
            key = event.key()
            if key in (Qt.Key.Key_Down, Qt.Key.Key_Up):
                row = self.results.currentRow() + (1 if key == Qt.Key.Key_Down else -1)
                self.results.setCurrentRow(max(0, min(self.results.count() - 1, row)))
                return True
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                item = self.results.currentItem()
                if item is not None:
                    self._choose(item)
                return True
        return super().eventFilter(watched, event)  # type: ignore[arg-type]

    def _choose(self, item: QListWidgetItem) -> None:
        block_id = item.data(Qt.ItemDataRole.UserRole)
        self.close()
        self.chosen.emit(blocks.get(block_id))

    def open_over(self, widget: QWidget) -> None:
        center = widget.mapToGlobal(widget.rect().center())
        self.move(center.x() - self.width() // 2, center.y() - self.height() // 2)
        self.show()
        self.field.setFocus()
