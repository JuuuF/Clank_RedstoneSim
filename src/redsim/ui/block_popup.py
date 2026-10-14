"""The inspector of one block as a floating panel over the viewport (E over a block).

It holds its own ``InspectorPanel`` (the same controls as the Inspector tab: state,
contents, signal source, pressure-plate visitors, …); the main window connects its
signals to the same handlers. A row of **pin** chips above it pins values to the block:
they stay in the view as a small live tag (``editor/pins.py``) after the panel closes.

The panel does not grab the keyboard or the mouse (owner, 2026-10-14): the timeline's
buttons and keys (run, pause, step, rewind) keep working while it is open, and keys the
panel does not use itself go on to the window's actions. It closes on Esc or E, its ×,
or a click elsewhere in the window except on the timeline, and follows the block while
the simulation runs (``refresh``).
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QEvent, QObject, QPoint, Qt, Signal
from PySide6.QtGui import QGuiApplication, QKeyEvent, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from redsim.core.pos import Pos
from redsim.editor import pins
from redsim.editor.document import Document
from redsim.ui import theme
from redsim.ui.panel_widgets import FlowLayout
from redsim.ui.panels import InspectorPanel

POPUP_WIDTH = 400  # at least; wider when the controls need it
POPUP_MAX_HEIGHT = 600
CURSOR_GAP = 18  # pixels between the cursor and the popup's corner


class BlockPopup(QFrame):
    closed = Signal()
    pin_toggled = Signal(object, str, bool)  # Pos, pin key, on

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self.setObjectName("blockPopup")
        self.setStyleSheet(
            f"#blockPopup {{ background: {theme.PANEL}; border: 1px solid {theme.LINE}; }}"
        )
        self.pos_: Pos | None = None
        self.close_keys: tuple[str, ...] = ("E",)
        #: Widgets whose clicks keep the panel open (the timeline), set by the window.
        self.keep_open_for: Callable[[QWidget], bool] = lambda widget: False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 8)
        top = QHBoxLayout()
        pin_label = QLabel("Pin to block:")
        pin_label.setStyleSheet(f"color: {theme.TEXT_DIM};")
        pin_label.setToolTip(
            "Pinned values stay in the view as a small tag at the block, live while the "
            "simulation runs (saved with the world)"
        )
        top.addWidget(pin_label, 0, Qt.AlignmentFlag.AlignTop)
        self.pin_row = QWidget()
        self.pin_layout = FlowLayout(self.pin_row)
        top.addWidget(self.pin_row, 1)
        close = QToolButton()
        close.setText("×")
        close.setToolTip("Close (Esc)")
        close.setAutoRaise(True)
        close.clicked.connect(self.close)
        top.addWidget(close, 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(top)
        self.pin_buttons: dict[str, QPushButton] = {}
        self._pin_keys: tuple[str, ...] = ()
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
        self._show_pins(document, pos)
        self.inspector.adjustSize()
        hint = self.inspector.sizeHint()
        bar = self.scroller.verticalScrollBar().sizeHint().width()
        width = max(POPUP_WIDTH, hint.width() + bar + 28)
        extra = self.pin_row.sizeHint().height() + 16
        self.resize(width, min(POPUP_MAX_HEIGHT, hint.height() + 20 + extra))
        self.move(self._placed(anchor))
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)
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
            self._show_pins(document, self.pos_)

    # ------------------------------------------------------------------ pins
    def _show_pins(self, document: Document, pos: Pos) -> None:
        """One checkable chip per value that can be pinned; checked when pinned."""
        options = pins.choices(document, pos)
        keys = tuple(key for key, _ in options)
        if keys != self._pin_keys:
            self._pin_keys = keys
            for button in self.pin_buttons.values():
                self.pin_layout.removeWidget(button)
                button.deleteLater()
            self.pin_buttons = {}
            for key, label in options:
                button = QPushButton(label)
                button.setCheckable(True)
                button.setProperty("chip", True)
                button.setToolTip(f"Show “{label}” at the block in the view")
                button.toggled.connect(lambda on, k=key: self._pin_toggled(k, on))
                self.pin_layout.addWidget(button)
                self.pin_buttons[key] = button
        chosen = set(pins.pinned(document, pos))
        for key, button in self.pin_buttons.items():
            if button.isChecked() != (key in chosen):
                button.blockSignals(True)
                button.setChecked(key in chosen)
                button.blockSignals(False)

    def _pin_toggled(self, key: str, on: bool) -> None:
        if self.pos_ is not None:
            self.pin_toggled.emit(self.pos_, key, on)

    # ------------------------------------------------------------------ keys and clicks
    def keyPressEvent(self, event: QKeyEvent) -> None:
        text = event.text().upper()
        if event.key() == Qt.Key.Key_Escape or (text and text in self.close_keys):
            self.close()
            return
        if self._forward(event):
            return
        super().keyPressEvent(event)

    def _forward(self, event: QKeyEvent) -> bool:
        """A key the panel's controls did not use: the window's action bound to it."""
        window = self.parentWidget()
        if window is None:
            return False
        pressed = QKeySequence(event.keyCombination())
        for action in window.window().actions():
            if action.isEnabled() and any(s == pressed for s in action.shortcuts()):
                action.trigger()
                return True
        return False

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """A click elsewhere in the window closes the panel, unless it is on the timeline
        (or a menu)."""
        if event.type() == QEvent.Type.MouseButtonPress and self.isVisible():
            widget = watched if isinstance(watched, QWidget) else None
            inside = widget is not None and (widget is self or self.isAncestorOf(widget))
            if (
                widget is not None
                and widget.isWindow() is False
                and not inside
                and not isinstance(widget.window(), QMenu)
                and not self.keep_open_for(widget)
            ):
                self.close()
        return False

    def hideEvent(self, event: object) -> None:  # noqa: D102 - Qt override
        super().hideEvent(event)  # type: ignore[arg-type]
        app = QApplication.instance()
        if app is not None:
            app.removeEventFilter(self)
        self.pos_ = None
        self.closed.emit()
