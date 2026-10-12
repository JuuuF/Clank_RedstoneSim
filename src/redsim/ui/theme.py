"""The look of the editor: Blender's dark, flat panels with a Minecraft soul.

* **Palette:** Blender-like charcoal tones for panels and widgets; redstone red as the
  accent (selection, playhead, checked tools), the game's gold for highlights.
* **Stylesheet** (``STYLESHEET``): one Qt stylesheet for every widget (menus, tool bars,
  docks, tabs, buttons, inputs, lists, scroll bars, tooltips), applied app-wide with the
  Fusion style and a dark ``QPalette``, so all views look like they belong together.
* **Pixel font** (``PixelFont``): the game's own bitmap font (``font/include/default.json``
  providers: ``ascii.png`` and friends, read from the client jar like the block textures),
  drawn with the game's drop shadow, for the viewport overlays, the F3 screen and the
  inventory. Without the jar, a monospace font stands in.
"""

from __future__ import annotations

import atexit
import json
import shutil
import tempfile
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QPoint, QRect, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QImage, QPainter, QPalette, QPixmap
from PySide6.QtWidgets import QApplication, QStyleFactory, QTabWidget

from redsim.ui.assets import Assets

# --------------------------------------------------------------------------- palette
WINDOW = "#1d1d1f"  # outer background, between panels
PANEL = "#26272b"  # docks, bars, the timeline
WIDGET = "#323338"  # buttons, inputs
WIDGET_HOVER = "#3d3e44"
SUNKEN = "#18181a"  # inset fields, inventory slots
BORDER = "#111113"
LINE = "#3a3b41"  # separators, grid lines
TEXT = "#dcdcde"
TEXT_DIM = "#8e8f96"
ACCENT = "#d8382a"  # redstone
ACCENT_SOFT = "#7a2620"
GOLD = "#ffd24a"  # the game's yellow text
GREEN = "#5fbf4a"
BLUE = "#4f8fe0"

FONT_FAMILY = "Inter, 'Noto Sans', 'DejaVu Sans', sans-serif"
MONO_FAMILY = "'JetBrains Mono', 'DejaVu Sans Mono', monospace"

