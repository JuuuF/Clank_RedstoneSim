"""Blender-like status bar: the essential actions for what you are doing right now.

``context_hints`` is pure (testable without a display); keys come from the keymap, so a
rebinding shows up here too. ``HintBar`` draws them as keycaps on the left and status
messages on the right.
"""

from __future__ import annotations

import html
from dataclasses import dataclass

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QWidget

from redsim.ui import pixel_icons, theme
from redsim.ui.keymap import Keymap


@dataclass(frozen=True)
class Context:
    mode: str
    has_region: bool = False
    locked: bool = False
    pasting: bool = False
    shift: bool = False
    gizmo: str | None = None  # "resize" | "rotate" | "flip" under the cursor
    running: bool = False


def context_hints(keymap: Keymap, context: Context) -> list[tuple[str, str]]:
    """(keys, what they do) pairs, most important first."""

    def key(action: str) -> str:
        bindings = keymap.bindings(action)
        return bindings[0] if bindings else "—"

    if context.pasting:
        return [
            ("Left Click", "place"),
            (key("paste.layer"), "layer up/down"),
            (key("edit.rotate"), "rotate"),
            (key("edit.flip"), "flip"),
            ("Right Click / Esc", "cancel"),
        ]
    if context.gizmo == "resize":
        if context.shift:
            return [("Shift+Drag", "stack copies along this axis"), ("release Shift", "resize")]
        return [("Drag", "move this face"), ("Shift+Drag", "stack copies")]
    if context.gizmo == "rotate":
        return [("Click", "rotate 90° this way"), (key("edit.rotate"), "rotate clockwise")]
    if context.gizmo == "flip":
        return [("Click", "flip along this axis"), (key("edit.flip"), "flip left/right")]
    run = (key("sim.run"), "pause" if context.running else "run")
    step = (f"{key('sim.tick_back')}/{key('sim.tick')}", "tick back/forward")
    if context.mode == "build":
        return [
            (key("build.place"), "place"),
            (key("build.line"), "line"),
            (key("build.layer"), "layer up/down"),
            (key("build.break"), "remove"),
            (key("edit.rotate_block"), "turn"),
            ("Middle Click", "pick"),
            ("1-9", "inventory"),
            (key("search.blocks").split(" / ")[0], "search"),
            run,
            (key("mode.select"), "select mode"),
        ]
    if context.mode == "select":
        if not context.has_region:
            return [
                ("Left Drag", "draw a box"),
                ("Left Click", "select a block"),
                ("Shift+Click", "extend"),
                (key("edit.paste"), "paste"),
                (key("mode.normal"), "normal mode"),
            ]
        if context.shift:
            return [("Shift+Drag an arrow", "stack copies"), ("Shift+Click", "extend the box")]
        hints = [
            ("Drag inside", "move"),
            ("Ctrl+Drag", "copy"),
            ("Drag an arrow", "resize"),
            (key("edit.rotate"), "rotate"),
            (key("edit.flip"), "flip"),
            (key("edit.copy"), "copy"),
            (key("edit.delete"), "delete"),
        ]
        lock = "unlock" if context.locked else "lock"
        hints.append((key("select.lock"), lock))
        return hints
    return [
        ("Left Click", "inspect"),
        ("Right Click", "use"),
        run,
        step,
        (key("mode.build"), "build"),
        (key("mode.select"), "select"),
        ("Middle Drag", "orbit"),
        ("F1", "all hotkeys"),
    ]


#: Mouse gestures drawn with a pixel mouse (Blender's status bar does the same): the
#: icon, and the word shown next to it (none for a plain click).
MOUSE_GESTURES = {
    "Left Click": ("mouse_left", ""),
    "Left Drag": ("mouse_left", "drag"),
    "Right Click": ("mouse_right", ""),
    "Right Drag": ("mouse_right", "drag"),
    "Middle Click": ("mouse_middle", ""),
    "Middle Drag": ("mouse_middle", "drag"),
    "Wheel": ("mouse_middle", "wheel"),
}


def _keycap(token: str) -> str:
    cap = (
        f'<span style="background-color:{theme.WIDGET_HOVER}; color:{theme.TEXT};">'
        "&nbsp;{}&nbsp;</span>"
    )
    gesture = MOUSE_GESTURES.get(token)
    if gesture is None:
        return cap.format(html.escape(token))
    icon, word = gesture
    image = f'<img src="{pixel_icons.pixel_data_uri(icon)}" align="middle">'
    return cap.format(f"{image}{'&nbsp;' + word if word else ''}")


def keycaps_html(keys: str) -> str:
    """``keys`` ("Shift+Middle Drag", "Right Click / Esc") as keycaps; mouse gestures as a
    small pixel mouse."""
    alternatives = []
    for alternative in keys.split(" / "):
        parts = alternative.split("+")
        alternatives.append("+".join(_keycap(part) if part else "" for part in parts))
    return " / ".join(alternatives)


#: Fits a pixel mouse keycap (20 px art) with its padding.
HINT_BAR_HEIGHT = 30


class HintBar(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 1, 6, 1)
        # One height in every mode: hints with mouse icons are taller than plain keys, and
        # a growing bar would resize the views above it.
        self.setFixedHeight(HINT_BAR_HEIGHT)
        self.hints = QLabel()
        self.hints.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        layout.addWidget(self.hints, 3)
        self.hover = QLabel()
        self.hover.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.hover.setStyleSheet(f"color: {theme.TEXT_DIM};")
        layout.addWidget(self.hover, 1)
        self.message = QLabel()
        layout.addWidget(self.message)
        self._clear = QTimer(self)
        self._clear.setSingleShot(True)
        self._clear.timeout.connect(lambda: self.message.setText(""))
        self._shown: list[tuple[str, str]] = []

    def show_hints(self, hints: list[tuple[str, str]]) -> None:
        if hints == self._shown:
            return
        self._shown = hints
        parts = [f"{keycaps_html(keys)}&nbsp;{html.escape(text)}" for keys, text in hints]
        self.hints.setText("&nbsp;&nbsp;&nbsp;".join(parts))

    def show_hover(self, text: str) -> None:
        self.hover.setText(text)

    def show_message(self, text: str, error: bool = False) -> None:
        color = theme.ACCENT if error else theme.GOLD
        self.message.setText(f'<span style="color:{color};">{html.escape(text)}</span>')
        self._clear.start(6000 if error else 3500)
