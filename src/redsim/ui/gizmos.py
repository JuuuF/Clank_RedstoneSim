"""Blender-like selection gizmos: geometry and hot spots (pure numpy, no Qt).

The selection gets three kinds of gizmos, sized by the camera distance (``unit``):

* resize arrows, one per face, colored by axis like Blender (X red, Y green, Z blue); with
  Shift held they turn into stacking chevrons (drag outwards to stack copies);
* a rotate ring around the box with two arrowheads (clockwise, counter-clockwise) on the
  side facing the camera;
* flip arrows: two double-headed arrows across the top face (X and Z).

Each gizmo has hot spots (sphere around a point) for picking. Vertices are
``x, y, z, r, g, b, a`` triangles, like the rest of the renderer.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np

from redsim.editor.clipboard import Region
from redsim.ui.selection_tools import HANDLES, Handle, bounds, face_center

Color = tuple[float, float, float, float]
AXIS_COLORS: tuple[Color, Color, Color] = (
    (0.92, 0.30, 0.30, 1.0),
    (0.45, 0.82, 0.30, 1.0),
    (0.30, 0.55, 0.98, 1.0),
)
HOVER_COLOR: Color = (1.0, 0.92, 0.35, 1.0)
STACK_COLOR: Color = (0.98, 0.98, 0.98, 1.0)
RING_COLOR: Color = (0.95, 0.80, 0.30, 1.0)
FLIP_COLOR: Color = (0.95, 0.95, 0.95, 1.0)
#: Gizmo outlines: dark, a little thicker than the gizmos (drawn behind them).
OUTLINE_COLOR = (0.05, 0.05, 0.07, 1.0)
OUTLINE_MARGIN = 0.09


@dataclass(frozen=True)
class Hotspot:
    kind: str  # "resize" | "rotate" | "flip"
    data: Any  # Handle | +1/-1 quarter turns | "x"/"z"
    center: tuple[float, float, float]
    radius: float


def _tri(points: list[np.ndarray], color: Color) -> np.ndarray:
    return np.array([(*p, *color) for p in points], dtype=np.float32)


def _bases(axes: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Two unit vectors across each of the (n, 3) ``axes``."""
    axes = axes / np.linalg.norm(axes, axis=1, keepdims=True)
    helpers = np.where(
        np.abs(axes[:, 1:2]) < 0.9, np.array([0.0, 1.0, 0.0]), np.array([1.0, 0.0, 0.0])
    )
    u = np.cross(axes, helpers)
    u /= np.linalg.norm(u, axis=1, keepdims=True)
    return u, np.cross(axes, u)


def _rims(axes: np.ndarray, radii: np.ndarray, sides: int) -> tuple[np.ndarray, np.ndarray]:
    """Offsets of the start and end of each of a circle's ``sides`` around each axis, at
    each radius: (n, sides, 3) twice."""
    u, v = _bases(axes)
    angles = 2 * math.pi * np.arange(sides + 1) / sides
    cos, sin = np.cos(angles)[None, :, None], np.sin(angles)[None, :, None]
    ring = (u[:, None, :] * cos + v[:, None, :] * sin) * radii[:, None, None]
    return ring[:, :-1], ring[:, 1:]


def _colored(points: np.ndarray, colors: np.ndarray) -> np.ndarray:
    """(n, k, 3) points, (n, 4) colors → (n k, 7) vertices."""
    n, k = points.shape[:2]
    rgba = np.broadcast_to(colors[:, None, :], (n, k, 4))
    return np.concatenate([points, rgba], axis=2).reshape(-1, 7).astype(np.float32)


class Shapes:
    """Tubes and cones collected first and built together, a few numpy calls for all of
    them (a selection's gizmos are rebuilt whenever the camera turns or zooms)."""

    def __init__(self) -> None:
        self.tubes: dict[int, list[tuple[Any, ...]]] = {}
        self.cones: list[tuple[Any, ...]] = []

    def tube(
        self, a: np.ndarray, b: np.ndarray, radius: float, color: Color, sides: int = 8
    ) -> None:
        self.tubes.setdefault(sides, []).append((a, b, radius, color))

    def tubes_along(self, points: np.ndarray, radius: float, color: Color, sides: int = 8) -> None:
        """Tubes from each point to the next."""
        for a, b in zip(points[:-1], points[1:], strict=True):
            self.tube(a, b, radius, color, sides)

    def cone(self, base: np.ndarray, tip: np.ndarray, radius: float, color: Color) -> None:
        self.cones.append((base, tip, radius, color))

    def build(self) -> np.ndarray:
        parts = []
        for sides, rows in self.tubes.items():
            a, b, radii, colors = (
                np.array(column, dtype=float) for column in zip(*rows, strict=True)
            )
            o0, o1 = _rims(b - a, radii, sides)
            start, end = a[:, None, None, :], b[:, None, None, :]
            o0, o1 = o0[:, :, None, :], o1[:, :, None, :]
            tris = np.concatenate(
                [start + o0, end + o0, end + o1, start + o0, end + o1, start + o1], axis=2
            )
            parts.append(_colored(tris.reshape(len(a), -1, 3), colors))
        if self.cones:
            base, tip, radii, colors = (
                np.array(column, dtype=float) for column in zip(*self.cones, strict=True)
            )
            o0, o1 = _rims(tip - base, radii, CONE_SIDES)
            p0, p1 = base[:, None, :] + o0, base[:, None, :] + o1
            tips = np.broadcast_to(tip[:, None, :], p0.shape)
            bases = np.broadcast_to(base[:, None, :], p0.shape)
            tris = np.stack([p0, p1, tips, p1, p0, bases], axis=2)
            parts.append(_colored(tris.reshape(len(base), -1, 3), colors))
        return np.vstack(parts) if parts else np.zeros((0, 7), dtype=np.float32)


