"""Block positions as plain integer tuples.

Java's ``BlockPos`` is an immutable (x, y, z) triple. Python tuples give the same value
semantics with fast hashing. ``java_hash`` reproduces ``Vec3i.hashCode`` (Vec3i.java L53),
which the game's ``HashSet``/``HashMap`` iteration order depends on.
"""

from __future__ import annotations

from redsim.core.direction import Direction

Pos = tuple[int, int, int]


def offset(pos: Pos, direction: Direction, distance: int = 1) -> Pos:
    """``BlockPos.relative(direction, distance)``."""
    dx, dy, dz = direction.step
    return (pos[0] + dx * distance, pos[1] + dy * distance, pos[2] + dz * distance)


def above(pos: Pos) -> Pos:
    return (pos[0], pos[1] + 1, pos[2])


def below(pos: Pos) -> Pos:
    return (pos[0], pos[1] - 1, pos[2])


def add(pos: Pos, delta: Pos) -> Pos:
    return (pos[0] + delta[0], pos[1] + delta[1], pos[2] + delta[2])


def to_int32(value: int) -> int:
    """Wrap an arbitrary Python int to Java's signed 32-bit ``int``."""
    value &= 0xFFFFFFFF
    return value - 0x1_0000_0000 if value >= 0x8000_0000 else value


def java_hash(pos: Pos) -> int:
    """``Vec3i.hashCode()``: ``(y + z * 31) * 31 + x`` in 32-bit arithmetic."""
    x, y, z = pos
    return to_int32((y + z * 31) * 31 + x)


def format_pos(pos: Pos) -> str:
    return f"({pos[0]}, {pos[1]}, {pos[2]})"
