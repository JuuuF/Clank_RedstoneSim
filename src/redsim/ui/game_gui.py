"""The game's menu look for dialogs: the dirt background of the game's option screens, a
darker list area, stone buttons and tabs (the ``widget/button`` and ``widget/tab``
nine-slice sprites) with text in the pixel font. Everything comes from the client jar;
without it the widgets fall back to the app's own theme."""

from __future__ import annotations

import json
from functools import cache

from PySide6.QtCore import QPoint, QRect, QSize, Qt
from PySide6.QtGui import QBrush, QColor, QImage, QPainter, QPaintEvent, QPixmap
from PySide6.QtWidgets import QPushButton, QTabBar, QWidget

from redsim.ui import theme
from redsim.ui.assets import Assets

#: Screen pixels per sprite pixel (the game's GUI scale 2).
SCALE = 2
#: Brightness of the dirt behind a screen and behind its list (the game's 64 and 32 of 255).
BACKGROUND_SHADE = 0.25
LIST_SHADE = 0.125
#: Text colors of the game's buttons: active, disabled.
BUTTON_TEXT = "#ffffff"
BUTTON_TEXT_DISABLED = "#a0a0a0"


@cache
def _image(path: str) -> QImage | None:
    assets = Assets.find()
    data = assets.file_bytes(path) if assets is not None else None
    image = QImage.fromData(data) if data else QImage()
    if image.isNull():
        return None
    return image.convertToFormat(QImage.Format.Format_ARGB32)


@cache
def _borders(sprite: str) -> tuple[int, int, int, int]:
    """A GUI sprite's nine-slice borders (left, top, right, bottom) from its ``.mcmeta``."""
    assets = Assets.find()
    path = f"assets/minecraft/textures/gui/sprites/{sprite}.png.mcmeta"
    raw = assets.file_bytes(path) if assets is not None else None
    try:
        scaling = json.loads(raw or b"{}")["gui"]["scaling"]
    except (KeyError, ValueError):
        return (0, 0, 0, 0)
    border = scaling.get("border", 0)
    if isinstance(border, int):
        return (border, border, border, border)
    return tuple(int(border.get(k, 0)) for k in ("left", "top", "right", "bottom"))  # type: ignore[return-value]


def sprite(name: str) -> QImage | None:
    """A GUI sprite such as ``widget/button``; None without the game's jar."""
    return _image(f"assets/minecraft/textures/gui/sprites/{name}.png")


def available() -> bool:
    return sprite("widget/button") is not None


def draw_sprite(painter: QPainter, name: str, rect: QRect, scale: int = SCALE) -> bool:
    """Draw a nine-slice sprite over ``rect``: corners as they are, edges and middle
    stretched, every sprite pixel ``scale`` screen pixels (crisp, no smoothing)."""
    image = sprite(name)
    if image is None:
        return False
    left, top, right, bottom = _borders(name)
    w, h = image.width(), image.height()
    xs = [(0, left), (left, w - right), (w - right, w)]
    ys = [(0, top), (top, h - bottom), (h - bottom, h)]
    dxs = [
        (rect.left(), left * scale),
        (rect.left() + left * scale, rect.width() - (left + right) * scale),
        (rect.right() + 1 - right * scale, right * scale),
    ]
    dys = [
        (rect.top(), top * scale),
        (rect.top() + top * scale, rect.height() - (top + bottom) * scale),
        (rect.bottom() + 1 - bottom * scale, bottom * scale),
    ]
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
    for (sy0, sy1), (dy, dh) in zip(ys, dys, strict=True):
        for (sx0, sx1), (dx, dw) in zip(xs, dxs, strict=True):
            if sx1 > sx0 and sy1 > sy0 and dw > 0 and dh > 0:
                painter.drawImage(
                    QRect(dx, dy, dw, dh), image, QRect(sx0, sy0, sx1 - sx0, sy1 - sy0)
                )
    painter.restore()
    return True