CONE_SIDES = 12


def arrow(
    shapes: Shapes,
    start: np.ndarray,
    direction: np.ndarray,
    length: float,
    unit: float,
    color: Color,
) -> None:
    """A shaft with a cone head, ``length`` long from ``start`` along ``direction``."""
    direction = direction / np.linalg.norm(direction)
    head = 1.3 * unit
    neck = start + direction * max(length - head, 0.0)
    shapes.tube(start, neck, 0.16 * unit, color)
    shapes.cone(neck, start + direction * length, 0.5 * unit, color)


def arrow_outline(
    shapes: Shapes, start: np.ndarray, direction: np.ndarray, length: float, unit: float
) -> None:
    """A slightly bigger dark arrow, drawn behind ``arrow`` as its outline (round 8)."""
    direction = direction / np.linalg.norm(direction)
    m = OUTLINE_MARGIN * unit
    head = 1.3 * unit
    neck = start + direction * max(length - head, 0.0)
    shapes.tube(start - direction * m, neck, 0.16 * unit + m, OUTLINE_COLOR)
    shapes.cone(
        neck - direction * m,
        start + direction * (length + 2 * m),
        0.5 * unit + 1.6 * m,
        OUTLINE_COLOR,
    )


def chevrons(
    shapes: Shapes, start: np.ndarray, direction: np.ndarray, unit: float, color: Color
) -> None:
    """Three flat cones in a row: the stacking look of a resize arrow."""
    direction = direction / np.linalg.norm(direction)
    shapes.tube(start, start + direction * 1.2 * unit, 0.12 * unit, color)
    for i in range(3):
        base = start + direction * (1.2 + i * 0.9) * unit
        shapes.cone(base, base + direction * 0.9 * unit, 0.55 * unit, color)


def box_faces(lo: np.ndarray, hi: np.ndarray, color: Color) -> np.ndarray:
    """A closed box (12 triangles) for translucent bodies."""
    x0, y0, z0 = lo
    x1, y1, z1 = hi
    quads = [
        [(x0, y1, z0), (x0, y1, z1), (x1, y1, z1), (x1, y1, z0)],
        [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)],
        [(x0, y0, z0), (x0, y1, z0), (x1, y1, z0), (x1, y0, z0)],
        [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)],
        [(x0, y0, z0), (x0, y0, z1), (x0, y1, z1), (x0, y1, z0)],
        [(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)],
    ]
    rows = [np.array(q[i]) for q in quads for i in (0, 1, 2, 0, 2, 3)]
    return _tri(rows, color)


#: Corner indices (bit 0: x, bit 1: y, bit 2: z of the high corner) of a box's 12
#: triangles, in ``box_faces``' order.
_BOX_CORNERS = np.array(
    [
        c
        for quad in (
            (2, 6, 7, 3),
            (0, 1, 5, 4),
            (0, 2, 3, 1),
            (4, 5, 7, 6),
            (0, 4, 6, 2),
            (1, 3, 7, 5),
        )  # fmt: skip
        for c in (quad[0], quad[1], quad[2], quad[0], quad[2], quad[3])
    ]
)


def many_box_faces(lows: np.ndarray, highs: np.ndarray, colors: np.ndarray) -> np.ndarray:
    """``box_faces`` for many boxes at once: (n, 3) corners and (n, 4) colors → (36 n, 7)."""
    if not len(lows):
        return np.zeros((0, 7), dtype=np.float32)
    bits = np.array([[(c >> 0) & 1, (c >> 1) & 1, (c >> 2) & 1] for c in _BOX_CORNERS])
    points = lows[:, None, :] + bits[None, :, :] * (highs - lows)[:, None, :]
    rows = np.concatenate(
        [points, np.broadcast_to(colors[:, None, :], (len(lows), len(bits), 4))], axis=2
    )
    return rows.reshape(-1, 7).astype(np.float32)


