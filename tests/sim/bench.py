"""A small test bench: a stone floor and player-like actions through the engine."""

from __future__ import annotations

from redsim.core.pos import Pos
from redsim.sim.engine import Action, Engine
from redsim.world import blocks
from redsim.world.block import BlockState
from redsim.world.properties import Property


class Bench:
    """Floor of stone at y=0 for x, z in [-4, 24); components go at y >= 1."""

    def __init__(self, floor: bool = True) -> None:
        self.engine = Engine()
        self.level = self.engine.level
        if floor:
            for x in range(-4, 24):
                for z in range(-4, 24):
                    self.level.blocks[(x, 0, z)] = blocks.STONE.default_state

    def place(self, pos: Pos, state: str) -> None:
        self.engine.apply(Action("place", pos, state))

    def setblock(self, pos: Pos, state: str) -> None:
        self.engine.apply(Action("setblock", pos, state))

    def use(self, pos: Pos) -> None:
        self.engine.apply(Action("use", pos))

    def break_block(self, pos: Pos) -> None:
        self.engine.apply(Action("break", pos))

    def tick(self, count: int = 1) -> None:
        self.engine.run_ticks(count)

    def state(self, pos: Pos) -> BlockState:
        return self.level.get_block_state(pos)

    def get(self, pos: Pos, prop: Property) -> object:
        return self.state(pos).get(prop)
