"""Constants and small helpers shared by the viewport's modules (colors, timings, mode
names, layer grid, game textures)."""

from __future__ import annotations

import math
from functools import lru_cache

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import (
    QColor,
    QWheelEvent,
)

from redsim.core.pos import Pos
from redsim.editor.clipboard import Region
from redsim.ui import theme
from redsim.ui.assets import Assets
from redsim.ui.atlas import Atlas
from redsim.ui.selection_tools import (
    Handle,
)

BACKGROUND = (0.53, 0.70, 0.86, 1.0)


MOVING_KEY = ("moving",)  # the renderer's mesh slot for moving pistons


FRAME_INTERVAL_MS = 16  # ~60 frames per second while something moves


BLOCKED_TINT = (1.0, 0.22, 0.22)  # a preview that cannot be placed: red


SIGN_TEXT_DISTANCE = 16.0  # blocks: sign text shows (and fades out) within this


ORBIT_DEGREES_PER_PIXEL = 0.3


#: Blocks the cursor reaches beyond twice the camera's distance to the pivot (pointing,
#: F to focus): the old fixed 96 blocks left far-out views unable to point at anything.
PICK_REACH = 96.0


#: The camera's field of view fits a viewport this share of the screen's height. The view
#: keeps its scale when the viewport is resized: a narrower or a lower viewport shows less
#: at that side instead of squeezing more in (owner, 2026-10-14).
FOV_SCREEN_SHARE = 0.7


#: Trackpad scrolling: pixels of finger travel per zoom notch and per block up/down.
TRACKPAD_PIXELS_PER_NOTCH = 40.0


TRACKPAD_PIXELS_PER_BLOCK = 30.0


ZOOM_PER_NOTCH = 1.15


DRAG_THRESHOLD = 4


#: The build preview is this much smaller than a block (no z-fighting with neighbors).
GHOST_SHRINK = 0.99


#: Longest line placed by one drag.
MAX_LINE = 64


DOUBLE_SHIFT_SECONDS = 0.35


#: Time constant of the smooth camera (seconds to cover ~63 % of the way).
GLIDE_SECONDS = 0.07


PIVOT_COLOR = (0.92, 0.92, 0.88, 0.85)  # round 9: a quiet helper, not a neon marker


#: The selection's fill: opacity, how far it breathes, and one breath in seconds.
BODY_ALPHA = 0.2


LOCATE_COLOR = (1.0, 0.9, 0.55, 0.55)  # hovered coordinates: a soft frame
#: The signal heat view's colors at strength 1 and 15 (RGB; in between: linear).
HEAT_LOW = np.array([0.45, 0.04, 0.04])
HEAT_HIGH = np.array([1.0, 0.92, 0.25])


HIGHLIGHT_SECONDS = 3.0  # how long a flashed block (Diagnostics click) stays lit


BODY_MARGIN = 0.02  # blocks the fill box stands out of its contents (no z-fighting)


BODY_PULSE = 0.06


PULSE_SECONDS = 1.8


SELECTION_COLOR = (0.0, 0.85, 0.95, 1.0)


LOCKED_COLOR = (1.0, 0.62, 0.15, 1.0)


EXTRA_SELECTION_COLOR = (0.35, 0.65, 0.95, 0.8)  # further selections (Shift+drag): calmer


TARGET_COLOR = (1.0, 1.0, 1.0, 1.0)


#: Blocks a pending move would overwrite (owner: moves "possibly destroy other blocks").
REPLACED_COLOR = (1.0, 0.18, 0.12, 0.38)


#: One breath of the preview of pending blocks (a move, turn, copy, stack or paste).
PENDING_PULSE_SECONDS = 1.4


NORMAL, BUILD, SELECT, ANIMATE = "normal", "build", "select", "animate"


#: The Tab ring: the modes around the cursor, clockwise from the top.
RING_MODES = (NORMAL, BUILD, SELECT, ANIMATE)


RING_RADIUS = 70  # pixels from the center to a mode's label


RING_DEAD_ZONE = 18  # pixels: closer to the center chooses nothing


INFO_LABEL_LIMIT = 300


INFO_COLORS = {
    "wire": QColor(170, 20, 20, 210),
    "source": QColor(120, 60, 160, 220),
    "comparator": QColor(40, 40, 40, 220),
}


PASTE_COLOR = QColor(140, 60, 170)


MODE_COLORS = {
    NORMAL: QColor(60, 100, 160),
    BUILD: QColor(50, 140, 60),
    SELECT: QColor(200, 115, 25),
    ANIMATE: QColor(185, 45, 60),
}