def selection_gizmos(
    region: Region,
    unit: float,
    camera_yaw: float,
    stacking: bool,
    hover: Hotspot | None,
    outlines: list[np.ndarray] | None = None,
    handles: bool = True,
    flips: bool = True,
) -> tuple[np.ndarray, list[Hotspot]]:
    """All gizmos of a selection: triangles and their hot spots. ``outlines``, if given,
    collects dark outline shapes for the arrows, ring and arrowheads. ``handles``: the
    face arrows (or chevrons), ``flips``: the flip arrows."""
    parts, shells = Shapes(), Shapes()
    m = OUTLINE_MARGIN * unit
    lo, hi = bounds(region)
    center = (lo + hi) / 2
    spots: list[Hotspot] = []

    def is_hovered(kind: str, data: Any) -> bool:
        return hover is not None and hover.kind == kind and hover.data == data

    for handle in HANDLES if handles else ():
        start = face_center(region, handle) + handle.normal * 0.15 * unit
        hovered = is_hovered("resize", handle)
        if stacking:
            color = HOVER_COLOR if hovered else STACK_COLOR
            chevrons(parts, start, handle.normal, unit, color)
        else:
            color = HOVER_COLOR if hovered else AXIS_COLORS[handle.axis]
            arrow(parts, start, handle.normal, 4.2 * unit, unit, color)
            arrow_outline(shells, start, handle.normal, 4.2 * unit, unit)
        tip = start + handle.normal * 3.4 * unit
        spots.append(Hotspot("resize", handle, tuple(tip), 1.2 * unit))

    # Rotate ring around the box at its top, arrowheads on the side facing the camera.
    radius = 0.5 * math.hypot(hi[0] - lo[0], hi[2] - lo[2]) + 1.5 * unit
    y = hi[1] + 0.05
    segments = 64
    angles = 2 * math.pi * np.arange(segments + 1) / segments
    points = np.stack(
        [
            center[0] + radius * np.cos(angles),
            np.full(segments + 1, y),
            center[2] + radius * np.sin(angles),
        ],
        axis=1,
    )
    parts.tubes_along(points, 0.1 * unit, RING_COLOR, sides=6)
    shells.tubes_along(points, 0.1 * unit + m, OUTLINE_COLOR, sides=6)
    # Direction from the box towards the camera (yaw 0 looks south, so the camera is north).
    yaw = math.radians(camera_yaw)
    toward = math.atan2(-math.cos(yaw), math.sin(yaw))  # angle in the x/z plane
    for turns, offset in ((1, -0.45), (-1, 0.45)):
        angle = toward + offset
        point = np.array(
            [center[0] + radius * math.cos(angle), y, center[2] + radius * math.sin(angle)]
        )
        # Clockwise seen from above is increasing angle in x/z (x east, z south).
        tangent = np.array([-math.sin(angle), 0.0, math.cos(angle)]) * (1 if turns == 1 else -1)
        hovered = is_hovered("rotate", turns)
        color = HOVER_COLOR if hovered else RING_COLOR
        parts.cone(point - tangent * 0.7 * unit, point + tangent * 1.1 * unit, 0.6 * unit, color)
        shells.cone(
            point - tangent * (0.7 * unit + m),
            point + tangent * (1.1 * unit + 2 * m),
            0.6 * unit + 1.6 * m,
            OUTLINE_COLOR,
        )
        spots.append(Hotspot("rotate", turns, tuple(point), 1.3 * unit))

    # Flip arrows: double-headed, across the top face.
    top = np.array([center[0], hi[1] + 0.1, center[2]])
    for axis, index in (("x", 0), ("z", 2)) if flips else ():
        span = max(0.5 * (hi[index] - lo[index]) - 0.6 * unit, 1.2 * unit)
        direction = np.zeros(3)
        direction[index] = 1.0
        hovered = is_hovered("flip", axis)
        tint = AXIS_COLORS[index]
        color = (
            HOVER_COLOR
            if hovered
            else (
                (FLIP_COLOR[0] + tint[0]) / 2,
                (FLIP_COLOR[1] + tint[1]) / 2,
                (FLIP_COLOR[2] + tint[2]) / 2,
                1.0,
            )
        )
        for sign in (1, -1):
            arrow(parts, top, direction * sign, span, 0.8 * unit, color)
            arrow_outline(shells, top, direction * sign, span, 0.8 * unit)
            end = top + direction * sign * span
            spots.append(Hotspot("flip", axis, tuple(end), 1.1 * unit))
    if outlines is not None:
        outlines.append(shells.build())
    return parts.build(), spots


def pick_hotspot(origin: np.ndarray, direction: np.ndarray, spots: list[Hotspot]) -> Hotspot | None:
    """The nearest hot spot the ray passes within its radius."""
    unit = direction / np.linalg.norm(direction)
    best: tuple[float, Hotspot] | None = None
    for spot in spots:
        to = np.array(spot.center) - origin
        t = float(to @ unit)
        if t <= 0:
            continue
        if float(np.linalg.norm(to - unit * t)) <= spot.radius and (best is None or t < best[0]):
            best = (t, spot)
    return best[1] if best else None


__all__ = ["Handle", "Hotspot", "box_faces", "pick_hotspot", "selection_gizmos"]
