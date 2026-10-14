"""The tutorial card: the current lesson step over the top-right corner of the 3D view,
drawn like the game's own tutorial hints (``TutorialToast``: the ``toast/tutorial``
sprite, an icon, the title in purple, black text and a progress bar along the bottom).

The window polls it with snapshots (``redsim.tutorial.lessons.Snapshot``); when a step's
check passes, the card shows "Done!" and moves on after a moment. Progress is kept in
``tutorial.json`` in the config folder, so Help → Tutorial continues where it stopped.
"""

from __future__ import annotations

import html
import json
import math
import re
from functools import cache
from typing import Any

from PySide6.QtCore import QPoint, QRect, Qt, QTimer, QVariantAnimation, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPaintEvent, QPolygon
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from redsim.tutorial.lessons import LESSONS, Progress, Snapshot, Step
from redsim.ui import game_gui
from redsim.ui.assets import Assets
from redsim.ui.hints import keycaps_html, preferred_binding
from redsim.ui.keymap import Keymap
from redsim.ui.preferences import config_dir

#: Colors of the game's tutorial toast: title (-11534256), text, the progress bar's
#: track and fill (-16755456).
TITLE_COLOR = "#500050"
TEXT_COLOR = "#000000"
BAR_TRACK = QColor("#ffffff")
BAR_FILL = QColor("#006000")
DONE_COLOR = "#006000"
#: Fallback look without the game's jar.
PANEL = QColor("#dddddd")
PANEL_EDGE = QColor("#a8a8a8")
WIDTH = 360
#: How long "Done!" shows before the next step.
DONE_MS = 1100
#: The success glint: how long it plays, and the size of one glint texture tile.
GLINT_MS = 1000
GLINT_TILE = 96
#: The Lessons menu, drawn like the game's tooltips (near-black, purple frame).
MENU_STYLE = (
    "QMenu { background: rgba(16, 0, 16, 240); color: #ffffff; border: 2px solid #28007f;"
    " padding: 2px; }"
    "QMenu::item { padding: 4px 18px 4px 10px; }"
    "QMenu::item:selected { background: #3c1f8a; color: #ffff55; }"
)
#: The toast icon shown for each lesson (``toast/<name>``).
ICONS = (
    "mouse",
    "right_click",
    "recipe_book",
    "wooden_planks",
    "mouse",
    "tree",
    "recipe_book",
    "social_interactions",
    "recipe_book",
)
_TOKEN = re.compile(r"\{(key|cap):([^}]+)\}")


@cache
def _glint_image() -> QImage | None:
    """The game's item glint texture, darkened so its sum stays a shimmer."""
    data = Assets.find()
    raw = (
        data.file_bytes("assets/minecraft/textures/misc/enchanted_glint_item.png") if data else None
    )
    image = QImage.fromData(raw) if raw else QImage()
    return None if image.isNull() else image.convertToFormat(QImage.Format.Format_ARGB32)


def progress_path() -> Any:
    return config_dir() / "tutorial.json"


