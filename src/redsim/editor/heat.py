"""The signal heat view: how strongly each block is powered right now.

Signal sources (wire, torches, repeaters, comparators, levers, observers, …) count with
their own output strength; the blocks next to them with the strongest signal they receive
(``getBestNeighborSignal``, which includes power through strongly powered blocks), and so
do the blocks next to a powered conductor. Blocks without power are left out.
"""

from __future__ import annotations

from redsim.core.direction import ALL
from redsim.core.pos import Pos, offset
from redsim.sim.level import Level

#: The most blocks the view colors (a busy streamed world can have many sources).
MAX_BLOCKS = 20_000


def signal_heat(level: Level, limit: int = MAX_BLOCKS) -> dict[Pos, int]:
    """Position → signal strength (1–15) of every powered block found, at most ``limit``."""
    blocks = level.blocks
    heat: dict[Pos, int] = {}
    sources = [pos for pos, state in blocks.items() if state.is_signal_source()]
    for pos in sources:
        strength = blocks[pos].get_own_signal(level, pos)
        if strength > 0:
            heat[pos] = strength
    seen = set(sources)
    ring = [pos for pos in sources]
    for _ in range(2):  # next to sources, then next to the powered conductors among them
        found: list[Pos] = []
        for pos in ring:
            for direction in ALL:
                near = offset(pos, direction)
                if near in seen or near not in blocks:
                    continue
                seen.add(near)
                strength = level.get_best_neighbor_signal(near)
                if strength > 0:
                    heat[near] = strength
                    if blocks[near].is_redstone_conductor(level, near):
                        found.append(near)
                if len(heat) >= limit:
                    return heat
        ring = found
    return heat