@cache
def dirt(shade: float) -> QPixmap | None:
    """One dirt tile (the block texture at the GUI scale) darkened to ``shade``."""
    image = _image("assets/minecraft/textures/block/dirt.png")
    if image is None:
        return None
    tile = image.scaled(
        image.width() * SCALE,
        image.height() * SCALE,
        Qt.AspectRatioMode.IgnoreAspectRatio,
        Qt.TransformationMode.FastTransformation,
    )
    painter = QPainter(tile)
    painter.fillRect(tile.rect(), QColor(0, 0, 0, round(255 * (1 - shade))))
    painter.end()
    return QPixmap.fromImage(tile)


def dirt_brush(shade: float) -> QBrush | None:
    tile = dirt(shade)
    return QBrush(tile) if tile is not None else None


def paint_dirt(widget: QWidget, shade: float = BACKGROUND_SHADE) -> None:
    """Fill ``widget`` with dirt (call from its ``paintEvent``)."""
    brush = dirt_brush(shade)
    if brush is None:
        return
    painter = QPainter(widget)
    painter.fillRect(widget.rect(), brush)
    painter.end()


def _text(painter: QPainter, text: str, rect: QRect, color: str) -> None:
    """``text`` centered in ``rect``, in the pixel font (or the app's font without it)."""
    font = theme.PixelFont.load()
    if font is None:
        painter.setPen(QColor(color))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
        return
    pixmap = font.pixmap(text, color, SCALE)
    # The glyphs' visual middle is 4 font pixels below the room left for accents.
    at = QPoint(
        rect.center().x() + 1 - pixmap.width() // 2,
        rect.center().y() + 1 - (font.TOP + 4) * SCALE,
    )
    painter.drawPixmap(at, pixmap)


class GameButton(QPushButton):
    """A push button drawn like the game's: the stone ``widget/button`` sprite (lighter
    with a white frame under the mouse or with focus, flat when disabled)."""

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setMinimumHeight(20 * SCALE)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)

    def sizeHint(self) -> QSize:
        hint = super().sizeHint()
        return QSize(hint.width(), max(hint.height(), 20 * SCALE))

    def paintEvent(self, event: QPaintEvent) -> None:
        if not available():
            super().paintEvent(event)
            return
        if not self.isEnabled():
            name, color = "widget/button_disabled", BUTTON_TEXT_DISABLED
        elif self.underMouse() or self.hasFocus() or self.isDown():
            name, color = "widget/button_highlighted", BUTTON_TEXT
        else:
            name, color = "widget/button", BUTTON_TEXT
        painter = QPainter(self)
        draw_sprite(painter, name, self.rect())
        _text(painter, self.text(), self.rect(), color)
        painter.end()


class GameTabs(QTabBar):
    """A tab bar drawn like the game's world-creation tabs (``widget/tab`` sprites)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setExpanding(True)
        self.setDrawBase(False)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        self.setMouseTracking(True)

    def tabSizeHint(self, index: int) -> QSize:
        hint = super().tabSizeHint(index)
        return QSize(hint.width(), 24 * SCALE) if available() else hint

    def paintEvent(self, event: QPaintEvent) -> None:
        if not available():
            super().paintEvent(event)
            return
        painter = QPainter(self)
        cursor = self.mapFromGlobal(self.cursor().pos())
        for index in range(self.count()):
            rect = self.tabRect(index)
            hovered = rect.contains(cursor) and self.underMouse()
            name = "widget/tab_selected" if index == self.currentIndex() else "widget/tab"
            draw_sprite(painter, name + ("_highlighted" if hovered else ""), rect)
            color = BUTTON_TEXT if index == self.currentIndex() else BUTTON_TEXT_DISABLED
            _text(painter, self.tabText(index), rect, color)
        painter.end()


#: Style of a search field like the game's (``widget/text_field``: black, a grey frame,
#: white with focus).
TEXT_FIELD_STYLE = (
    "QLineEdit { background: #000000; color: #e0e0e0; border: 2px solid #a0a0a0;"
    " border-radius: 0; padding: 4px 6px; }"
    "QLineEdit:focus { border: 2px solid #ffffff; }"
)