STYLESHEET = f"""
* {{ font-family: {FONT_FAMILY}; font-size: 12px; color: {TEXT}; }}
QMainWindow, QDialog {{ background: {WINDOW}; }}
QWidget {{ background: transparent; }}
QMainWindow > QWidget, QDockWidget > QWidget, QTabWidget::pane, QScrollArea > QWidget > QWidget {{
    background: {PANEL};
}}
QToolTip {{
    background: {SUNKEN}; color: {TEXT}; border: 1px solid {LINE}; padding: 4px 6px;
}}
QMenuBar {{ background: {WINDOW}; padding: 2px; }}
QMenuBar::item {{ padding: 4px 9px; border-radius: 4px; background: transparent; }}
QMenuBar::item:selected {{ background: {WIDGET_HOVER}; }}
QMenu {{ background: {PANEL}; border: 1px solid {BORDER}; padding: 4px; }}
QMenu::item {{ padding: 5px 22px 5px 22px; border-radius: 4px; }}
QMenu::item:selected {{ background: {ACCENT_SOFT}; }}
QMenu::item:disabled {{ color: {TEXT_DIM}; }}
QMenu::separator {{ height: 1px; background: {LINE}; margin: 4px 8px; }}
QMenu::indicator {{ width: 12px; height: 12px; left: 5px; }}
QToolBar {{ background: {WINDOW}; border: none; spacing: 2px; padding: 3px 6px; }}
QToolBar::separator {{ width: 1px; background: {LINE}; margin: 4px 6px; }}
QToolButton, QPushButton {{
    background: {WIDGET}; border: 1px solid {BORDER}; border-radius: 4px; padding: 4px 9px;
}}
QToolButton:hover, QPushButton:hover {{ background: {WIDGET_HOVER}; }}
QToolButton:pressed, QPushButton:pressed {{ background: {SUNKEN}; }}
QToolButton:checked, QPushButton:checked {{
    background: {ACCENT_SOFT}; border: 1px solid {ACCENT};
}}
QToolButton:disabled, QPushButton:disabled {{ color: {TEXT_DIM}; background: {PANEL}; }}
QToolBar QToolButton {{ background: transparent; border: 1px solid transparent; }}
QToolBar QToolButton:hover {{ background: {WIDGET}; border: 1px solid {BORDER}; }}
QToolBar QToolButton:checked {{ background: {ACCENT_SOFT}; border: 1px solid {ACCENT}; }}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QPlainTextEdit, QTextBrowser, QTextEdit {{
    background: {SUNKEN}; border: 1px solid {BORDER}; border-radius: 4px; padding: 3px 6px;
    selection-background-color: {ACCENT_SOFT};
}}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QPlainTextEdit:focus {{
    border: 1px solid {ACCENT};
}}
QComboBox::drop-down {{ border: none; width: 18px; }}
QComboBox QAbstractItemView {{
    background: {PANEL}; border: 1px solid {BORDER}; selection-background-color: {ACCENT_SOFT};
}}
QSpinBox::up-button, QSpinBox::down-button {{
    background: {WIDGET}; border: none; width: 16px; subcontrol-origin: border;
}}
QSpinBox::up-button {{ subcontrol-position: top right; border-top-right-radius: 4px; }}
QSpinBox::down-button {{ subcontrol-position: bottom right; border-bottom-right-radius: 4px; }}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {{ background: {WIDGET_HOVER}; }}

QCheckBox::indicator, QRadioButton::indicator {{
    width: 13px; height: 13px; background: {SUNKEN}; border: 1px solid {LINE};
    border-radius: 3px;
}}
QCheckBox::indicator:checked {{ background: {ACCENT}; border: 1px solid {ACCENT}; }}
QDockWidget {{ titlebar-close-icon: none; }}
QDockWidget::title {{
    background: {WINDOW}; padding: 5px 8px; text-align: left;
}}
QTabWidget::pane {{ border: none; border-top: 1px solid {LINE}; }}
QTabWidget::tab-bar {{ left: 4px; }}
QTabWidget, QTabWidget > QWidget, QTabBar {{ background: {PANEL}; }}
QTabBar {{ qproperty-drawBase: 0; }}
QTabBar::tab {{
    background: transparent; color: {TEXT_DIM}; padding: 6px 12px; border: none;
    border-bottom: 2px solid transparent;
}}
QTabBar::tab:hover {{ color: {TEXT}; }}
QTabBar::tab:selected {{ color: {TEXT}; border-bottom: 2px solid {ACCENT}; }}
QListWidget, QTreeWidget, QTableWidget {{
    background: {SUNKEN}; border: 1px solid {BORDER}; border-radius: 4px;
    alternate-background-color: {PANEL}; gridline-color: {LINE};
}}
QListWidget::item, QTreeWidget::item {{ padding: 3px; border-radius: 3px; }}
QListWidget::item:selected, QTreeWidget::item:selected, QTableWidget::item:selected {{
    background: {ACCENT_SOFT}; color: {TEXT};
}}
QHeaderView::section {{
    background: {PANEL}; border: none; border-bottom: 1px solid {LINE}; padding: 4px;
}}
QScrollBar:vertical, QScrollBar:horizontal {{ background: transparent; border: none; }}
QScrollBar:vertical {{ width: 10px; }}
QScrollBar:horizontal {{ height: 10px; }}
QScrollBar::handle {{
    background: {WIDGET_HOVER}; border-radius: 4px; min-height: 24px; min-width: 24px;
}}
QScrollBar::handle:hover {{ background: {TEXT_DIM}; }}
QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {{
    background: none; border: none; width: 0; height: 0;
}}
QSlider::groove:horizontal {{ height: 4px; background: {SUNKEN}; border-radius: 2px; }}
QSlider::handle:horizontal {{
    width: 12px; margin: -5px 0; background: {TEXT}; border-radius: 6px;
}}
QSlider::sub-page:horizontal {{ background: {ACCENT}; border-radius: 2px; }}
QSplitter::handle, QMainWindow::separator {{ background: {WINDOW}; width: 4px; height: 4px; }}
QStatusBar {{ background: {WINDOW}; }}
QLabel {{ background: transparent; }}
QGroupBox {{ border: 1px solid {LINE}; border-radius: 6px; margin-top: 12px; padding-top: 6px; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 8px; color: {TEXT_DIM}; }}
"""


def apply(app: QApplication) -> None:
    """Dark Fusion palette plus the stylesheet, for the whole application."""
    style = QStyleFactory.create("Fusion")
    if style is not None:
        app.setStyle(style)
    palette = QPalette()
    for role, color in (
        (QPalette.ColorRole.Window, PANEL),
        (QPalette.ColorRole.WindowText, TEXT),
        (QPalette.ColorRole.Base, SUNKEN),
        (QPalette.ColorRole.AlternateBase, PANEL),
        (QPalette.ColorRole.Text, TEXT),
        (QPalette.ColorRole.Button, WIDGET),
        (QPalette.ColorRole.ButtonText, TEXT),
        (QPalette.ColorRole.Highlight, ACCENT),
        (QPalette.ColorRole.HighlightedText, "#ffffff"),
        (QPalette.ColorRole.ToolTipBase, SUNKEN),
        (QPalette.ColorRole.ToolTipText, TEXT),
        (QPalette.ColorRole.PlaceholderText, TEXT_DIM),
        (QPalette.ColorRole.Link, GOLD),
        # Fusion's bevels and frames: dark too, or stray light lines show up (tab bases).
        (QPalette.ColorRole.Light, LINE),
        (QPalette.ColorRole.Midlight, WIDGET_HOVER),
        (QPalette.ColorRole.Mid, WIDGET),
        (QPalette.ColorRole.Dark, BORDER),
        (QPalette.ColorRole.Shadow, "#000000"),
    ):
        palette.setColor(role, QColor(color))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(TEXT_DIM))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(TEXT_DIM))
    app.setPalette(palette)
    app.setStyleSheet(STYLESHEET + _arrow_rules())
    filler = _TabFiller(app)
    app.installEventFilter(filler)


