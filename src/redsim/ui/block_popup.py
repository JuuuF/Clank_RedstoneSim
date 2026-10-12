"""The inspector of one block as a popup over the viewport (E over a block).

It holds its own ``InspectorPanel`` (the same controls as the Inspector tab: state,
contents, signal source, pressure-plate visitors, …); the main window connects its
signals to the same handlers. The popup closes on a click outside, on Esc, or on E again,
and follows the block while the simulation runs (``refresh``).
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QGuiApplication, QKeyEvent
from PySide6.QtWidgets import QFrame, QScrollArea, QVBoxLayout, QWidget

from redsim.core.pos import Pos
from redsim.editor.document import Document
from redsim.ui import theme
from redsim.ui.panels import InspectorPanel

POPUP_WIDTH = 400  # at least; wider when the controls need it
POPUP_MAX_HEIGHT = 560
CURSOR_GAP = 18  # pixels between the cursor and the popup's corner


class BlockPopup(QFrame):
    closed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent, Qt.WindowType.Popup)
        self.setObjectName("blockPopup")
        self.setStyleSheet(
            f"#blockPopup {{ background: {theme.PANEL}; border: 1px solid {theme.LINE}; }}"
        )
        self.pos_: Pos | None = None
        self.close_keys: tuple[str, ...] = ("E",)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        self.inspector = InspectorPanel()
        self.scroller = QScrollArea()
        self.scroller.setWidgetResizable(True)
        self.scroller.setFrameShape(QFrame.Shape.NoFrame)
        self.scroller.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroller.setWidget(self.inspector)
        layout.addWidget(self.scroller)

    def open_at(self, document: Document, pos: Pos, anchor: QPoint) -> None:
        """Show the block at ``pos`` beside the screen point ``anchor`` (the cursor)."""
        self.pos_ = pos
        self.inspector.show_block(document, pos)
        self.inspector.adjustSize()
        hint = self.inspector.sizeHint()
        bar = self.scroller.verticalScrollBar().sizeHint().width()
        width = max(POPUP_WIDTH, hint.width() + bar + 28)
        self.resize(width, min(POPUP_MAX_HEIGHT, hint.height() + 20))
        self.move(self._placed(anchor))
        self.show()
        self.raise_()

    def _placed(self, anchor: QPoint) -> QPoint:
        """Below right of the cursor, kept inside the window (else the screen)."""
        screen = QGuiApplication.screenAt(anchor) or QGuiApplication.primaryScreen()
        area = screen.availableGeometry()
        window = self.parentWidget()
        if window is not None:
            frame = window.window().geometry()
            if frame.width() >= self.width() and frame.height() >= self.height():
                area = area.intersected(frame)
        x, y = anchor.x() + CURSOR_GAP, anchor.y() + CURSOR_GAP
        if x + self.width() > area.right():
            x = anchor.x() - CURSOR_GAP - self.width()
        if y + self.height() > area.bottom():
            y = max(area.top(), area.bottom() - self.height())
        return QPoint(max(area.left(), x), y)

    def refresh(self, document: Document) -> None:
        if self.isVisible() and self.pos_ is not None:
            self.inspector.show_block(document, self.pos_)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        text = event.text().upper()
        if event.key() == Qt.Key.Key_Escape or (text and text in self.close_keys):
            self.close()
            return
        super().keyPressEvent(event)

    def hideEvent(self, event: object) -> None:  # noqa: D102 - Qt override
        super().hideEvent(event)  # type: ignore[arg-type]
        self.pos_ = None
        self.closed.emit()
