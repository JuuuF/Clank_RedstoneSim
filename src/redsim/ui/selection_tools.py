"""Selection box handles and drag math, in the spirit of the Axiom building mod (no Qt).

A selection box has one handle per face (a square at the face center). Dragging a handle
moves that face along its axis; dragging from a block inside the box moves the box (or a
copy) across the horizontal plane at the height where it was grabbed. The world edits
themselves are ``/clone`` actions (``Document.clone_region``); this module only computes
regions and offsets.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from redsim.core.pos import Pos
from redsim.editor.clipboard import Region


@dataclass(frozen=True)
class Handle:
    axis: int  # 0 = x, 1 = y, 2 = z
    high: bool  # the face on the + side of the axis

    @property
    def normal(self) -> np.ndarray:
        """Outward normal of the face."""
        normal = np.zeros(3)
        normal[self.axis] = 1.0 if self.high else -1.0
        return normal


HANDLES = tuple(Handle(axis, high) for axis in range(3) for high in (False, True))


def bounds(region: Region) -> tuple[np.ndarray, np.ndarray]:
    """World-space corners of the box (the high corner is exclusive)."""
    return np.array(region.low, dtype=float), np.array(region.high, dtype=float) + 1.0


def face_center(region: Region, handle: Handle) -> np.ndarray:
    lo, hi = bounds(region)
    center = (lo + hi) / 2.0
    center[handle.axis] = hi[handle.axis] if handle.high else lo[handle.axis]
    return center


def knob_center(region: Region, handle: Handle, size: float) -> np.ndarray:
    """A handle is a pin: a stem out of the face center ending in a knob of ``size``."""
    return face_center(region, handle) + handle.normal * (0.25 + 2.0 * size)


def handle_hit(
    region: Region, origin: np.ndarray, direction: np.ndarray, size: float
) -> tuple[Handle, float] | None:
    """The nearest handle knob the ray passes (generously: 1.5 × the knob size). Handles
    are drawn on top of the world, so blocks never hide them from the mouse either."""
    best: tuple[Handle, float] | None = None
    unit = direction / np.linalg.norm(direction)
    for handle in HANDLES:
        to_knob = knob_center(region, handle, size) - origin
        t = float(to_knob @ unit)
        if t <= 0:
            continue
        miss = float(np.linalg.norm(to_knob - unit * t))
        if miss <= 1.5 * size and (best is None or t < best[1]):
            best = (handle, t)
    return best


def resized(region: Region, handle: Handle, steps: int) -> Region:
    """Move one face ``steps`` blocks outward (negative: inward); never thinner than 1."""
    low, high = list(region.low), list(region.high)
    axis = handle.axis
    if handle.high:
        high[axis] = max(low[axis], region.high[axis] + steps)
    else:
        low[axis] = min(high[axis], region.low[axis] - steps)
    return Region((low[0], low[1], low[2]), (high[0], high[1], high[2]))


def steps_along(drag: tuple[float, float], axis_on_screen: np.ndarray) -> int:
    """Whole blocks a mouse drag covers along an axis whose 1-block length on screen is
    ``axis_on_screen`` (pixels). Axes seen nearly end-on (< 2 px per block) do not move."""
    length2 = float(axis_on_screen @ axis_on_screen)
    if length2 < 4.0:
        return 0
    return round((drag[0] * axis_on_screen[0] + drag[1] * axis_on_screen[1]) / length2)


def plane_point(origin: np.ndarray, direction: np.ndarray, y: float) -> np.ndarray | None:
    """Where the ray meets the horizontal plane at height ``y`` (None if it never does)."""
    if abs(direction[1]) < 1e-6:
        return None
    t = (y - origin[1]) / direction[1]
    if t <= 0:
        return None
    return origin + direction * t


def horizontal_offset(start: np.ndarray, point: np.ndarray) -> tuple[int, int]:
    """Whole-block x/z offset between two points on the drag plane."""
    return round(float(point[0] - start[0])), round(float(point[2] - start[2]))


def shifted(region: Region, offset: Pos) -> Region:
    low = (region.low[0] + offset[0], region.low[1] + offset[1], region.low[2] + offset[2])
    high = (region.high[0] + offset[0], region.high[1] + offset[1], region.high[2] + offset[2])
    return Region(low, high)