#: Short verbs for the mode badge.
CLICK_VERBS = {
    "normal.inspect": "inspect",
    "normal.use": "use",
    "build.place": "place",
    "build.line": "line",
    "build.rotate": "turn",
    "build.break": "break",
    "select.block": "select",
    "select.box": "box / move / resize",
    "select.copy_drag": "copy",
    "select.stack": "stack",
    "select.extend": "extend",
    "animate.pulse": "power from this tick",
    "animate.remove": "remove pulse",
    "pick": "pick",
}


_BUTTON_NAMES = {
    Qt.MouseButton.LeftButton: "Left",
    Qt.MouseButton.RightButton: "Right",
    Qt.MouseButton.MiddleButton: "Middle",
}


def _from_trackpad(event: QWheelEvent) -> bool:
    """Scrolling with fingers (it has scroll phases or pixel deltas), not a wheel."""
    return event.phase() != Qt.ScrollPhase.NoScrollPhase or not event.pixelDelta().isNull()


def _modifier_names(modifiers: Qt.KeyboardModifier) -> frozenset[str]:
    names = set()
    if modifiers & Qt.KeyboardModifier.ControlModifier:
        names.add("Ctrl")
    if modifiers & Qt.KeyboardModifier.ShiftModifier:
        names.add("Shift")
    if modifiers & Qt.KeyboardModifier.AltModifier:
        names.add("Alt")
    if modifiers & Qt.KeyboardModifier.MetaModifier:
        names.add("Meta")
    return frozenset(names)


@lru_cache(maxsize=1)
def game_textures() -> tuple[Assets | None, Atlas | None]:
    """The game's block models and a texture atlas, if the client jar is available."""
    assets = Assets.find()
    if assets is None:
        return None, None
    return assets, Atlas.for_blocks(assets)


#: The layer grid around a build target or paste: reach (blocks) and strongest alpha.
GRID_REACH = 5


GRID_ALPHA = 0.8


def _layer_grid(box: Region) -> np.ndarray:
    """Grid lines on the working plane around ``box``, in one-block segments that fade
    out with the distance to the box, so the grid reads as a height guide and not as
    outlines of the blocks below it."""
    y = box.low[1] + 0.01  # just above the layer's floor: no z-fighting with block tops
    lo_x, hi_x = box.low[0], box.high[0] + 1
    lo_z, hi_z = box.low[2], box.high[2] + 1

    def alpha(x: float, z: float) -> float:
        dx = max(lo_x - x, 0.0, x - hi_x)
        dz = max(lo_z - z, 0.0, z - hi_z)
        fade = max(0.0, 1.0 - math.hypot(dx, dz) / GRID_REACH)
        return GRID_ALPHA * fade

    xs = range(lo_x - GRID_REACH, hi_x + GRID_REACH + 1)
    zs = range(lo_z - GRID_REACH, hi_z + GRID_REACH + 1)
    segments = [((x, z), (x, z + 1)) for x in xs for z in zs[:-1]]  # lines along z
    segments += [((x, z), (x + 1, z)) for z in zs for x in xs[:-1]]  # lines along x
    rows = []
    for p, q in segments:
        ap, aq = alpha(*p), alpha(*q)
        if ap > 0.0 or aq > 0.0:
            rows += [(p[0], y, p[1], 1.0, 1.0, 1.0, ap), (q[0], y, q[1], 1.0, 1.0, 1.0, aq)]
    return np.array(rows, dtype=np.float32).reshape(-1, 7)


_HANDLES = tuple(Handle(axis, high) for axis in range(3) for high in (False, True))


def _elide(text: str, room: int) -> str:
    """Cut ``text`` (pixel font) to ``room`` pixels with an ellipsis."""
    if theme.text_width(text) <= room:
        return text
    while text and theme.text_width(text + "…") > room:
        text = text[:-1]
    return text + "…"


def _ghost_key(ghost: tuple[np.ndarray, Pos] | None) -> tuple[int, Pos] | None:
    """Compare ghosts by mesh identity and place (comparing arrays would be elementwise)."""
    return None if ghost is None else (id(ghost[0]), ghost[1])


def _bounds(region: Region) -> tuple[np.ndarray, np.ndarray]:
    low, high = region.low, region.high
    return np.array(low, dtype=float), np.array(high, dtype=float) + 1.0


def _hex_color(text: str) -> tuple[float, float, float, float]:
    text = text.lstrip("#")
    return (int(text[0:2], 16) / 255, int(text[2:4], 16) / 255, int(text[4:6], 16) / 255, 1.0)
