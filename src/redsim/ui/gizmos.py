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
BODY_ALPHA = 0.08


@dataclass(frozen=True)
class Hotspot:
    kind: str  # "resize" | "rotate" | "flip"
    data: Any  # Handle | +1/-1 quarter turns | "x"/"z"
    center: tuple[float, float, float]
    radius: float


def _tri(points: list[np.ndarray], color: Color) -> np.ndarray:
    return np.array([(*p, *color) for p in points], dtype=np.float32)


def _basis(axis: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    axis = axis / np.linalg.norm(axis)
    helper = np.array([0.0, 1.0, 0.0]) if abs(axis[1]) < 0.9 else np.array([1.0, 0.0, 0.0])
    u = np.cross(axis, helper)
    u /= np.linalg.norm(u)
    return u, np.cross(axis, u)


def cylinder(
    a: np.ndarray, b: np.ndarray, radius: float, color: Color, sides: int = 8
) -> np.ndarray:
    u, v = _basis(b - a)
    rows: list[np.ndarray] = []
    for i in range(sides):
        t0, t1 = 2 * math.pi * i / sides, 2 * math.pi * (i + 1) / sides
        o0 = (u * math.cos(t0) + v * math.sin(t0)) * radius
        o1 = (u * math.cos(t1) + v * math.sin(t1)) * radius
        rows += [a + o0, b + o0, b + o1, a + o0, b + o1, a + o1]
    return _tri(rows, color)


def cone(
    base: np.ndarray, tip: np.ndarray, radius: float, color: Color, sides: int = 12
) -> np.ndarray:
    u, v = _basis(tip - base)
    rows: list[np.ndarray] = []
    for i in range(sides):
        t0, t1 = 2 * math.pi * i / sides, 2 * math.pi * (i + 1) / sides
        p0 = base + (u * math.cos(t0) + v * math.sin(t0)) * radius
        p1 = base + (u * math.cos(t1) + v * math.sin(t1)) * radius
        rows += [p0, p1, tip, p1, p0, base]
    return _tri(rows, color)


def arrow(
    start: np.ndarray, direction: np.ndarray, length: float, unit: float, color: Color
) -> np.ndarray:
    """A shaft with a cone head, ``length`` long from ``start`` along ``direction``."""
    direction = direction / np.linalg.norm(direction)
    head = 1.3 * unit
    neck = start + direction * max(length - head, 0.0)
    return np.vstack(
        [
            cylinder(start, neck, 0.16 * unit, color),
            cone(neck, start + direction * length, 0.5 * unit, color),
        ]
    )


def chevrons(start: np.ndarray, direction: np.ndarray, unit: float, color: Color) -> np.ndarray:
    """Three flat cones in a row: the stacking look of a resize arrow."""
    direction = direction / np.linalg.norm(direction)
    parts = [cylinder(start, start + direction * 1.2 * unit, 0.12 * unit, color)]
    for i in range(3):
        base = start + direction * (1.2 + i * 0.9) * unit
        parts.append(cone(base, base + direction * 0.9 * unit, 0.55 * unit, color))
    return np.vstack(parts)


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


def selection_gizmos(
    region: Region, unit: float, camera_yaw: float, stacking: bool, hover: Hotspot | None
) -> tuple[np.ndarray, list[Hotspot]]:
    """All gizmos of a selection: triangles and their hot spots."""
    lo, hi = bounds(region)
    center = (lo + hi) / 2
    parts: list[np.ndarray] = []
    spots: list[Hotspot] = []

    def is_hovered(kind: str, data: Any) -> bool:
        return hover is not None and hover.kind == kind and hover.data == data

    for handle in HANDLES:
        start = face_center(region, handle) + handle.normal * 0.15 * unit
        hovered = is_hovered("resize", handle)
        if stacking:
            color = HOVER_COLOR if hovered else STACK_COLOR
            parts.append(chevrons(start, handle.normal, unit, color))
        else:
            color = HOVER_COLOR if hovered else AXIS_COLORS[handle.axis]
            parts.append(arrow(start, handle.normal, 4.2 * unit, unit, color))
        tip = start + handle.normal * 3.4 * unit
        spots.append(Hotspot("resize", handle, tuple(tip), 1.2 * unit))

    # Rotate ring around the box at its top, arrowheads on the side facing the camera.
    radius = 0.5 * math.hypot(hi[0] - lo[0], hi[2] - lo[2]) + 1.5 * unit
    y = hi[1] + 0.05
    segments = 64
    ring = []
    for i in range(segments):
        a0, a1 = 2 * math.pi * i / segments, 2 * math.pi * (i + 1) / segments
        p0 = np.array([center[0] + radius * math.cos(a0), y, center[2] + radius * math.sin(a0)])
        p1 = np.array([center[0] + radius * math.cos(a1), y, center[2] + radius * math.sin(a1)])
        ring.append(cylinder(p0, p1, 0.1 * unit, RING_COLOR, sides=6))
    parts.extend(ring)
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
        parts.append(
            cone(point - tangent * 0.7 * unit, point + tangent * 1.1 * unit, 0.6 * unit, color)
        )
        spots.append(Hotspot("rotate", turns, tuple(point), 1.3 * unit))

    # Flip arrows: double-headed, across the top face.
    top = np.array([center[0], hi[1] + 0.1, center[2]])
    for axis, index in (("x", 0), ("z", 2)):
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
            parts.append(arrow(top, direction * sign, span, 0.8 * unit, color))
            end = top + direction * sign * span
            spots.append(Hotspot("flip", axis, tuple(end), 1.1 * unit))
    return np.vstack(parts), spots


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