#: Pixel arrows for spin boxes and combo boxes (style sheets need image files).
_ARROW = ("...#...", "..###..", ".#####.", "#######")
_CHECK = ("......#", ".....##", "#...##.", "##.##..", ".###...", "..#....")


def _arrow_rules() -> str:
    """Style sheet rules that draw the pixel arrows, written once per run to a temporary
    folder (Qt style sheets take image paths, not in-memory images)."""
    folder = Path(tempfile.mkdtemp(prefix="redsim-ui-"))  # private, removed at exit
    atexit.register(shutil.rmtree, folder, True)
    paths = {}
    for name, rows, color in (
        ("up", _ARROW, TEXT_DIM),
        ("down", _ARROW[::-1], TEXT_DIM),
        ("check", _CHECK, "#ffffff"),
    ):
        image = QImage(2 * len(rows[0]), 2 * len(rows), QImage.Format.Format_ARGB32)
        image.fill(QColor(0, 0, 0, 0))
        painter = QPainter(image)
        for y, row in enumerate(rows):
            for x, cell in enumerate(row):
                if cell == "#":
                    painter.fillRect(2 * x, 2 * y, 2, 2, QColor(color))
        painter.end()
        path = folder / f"arrow_{name}.png"
        image.save(str(path))
        paths[name] = path.as_posix()
    return f"""
QSpinBox::up-arrow {{ image: url({paths["up"]}); width: 14px; height: 8px; }}
QSpinBox::down-arrow {{ image: url({paths["down"]}); width: 14px; height: 8px; }}
QComboBox::down-arrow {{ image: url({paths["down"]}); width: 14px; height: 8px; }}
QCheckBox::indicator:checked {{ image: url({paths["check"]}); }}
"""


class _TabFiller(QObject):
    """Tab widgets in document mode leave the gaps around their tab bar unpainted (the
    pane is not drawn): every tab widget fills its background with the panel color. On
    show, since the style sheet's polish resets the flag."""

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.Show and isinstance(watched, QTabWidget):
            watched.setAutoFillBackground(True)
        return False


def paint_slot(painter: QPainter, r: QRect, alpha: int = 255) -> None:
    """A Minecraft slot: sunken, with a dark top/left and a light bottom/right bevel."""

    def color(name: str) -> QColor:
        c = QColor(name)
        c.setAlpha(alpha)
        return c

    painter.fillRect(r, color(SUNKEN))
    painter.fillRect(QRect(r.left(), r.top(), r.width(), 2), color("#0b0b0c"))
    painter.fillRect(QRect(r.left(), r.top(), 2, r.height()), color("#0b0b0c"))
    painter.fillRect(QRect(r.left(), r.bottom() - 1, r.width(), 2), color(LINE))
    painter.fillRect(QRect(r.right() - 1, r.top(), 2, r.height()), color(LINE))


# --------------------------------------------------------------------------- pixel font
@dataclass(frozen=True)
class Glyph:
    image: QImage  # white glyph, its cell (height × cell width)
    width: int  # drawn width in font pixels
    height: int  # drawn height in font pixels (the provider's ``height``, default 8)
    ascent: int


