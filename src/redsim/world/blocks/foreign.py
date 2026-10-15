"""Blocks the simulator does not model yet, kept as the game wrote them (round 8: opening
Minecraft worlds). A foreign block carries its id and properties as text, is drawn with
the game's model and written back unchanged; in the simulation it is inert. How pistons
treat it, whether it conducts and how hard it is come from the game's block table
(``catalog_data``, from ``Blocks.java``): a block with a block entity (a furnace, a
beacon, …) is never moved by pistons (``PistonBaseBlock.isPushable``:
``!state.hasBlockEntity()``), which slime and honey rely on. Only whether it is a full
cube is still guessed from its name (doc/world-import.md); the import lists such blocks.
"""

from __future__ import annotations

from redsim.world.block import Conductor, PushReaction
from redsim.world.blocks.catalog_data import BLOCKS
from redsim.world.blocks.simple import SimpleBlock
from redsim.world.shape import EMPTY

#: Name parts of blocks that are not full cubes (no collision box is modeled for them).
_NOT_FULL = (
    "sign", "stairs", "slab", "fence", "wall", "door", "pane", "bars", "carpet", "button",
    "pressure_plate", "torch", "flower", "sapling", "short_grass", "tall_grass", "fern",
    "bed", "chain", "lantern", "candle", "head", "skull", "banner", "campfire",
    "composter", "cauldron", "bell", "anvil", "chest", "scaffolding", "ladder", "vine",
    "kelp", "coral", "pot", "rod", "pickle", "dripleaf", "sculk_sensor", "amethyst_bud",
    "cluster", "snow", "cake", "lily", "mushroom", "roots", "sprouts", "tripwire",
    "daylight_detector", "enchanting_table", "end_portal_frame", "grindstone", "stonecutter",
    "brewing_stand", "conduit", "item_frame", "web", "chorus", "frogspawn", "decorated_pot",
)  # fmt: skip
#: Full cubes that do not conduct redstone (``Blocks::never``).
_NOT_CONDUCTING = ("glass", "leaves", "ice", "beacon", "sea_lantern", "glowstone", "tnt")

_CACHE: dict[str, ForeignBlock] = {}
#: ``catalog_data`` flags.
NO_COLLISION = 1
HAS_BLOCK_ENTITY = 16


class ForeignBlock(SimpleBlock):
    """One state of a block the simulator does not model, as text."""

    def __init__(self, block_id: str, properties: dict[str, str]) -> None:
        name = block_id.split(":", 1)[-1]
        spec = BLOCKS.get(block_id)
        self.full = not any(part in name for part in _NOT_FULL)
        if spec is not None and spec[4] & NO_COLLISION:
            self.full = False
        conducting = self.full and not any(part in name for part in _NOT_CONDUCTING)
        conductor = Conductor.DEFAULT if conducting else Conductor.NEVER
        push = PushReaction.PUSH_PULL if self.full else PushReaction.POPPED
        destroy = 1.5
        if spec is not None:  # the game's settings (``Blocks.java``)
            _, destroy, reaction, rule, flags, _ = spec
            push = PushReaction[reaction]
            if flags & HAS_BLOCK_ENTITY and push is PushReaction.PUSH_PULL:
                # isPushable is false for any block entity: the same for pistons (pushed or
                # pulled by slime) as IMMOVEABLE. The block entity itself is not modeled.
                push = PushReaction.IMMOVEABLE
            if rule == "never" or not self.full:
                conductor = Conductor.NEVER
            elif rule == "always":
                conductor = Conductor.ALWAYS
            else:
                conductor = Conductor.DEFAULT
        super().__init__(
            block_id,
            shape=None if self.full else EMPTY,
            collision_shape=None if self.full else EMPTY,
            push_reaction=push,
            conductor=conductor,
            destroy_speed=float(destroy),
        )
        self.extra_properties = dict(properties)

    @property
    def text(self) -> str:
        if not self.extra_properties:
            return self.id
        props = ",".join(f"{k}={v}" for k, v in self.extra_properties.items())
        return f"{self.id}[{props}]"


def foreign_block(block_id: str, properties: dict[str, str]) -> ForeignBlock:
    """The (shared) foreign block for this exact state."""
    key = f"{block_id}{sorted(properties.items())}"
    block = _CACHE.get(key)
    if block is None:
        block = _CACHE[key] = ForeignBlock(block_id, properties)
    return block
