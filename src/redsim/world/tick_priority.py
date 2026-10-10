"""``net/minecraft/world/ticks/TickPriority.java``: scheduled-tick priorities."""

from __future__ import annotations

from enum import IntEnum


class TickPriority(IntEnum):
    """``net/minecraft/world/ticks/TickPriority.java`` (lower runs first)."""

    EXTREMELY_HIGH = -3
    VERY_HIGH = -2
    HIGH = -1
    NORMAL = 0
    LOW = 1
    VERY_LOW = 2
    EXTREMELY_LOW = 3