class PixelFont:
    """The game's bitmap font: glyphs from the ``bitmap`` providers of
    ``font/include/default.json`` (advance = width + 1, space 4, as in the game)."""

    LINE = 9  # glyph height 8 + 1
    TOP = 3  # room above the line for tall glyphs (accents)

    def __init__(self, assets: Assets) -> None:
        self.glyphs: dict[str, Glyph] = {}
        path = "assets/minecraft/font/include/default.json"
        data = json.loads(assets.file_bytes(path) or b"{}")
        for provider in data.get("providers", []):
            if provider.get("type") != "bitmap":
                continue
            raw = assets.texture_bytes(provider["file"].replace(".png", ""))
            image = QImage.fromData(raw) if raw else QImage()
            if image.isNull():
                continue
            image = image.convertToFormat(QImage.Format.Format_ARGB32)
            rows: list[str] = provider["chars"]
            cell_h = image.height() // len(rows)
            for row, chars in enumerate(rows):
                cell_w = image.width() // max(1, len(chars))
                for col, char in enumerate(chars):
                    if char in self.glyphs or char == "\u0000":
                        continue
                    cell = image.copy(col * cell_w, row * cell_h, cell_w, cell_h)
                    width = 0
                    for x in range(cell_w):
                        if any((cell.pixel(x, y) >> 24) & 0xFF for y in range(cell_h)):
                            width = x + 1
                    height = int(provider.get("height", 8))
                    scale = height / cell_h if cell_h else 1
                    self.glyphs[char] = Glyph(
                        cell, max(1, round(width * scale)), height, int(provider.get("ascent", 7))
                    )
        self._cache: dict[tuple[str, str, int, bool], QPixmap] = {}

    @staticmethod
    @lru_cache(maxsize=1)
    def load() -> PixelFont | None:
        assets = Assets.find()
        if assets is None:
            return None
        font = PixelFont(assets)
        return font if "A" in font.glyphs else None

    def advance(self, char: str) -> int:
        if char == " ":
            return 4
        glyph = self.glyphs.get(char)
        return glyph.width + 1 if glyph is not None else 6

    def width(self, text: str, scale: int = 2) -> int:
        return sum(self.advance(c) for c in text) * scale

    def pixmap(
        self, text: str, color: str = "#ffffff", scale: int = 2, shadow: bool = True
    ) -> QPixmap:
        """``text`` in the pixel font: white glyphs tinted with ``color``, plus the game's
        shadow (the color at 25 % brightness, one font pixel down-right)."""
        key = (text, color, scale, shadow)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        width = self.width(text, 1) + 1
        height = self.TOP + self.LINE + 1
        canvas = QImage(max(1, width), height, QImage.Format.Format_ARGB32_Premultiplied)
        canvas.fill(Qt.GlobalColor.transparent)
        painter = QPainter(canvas)
        x = 0
        fallback = QFont("DejaVu Sans", 7)
        for char in text:
            glyph = self.glyphs.get(char)
            if glyph is not None:
                cell_w = round(glyph.image.width() * glyph.height / glyph.image.height())
                top = self.TOP + 7 - glyph.ascent
                painter.drawImage(QRect(x, top, cell_w, glyph.height), glyph.image)
            elif char != " ":
                painter.setFont(fallback)
                painter.setPen(QColor("#ffffff"))
                painter.drawText(QPoint(x, self.TOP + 7), char)
            x += self.advance(char)
        painter.end()
        tinted = _tint(canvas, QColor(color))
        out = QImage(
            (width + 1) * scale, (height + 1) * scale, QImage.Format.Format_ARGB32_Premultiplied
        )
        out.fill(Qt.GlobalColor.transparent)
        painter = QPainter(out)
        if shadow:
            dark = QColor(color)
            dark = QColor(dark.red() // 4, dark.green() // 4, dark.blue() // 4)
            painter.drawImage(
                QRect(scale, scale, canvas.width() * scale, canvas.height() * scale),
                _tint(canvas, dark),
            )
        painter.drawImage(QRect(0, 0, canvas.width() * scale, canvas.height() * scale), tinted)
        painter.end()
        pixmap = QPixmap.fromImage(out)
        self._cache[key] = pixmap
        return pixmap


def _tint(image: QImage, color: QColor) -> QImage:
    result = QImage(image.size(), QImage.Format.Format_ARGB32_Premultiplied)
    result.fill(color)
    painter = QPainter(result)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
    painter.drawImage(0, 0, image)
    painter.end()
    return result


def draw_text(
    painter: QPainter,
    x: int,
    y: int,
    text: str,
    color: str = "#ffffff",
    scale: int = 2,
    shadow: bool = True,
) -> int:
    """Draw ``text`` with its top-left at (x, y): the pixel font if available, else a
    monospace font. Returns the drawn width."""
    font = PixelFont.load()
    if font is not None:
        pixmap = font.pixmap(text, color, scale, shadow)
        painter.drawPixmap(x, y - PixelFont.TOP * scale, pixmap)
        return font.width(text, scale)
    qfont = QFont("DejaVu Sans Mono", 5 * scale)
    painter.setFont(qfont)
    metrics = QFontMetrics(qfont)
    if shadow:
        painter.setPen(QColor(0, 0, 0, 180))
        painter.drawText(x + scale, y + scale + metrics.ascent(), text)
    painter.setPen(QColor(color))
    painter.drawText(x, y + metrics.ascent(), text)
    return metrics.horizontalAdvance(text)


def text_width(text: str, scale: int = 2) -> int:
    font = PixelFont.load()
    if font is not None:
        return font.width(text, scale)
    return QFontMetrics(QFont("DejaVu Sans Mono", 5 * scale)).horizontalAdvance(text)


def line_height(scale: int = 2) -> int:
    return PixelFont.LINE * scale if PixelFont.load() is not None else 7 * scale + 4