def load_progress() -> Progress:
    try:
        return Progress.from_json(json.loads(progress_path().read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return Progress()


def save_progress(progress: Progress) -> None:
    path = progress_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(progress.to_json()) + "\n", encoding="utf-8")
    except OSError:
        pass  # progress is a convenience


def render_text(text: str, keymap: Keymap) -> str:
    """A step's text as rich text: ``{key:action}`` becomes the user's binding as a
    keycap, ``{cap:Text}`` a keycap as written."""

    def keycap(match: re.Match[str]) -> str:
        kind, value = match[1], match[2]
        keys = preferred_binding(keymap, value) if kind == "key" else value
        return keycaps_html(keys) if keys else html.escape(value)

    return _TOKEN.sub(keycap, text)


class TutorialCard(QWidget):
    """The card. ``step_started(step)`` asks the window to act on a new step (move the
    camera); ``closed`` when the user closes it."""

    step_started = Signal(object)  # Step
    closed = Signal()

    def __init__(self, keymap: Keymap, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.keymap = keymap
        self.progress = load_progress()
        self.setFixedWidth(WIDTH)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(64, 12, 12, 16)
        layout.setSpacing(6)
        top = QHBoxLayout()
        self.title = QLabel()
        self.title.setStyleSheet(f"color: {TITLE_COLOR}; font-weight: bold;")
        self.title.setWordWrap(True)
        top.addWidget(self.title, 1)
        close = QToolButton()
        close.setText("×")
        close.setToolTip("Hide the card (the bar at the top shows it again)")
        close.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        close.setStyleSheet(
            f"QToolButton {{ color: {TEXT_COLOR}; border: none; font-size: 16px; }}"
            "QToolButton:hover { color: #a00000; }"
        )
        close.clicked.connect(self.close_card)
        top.addWidget(close, 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(top)
        self.body = QLabel()
        self.body.setWordWrap(True)
        self.body.setTextFormat(Qt.TextFormat.RichText)
        self.body.setStyleSheet(f"color: {TEXT_COLOR};")
        self.body.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        layout.addWidget(self.body)
        self.status = QLabel()
        self.status.setStyleSheet(f"color: {DONE_COLOR}; font-weight: bold;")
        layout.addWidget(self.status)
        buttons = QHBoxLayout()
        buttons.setSpacing(4)
        self.lessons = self._button("Lessons ▾", lambda: None)
        menu = QMenu(self.lessons)
        menu.setStyleSheet(MENU_STYLE)
        for index, lesson in enumerate(LESSONS):
            action = menu.addAction(f"{index + 1}. {lesson.title}")
            action.triggered.connect(lambda _=False, i=index: self.go(i))
        self.lessons.setMenu(menu)
        self.lessons.setMinimumWidth(96)
        buttons.addWidget(self.lessons)
        buttons.addStretch(1)
        self.back = self._button("Back", self._back)
        self.next = self._button("Next", self._next)
        buttons.addWidget(self.back)
        buttons.addWidget(self.next)
        layout.addLayout(buttons)
        self._advance_timer = QTimer(self)
        self._advance_timer.setSingleShot(True)
        self._advance_timer.timeout.connect(self._next)
        #: The success glint (0 → 1 while it plays), like an enchanted item's shimmer.
        self.glint = 0.0
        self._glint = QVariantAnimation(self)
        self._glint.setStartValue(0.0)
        self._glint.setEndValue(1.0)
        self._glint.setDuration(GLINT_MS)
        self._glint.valueChanged.connect(self._glint_frame)
        self._glint.finished.connect(lambda: self._glint_frame(0.0))
        self._started = False
        self.show_step()

    def _button(self, text: str, slot: Any) -> QPushButton:
        button: QPushButton = (
            game_gui.GameButton(text) if game_gui.available() else QPushButton(text)
        )
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        button.setMinimumWidth(72)
        button.clicked.connect(slot)
        return button

    # ------------------------------------------------------------------ steps
    @property
    def step(self) -> Step:
        return self.progress.current

    def show_step(self) -> None:
        progress = self.progress
        lesson = LESSONS[progress.lesson]
        self.title.setText(
            f"Lesson {progress.lesson + 1}/{len(LESSONS)}: {html.escape(lesson.title)}"
            f"<br><span style='font-weight: normal;'>{html.escape(self.step.title)}</span>"
        )
        self.body.setText(render_text(self.step.text, self.keymap))
        self.status.setText("")
        self.back.setEnabled(progress.lesson > 0 or progress.step > 0)
        self.next.setText("Finish" if progress.is_last else "Next")
        self._started = False
        self.adjustSize()
        self.update()

    def begin(self, snapshot: Snapshot) -> None:
        """Start the shown step with ``snapshot`` as its baseline."""
        self.progress.begin(snapshot)
        self._started = True
        self.step_started.emit(self.step)

    def poll(self, snapshot: Snapshot) -> None:
        """Check the current step; the first poll after a change starts it."""
        if not self._started:
            self.begin(snapshot)
            return
        if self._advance_timer.isActive():
            return
        if self.progress.poll(snapshot):
            self.status.setText("✔ Done!")
            self.celebrate()
            self._advance_timer.start(DONE_MS)

    def celebrate(self) -> None:
        """A step is done: the card flashes and an enchantment glint sweeps over it."""
        self._glint.stop()
        self._glint.start()

    def _glint_frame(self, value: object) -> None:
        self.glint = float(value)  # type: ignore[arg-type]
        self.update()

    def go(self, lesson: int, step: int = 0) -> None:
        self._advance_timer.stop()
        self.progress.go(lesson, step)
        save_progress(self.progress)
        self.show_step()

    def _next(self) -> None:
        self._advance_timer.stop()
        if self.progress.is_last:
            self.progress.go(0)
            save_progress(self.progress)
            self.close_card()
            return
        self.progress.advance()
        save_progress(self.progress)
        self.show_step()

    def _back(self) -> None:
        self._advance_timer.stop()
        self.progress.back()
        save_progress(self.progress)
        self.show_step()

    def close_card(self) -> None:
        self._advance_timer.stop()
        self.hide()
        self.closed.emit()

    def set_keymap(self, keymap: Keymap) -> None:
        self.keymap = keymap
        self.show_step()

    # ------------------------------------------------------------------ drawing
    def place(self, view: QWidget, below: int = 0) -> None:
        """Top-right corner of ``view`` (or lower, below an overlay of height ``below``)."""
        self.adjustSize()
        self.move(view.width() - self.width() - 10, 10 + below)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        rect = self.rect()
        if not game_gui.draw_sprite(painter, "toast/tutorial", rect):
            painter.fillRect(rect, PANEL_EDGE)
            painter.fillRect(rect.adjusted(3, 3, -3, -3), PANEL)
        icon = game_gui.sprite(f"toast/{ICONS[self.progress.lesson % len(ICONS)]}")
        if icon is not None:
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
            painter.drawImage(QRect(12, 12, 40, 40), icon)
        steps = len(LESSONS[self.progress.lesson].steps)
        done = self.progress.step + (1 if self.progress.done else 0)
        bar = QRect(6, rect.height() - 8, rect.width() - 12, 2)
        painter.fillRect(bar, BAR_TRACK)
        painter.fillRect(QRect(bar.x(), bar.y(), round(bar.width() * done / steps), 2), BAR_FILL)
        if self.glint > 0.0:
            self._paint_glint(painter, rect.adjusted(3, 3, -3, -3))
        painter.end()

    def _paint_glint(self, painter: QPainter, rect: QRect) -> None:
        """The enchantment glint (``misc/enchanted_glint_item``, added like the game's
        glint shader), sliding diagonally and fading in and out, over a quick white
        flash at the start."""
        t = self.glint
        flash = max(0.0, 1.0 - t * 5.0) * 0.55
        if flash:
            painter.fillRect(rect, QColor(255, 255, 255, round(255 * flash)))
        strength = math.sin(math.pi * t)
        painter.save()
        painter.setClipRect(rect)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)
        painter.setOpacity(min(1.0, 1.3 * strength))
        image = _glint_image()
        if image is not None:
            size = GLINT_TILE
            shift = round(t * size * 2)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
            for x in range(rect.left() - 2 * size + shift, rect.right() + size, size):
                for y in range(rect.top() - 2 * size + shift // 2, rect.bottom() + size, size):
                    painter.drawImage(QRect(x, y, size, size), image)
        else:  # without the jar: purple bands
            painter.setPen(Qt.PenStyle.NoPen)
            for k in range(-4, 8):
                offset = round((k + t * 2) * rect.height() * 0.6)
                band = QPolygon(
                    [
                        QPoint(rect.left() + offset, rect.bottom()),
                        QPoint(rect.left() + offset + 18, rect.bottom()),
                        QPoint(rect.left() + offset + 18 + rect.height(), rect.top()),
                        QPoint(rect.left() + offset + rect.height(), rect.top()),
                    ]
                )
                painter.setBrush(QColor(128, 64, 204, 150))
                painter.drawPolygon(band)
        painter.restore()
