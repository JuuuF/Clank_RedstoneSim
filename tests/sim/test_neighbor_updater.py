"""CollectingNeighborUpdater semantics (doc/mechanics/neighbor-updates.md).

The key property: a handler runs to completion before the updates it emitted, which then run
depth-first before the handler's remaining siblings. Naive recursion and a FIFO queue give
different orders; ``test_handler_finishes_before_emitted_updates`` tells all three apart.
"""

from __future__ import annotations

from typing import Any

from redsim.sim.level import Level
from redsim.world import blocks
from tests.sim.probe import ProbeBlock

ORIGIN = (0, 0, 0)


def neighbor_names(log: list[tuple[Any, ...]]) -> list[str]:
    return [entry[1] if entry[0] == "neighbor" else f"{entry[0]}:{entry[1]}" for entry in log]


def test_update_order_is_w_e_d_u_n_s() -> None:
    log: list[tuple[Any, ...]] = []
    level = Level()
    probe = ProbeBlock("p", log)
    around = {
        "W": (-1, 0, 0),
        "E": (1, 0, 0),
        "D": (0, -1, 0),
        "U": (0, 1, 0),
        "N": (0, 0, -1),
        "S": (0, 0, 1),
    }
    for pos in around.values():
        level.blocks[pos] = probe.default_state
    level.update_neighbors_at(ORIGIN, blocks.STONE)
    order = [entry[2] for entry in log]
    assert order == [around[k] for k in ("W", "E", "D", "U", "N", "S")]
    assert all(entry[3] == "stone" for entry in log)


def test_except_from_facing_skips_one_side() -> None:
    from redsim.core.direction import Direction

    log: list[tuple[Any, ...]] = []
    level = Level()
    probe = ProbeBlock("p", log)
    for pos in [(-1, 0, 0), (1, 0, 0), (0, -1, 0), (0, 1, 0), (0, 0, -1), (0, 0, 1)]:
        level.blocks[pos] = probe.default_state
    level.update_neighbors_at_except_from_facing(ORIGIN, blocks.STONE, Direction.WEST)
    assert [entry[2] for entry in log] == [(1, 0, 0), (0, -1, 0), (0, 1, 0), (0, 0, -1), (0, 0, 1)]


def test_handler_finishes_before_emitted_updates() -> None:
    """Collecting updater: [a, after-a, c, b]. Recursion would give [a, c, after-a, b];
    a FIFO queue would give [a, after-a, b, c]."""
    log: list[tuple[Any, ...]] = []
    level = Level()
    a, b, c = ProbeBlock("a", log), ProbeBlock("b", log), ProbeBlock("c", log)
    level.blocks[(-1, 0, 0)] = a.default_state  # west of ORIGIN: updated first
    level.blocks[(1, 0, 0)] = b.default_state  # east of ORIGIN: updated second
    level.blocks[(-9, 0, 0)] = c.default_state  # far away, only reached through a

    def a_reacts(state: Any, lvl: Level, pos: Any) -> None:
        lvl.neighbor_changed((-9, 0, 0), a)
        log.append(("after", "a"))

    a.on_neighbor = a_reacts
    level.update_neighbors_at(ORIGIN, blocks.STONE)
    assert neighbor_names(log) == ["a", "after:a", "c", "b"]


def test_emitted_updates_run_in_order_each_depth_first() -> None:
    log: list[tuple[Any, ...]] = []
    level = Level()
    a, c, d, e = (ProbeBlock(n, log) for n in "acde")
    level.blocks[(-1, 0, 0)] = a.default_state
    level.blocks[(10, 0, 0)] = c.default_state
    level.blocks[(20, 0, 0)] = d.default_state
    level.blocks[(30, 0, 0)] = e.default_state
    a.on_neighbor = lambda s, lvl, p: (
        lvl.neighbor_changed((10, 0, 0), a),
        lvl.neighbor_changed((20, 0, 0), a),
    )
    c.on_neighbor = lambda s, lvl, p: lvl.neighbor_changed((30, 0, 0), c)
    level.neighbor_changed((-1, 0, 0), blocks.STONE)
    assert neighbor_names(log) == ["a", "c", "e", "d"]


def test_multi_update_resumes_after_children() -> None:
    """A multi-neighbor update interrupted by a child continues with its next direction."""
    log: list[tuple[Any, ...]] = []
    level = Level()
    w, e, child = ProbeBlock("w", log), ProbeBlock("e", log), ProbeBlock("child", log)
    level.blocks[(-1, 0, 0)] = w.default_state
    level.blocks[(1, 0, 0)] = e.default_state
    level.blocks[(50, 0, 0)] = child.default_state
    w.on_neighbor = lambda s, lvl, p: lvl.neighbor_changed((50, 0, 0), w)
    level.update_neighbors_at(ORIGIN, blocks.STONE)
    assert neighbor_names(log) == ["w", "child", "e"]


def test_top_level_calls_run_synchronously() -> None:
    log: list[tuple[Any, ...]] = []
    level = Level()
    a = ProbeBlock("a", log)
    level.blocks[(5, 0, 0)] = a.default_state
    level.neighbor_changed((5, 0, 0), blocks.STONE)  # nothing is running: executes now
    log.append(("after", "call"))
    assert neighbor_names(log) == ["a", "after:call"]


def test_chain_limit_drops_excess_updates() -> None:
    log: list[tuple[Any, ...]] = []
    level = Level(max_chained_neighbor_updates=5)
    loop = ProbeBlock("loop", log)
    level.blocks[ORIGIN] = loop.default_state
    loop.on_neighbor = lambda s, lvl, p: lvl.neighbor_changed(ORIGIN, loop)
    level.neighbor_changed(ORIGIN, blocks.STONE)
    assert len(log) == 5
    assert level.neighbor_updater.skipped == 1
    assert not level.neighbor_updater.running
