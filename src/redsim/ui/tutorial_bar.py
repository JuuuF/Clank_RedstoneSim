"""The bar at the top of the 3D view while the tutorial runs (owner, 2026-10-14: the
tutorial should be a mode "which can be closed and exited easily"): it says you are in
the tutorial and has the way out. Exit tutorial brings back the world you had open
before, as you left it (unsaved changes included); the card can be hidden and shown
again from here.

Drawn like the game's tooltips: near-black with a purple frame.
"""

from __future__ import annotations

from PySide6.QtCore import QRect, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPaintEvent
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from redsim.ui import game_gui, theme

#: The game's tooltip: background 0xF0100010, frame from 0x505000FF to 0x5028007F.
BACKGROUND = QColor(16, 0, 16, 235)
FRAME_TOP = QColor(80, 0, 255, 200)
FRAME_BOTTOM = QColor(40, 0, 127, 200)


class TutorialBar(QWidget):
    exit_requested = Signal()
    card_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 6, 8, 6)
        layout.setSpacing(8)
        self.label = QLabel("Tutorial")
        self.label.setStyleSheet(f"color: {theme.GOLD}; font-weight: bold;")
        layout.addWidget(self.label)
        self.detail = QLabel()
        self.detail.setStyleSheet("color: #e0e0e0;")
        layout.addWidget(self.detail)
        self.card_button = self._button("Show card", self.card_requested.emit)
        self.card_button.setToolTip("Show the lesson card again")
        layout.addWidget(self.card_button)
        exit_button = self._button("Exit tutorial", self.exit_requested.emit)
        exit_button.setToolTip("Back to the world you had open before")
        layout.addWidget(exit_button)

    def _button(self, text: str, slot: object) -> QPushButton:
        button: QPushButton = (
            game_gui.GameButton(text) if game_gui.available() else QPushButton(text)
        )
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        button.clicked.connect(slot)
        return button

    def set_state(self, detail: str, card_shown: bool) -> None:
        if self.detail.text() != detail:
            self.detail.setText(detail)
        self.card_button.setVisible(not card_shown)
        self.adjustSize()

    def place(self, view: QWidget) -> None:
        """Top middle of ``view``."""
        self.adjustSize()
        self.move((view.width() - self.width()) // 2, 8)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        rect = self.rect()
        painter.fillRect(rect.adjusted(2, 2, -2, -2), BACKGROUND)
        for color, line in (
            (FRAME_TOP, QRect(rect.left() + 2, rect.top() + 2, rect.width() - 4, 2)),
            (FRAME_BOTTOM, QRect(rect.left() + 2, rect.bottom() - 3, rect.width() - 4, 2)),
        ):
            painter.fillRect(line, color)
        for x in (rect.left() + 2, rect.right() - 3):
            painter.fillRect(QRect(x, rect.top() + 2, 2, rect.height() - 4), FRAME_BOTTOM)
        painter.end()
