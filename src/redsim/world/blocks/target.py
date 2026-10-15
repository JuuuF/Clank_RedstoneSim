"""Target block: a signal source that dust always connects to; projectiles power it.

``net/minecraft/world/level/block/TargetBlock.java`` (relative to
``data/minecraft_src/client-src/``):

* ``POWER`` 0-15; ``isSignalSource`` (so dust connects to it from any side, like to a
  component) and ``ownSignal`` = ``POWER`` (weak, all sides). A full block: it conducts.
* ``onProjectileHit`` → ``updateRedstoneOutput``: strength 1-15 from how close to the face
  center the hit is (``getRedstoneStrength``), for 20 ticks (arrows) or 8 (other
  projectiles), unless a tick is already pending (``setOutputPower``: set with flags 3,
  schedule the reset).
* ``tick``: back to 0 (flags 3). ``onPlace``: placed with power and no pending tick → 0
  (flags 18).

The simulator has no projectiles: the ``Engine`` action ``projectile_hit`` queues the hit,
and the next tick's entity phase (``Phase.ENTITIES``, after block events) applies
``updateRedstoneOutput``, where a projectile summoned between ticks lands in the game
(EXP-037).
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from redsim.core.pos import Pos
from redsim.world.block import Block, BlockState
from redsim.world.properties import POWER

if TYPE_CHECKING:
    from redsim.sim.level import Level

TARGET = "minecraft:target"
ARROW_TICKS, OTHER_TICKS = 20, 8


def hit_strength(distance_from_center: float) -> int:
    """``getRedstoneStrength``: ``distance`` is the larger in-face offset from the center."""
    fraction = min(1.0, max(0.0, (0.5 - distance_from_center) / 0.5))
    return max(1, math.ceil(15.0 * fraction))


class TargetBlock(Block):
    properties = (POWER,)

    def __init__(self) -> None:
        super().__init__(TARGET, destroy_speed=0.5)
        self.register_default_state(self.default_state.with_(POWER, 0))

    def is_signal_source(self, state: BlockState) -> bool:
        return True

    def own_signal(self, state: BlockState, level: Level, pos: Pos) -> int:
        return int(state.get(POWER))

    def hit(self, level: Level, pos: Pos, strength: int, ticks: int) -> bool:
        """``updateRedstoneOutput``; returns False when a reset tick was still pending.

        Not as in the game: called by the editor's projectile-hit stand-in (projectiles are
        not simulated), with the strength and duration the editor chose."""
        if level.has_scheduled_tick(pos, self):
            return False
        state = level.get_block_state(pos)
        level.set_block_and_update(pos, state.with_(POWER, strength))
        level.schedule_tick(pos, self, ticks)
        return True

    def tick(self, state: BlockState, level: Level, pos: Pos) -> None:
        if state.get(POWER) != 0:
            level.set_block_and_update(pos, state.with_(POWER, 0))

    def on_place(
        self,
        state: BlockState,
        level: Level,
        pos: Pos,
        old_state: BlockState,
        moved_by_piston: bool,
    ) -> None:
        changed = state.block is not old_state.block
        if changed and state.get(POWER) > 0 and not level.has_scheduled_tick(pos, self):
            level.set_block(pos, state.with_(POWER, 0), 18)


__all__ = ["ARROW_TICKS", "OTHER_TICKS", "TARGET", "TargetBlock", "hit_strength"]
