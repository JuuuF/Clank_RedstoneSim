"""Voxel shapes at 1/16-block resolution, for support and conduction checks.

The game derives several mechanical properties from ``VoxelShape``s:

* ``isCollisionShapeFullBlock`` (default redstone-conductor predicate,
  ``BlockBehaviour.Properties.isRedstoneConductor`` L1030),
* ``isFaceSturdy`` for ``SupportType`` FULL/CENTER/RIGID (``SupportType.java``),
  evaluated on the block support shape's ``getFaceShape(direction)``.

``VoxelShape.getFaceShape`` takes the slice of voxels touching the face and extrudes it
through the whole block. FULL requires that slice to be the full face; CENTER and RIGID
require it to contain ``Block.column(2, 0, 10)`` and the outer 2-pixel ring
(``Shapes.block()`` minus ``Block.column(12, 0, 16)``) respectively. All in-scope shapes are
aligned to the 1/16 grid, so a 16×16×16 boolean grid reproduces these checks exactly.
Parts of a shape outside the unit cube (the piston arm reaching into the base) are clipped;
they do not affect any of these checks.
"""

from __future__ import annotations

from enum import Enum

import numpy as np
import numpy.typing as npt

from redsim.core.direction import Axis, Direction

N = 16
Grid = npt.NDArray[np.bool_]


class SupportType(Enum):
    FULL = "full"
    CENTER = "center"
    RIGID = "rigid"


class Shape:
    """Immutable voxel shape. Index order of the grid is ``[x, y, z]`` in pixels."""

    __slots__ = ("_grid", "_sturdy_cache")

    def __init__(self, grid: Grid) -> None:
        self._grid = grid
        self._grid.setflags(write=False)
        self._sturdy_cache: dict[tuple[Direction, SupportType], bool] = {}

    @property
    def grid(self) -> Grid:
        return self._grid

    def union(self, other: Shape) -> Shape:
        return Shape(self._grid | other._grid)

    def __or__(self, other: Shape) -> Shape:
        return self.union(other)

    def is_empty(self) -> bool:
        return not bool(self._grid.any())

    def is_full_block(self) -> bool:
        """``Block.isShapeFullBlock``."""
        return bool(self._grid.all())

    def bounds(self) -> tuple[int, int, int, int, int, int]:
        """Bounding box in pixels ``(x0, y0, z0, x1, y1, z1)`` (``VoxelShape.bounds``)."""
        xs, ys, zs = np.nonzero(self._grid)
        return (
            int(xs.min()), int(ys.min()), int(zs.min()),
            int(xs.max()) + 1, int(ys.max()) + 1, int(zs.max()) + 1,
        )  # fmt: skip

    def face_slice(self, direction: Direction) -> Grid:
        """The 2D slice of voxels touching ``direction``'s face (``getFaceShape``)."""
        axis = {Axis.X: 0, Axis.Y: 1, Axis.Z: 2}[direction.axis]
        index = N - 1 if direction.is_positive else 0
        return np.take(self._grid, index, axis=axis)

    def is_face_sturdy(self, direction: Direction, support: SupportType = SupportType.FULL) -> bool:
        key = (direction, support)
        cached = self._sturdy_cache.get(key)
        if cached is None:
            cached = _is_supporting(self, direction, support)
            self._sturdy_cache[key] = cached
        return cached

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Shape) and bool(np.array_equal(self._grid, other._grid))

    def __hash__(self) -> int:
        return hash(self._grid.tobytes())


def box(x0: float, y0: float, z0: float, x1: float, y1: float, z1: float) -> Shape:
    """``Block.box`` in pixel units; coordinates are clipped to the unit cube."""

    def span(a: float, b: float) -> slice:
        lo, hi = max(0, int(a)), min(N, int(b))
        if lo != a and a > 0 or hi != b and b < N:
            raise ValueError("shape coordinates must be whole pixels")
        return slice(lo, hi)

    grid = np.zeros((N, N, N), dtype=np.bool_)
    grid[span(x0, x1), span(y0, y1), span(z0, z1)] = True
    return Shape(grid)


def column(size: float, y0: float, y1: float) -> Shape:
    """``Block.column(sizeXZ, minY, maxY)``."""
    half = size / 2
    return box(8 - half, y0, 8 - half, 8 + half, y1, 8 + half)


def facing_box(direction: Direction, size: float, depth_from: float, depth_to: float) -> Shape:
    """A box centered on the face of ``direction``, ``size`` wide on both cross axes,
    reaching from ``depth_from`` to ``depth_to`` pixels inward from that face.

    Equivalent to ``Shapes.rotateAll(Block.boxZ(size, depth_from, depth_to))[direction]``
    for the centered, rotation-symmetric boxes used by pistons.
    """
    lo, hi = 8 - size / 2, 8 + size / 2
    near, far = (N - depth_to, N - depth_from) if direction.is_positive else (depth_from, depth_to)
    if direction.axis is Axis.X:
        return box(near, lo, lo, far, hi, hi)
    if direction.axis is Axis.Y:
        return box(lo, near, lo, hi, far, hi)
    return box(lo, lo, near, hi, hi, far)


EMPTY = Shape(np.zeros((N, N, N), dtype=np.bool_))
FULL_BLOCK = Shape(np.ones((N, N, N), dtype=np.bool_))
_CENTER_SUPPORT = column(2, 0, 10).grid
_RIGID_SUPPORT = FULL_BLOCK.grid & ~column(12, 0, 16).grid


def _extruded_face(shape: Shape, direction: Direction) -> Grid:
    face = shape.face_slice(direction)
    axis = {Axis.X: 0, Axis.Y: 1, Axis.Z: 2}[direction.axis]
    return np.repeat(np.expand_dims(face, axis), N, axis=axis)


def _is_supporting(shape: Shape, direction: Direction, support: SupportType) -> bool:
    if shape.is_empty():
        return False
    face = _extruded_face(shape, direction)
    if support is SupportType.FULL:
        return bool(face.all())
    required = _CENTER_SUPPORT if support is SupportType.CENTER else _RIGID_SUPPORT
    # Shapes.joinIsNotEmpty(face, required, ONLY_SECOND) == any required voxel missing.
    return not bool((required & ~face).any())
