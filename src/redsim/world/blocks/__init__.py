"""Block registry: one instance per block id, like ``net/minecraft/world/level/block/Blocks``.

Component modules import this module lazily (inside functions) to refer to other blocks,
which avoids import cycles.
"""

from __future__ import annotations

from redsim.world.block import Block, BlockState, PushReaction
from redsim.world.blocks.attached import ButtonBlock, LeverBlock
from redsim.world.blocks.cake import CakeBlock
from redsim.world.blocks.comparator import ComparatorBlock
from redsim.world.blocks.container import BarrelBlock
from redsim.world.blocks.diode import RepeaterBlock
from redsim.world.blocks.lamp import RedstoneLampBlock
from redsim.world.blocks.lectern import LecternBlock
from redsim.world.blocks.piston import MovingPistonBlock, PistonBaseBlock, PistonHeadBlock
from redsim.world.blocks.redstone_wire import RedstoneWireBlock
from redsim.world.blocks.simple import (
    AirBlock,
    GrassBlock,
    HoneyBlock,
    RedstoneBlock,
    SimpleBlock,
    SlabBlock,
    full_cube,
    immovable,
    non_conductor,
)
from redsim.world.blocks.torch import RedstoneTorchBlock, RedstoneWallTorchBlock
from redsim.world.properties import Property

REGISTRY: dict[str, Block] = {}


def register(block: Block) -> Block:
    if block.id in REGISTRY:
        raise ValueError(f"duplicate block id {block.id}")
    REGISTRY[block.id] = block
    return block


def get(block_id: str) -> Block:
    if ":" not in block_id:
        block_id = "minecraft:" + block_id
    return REGISTRY[block_id]


def parse_state(text: str) -> BlockState:
    """Parse ``id[prop=value,...]`` (the ``/setblock`` syntax) into a block state."""
    return parse_state_explicit(text)[0]


def parse_state_explicit(text: str) -> tuple[BlockState, list[Property]]:
    """Like ``parse_state``, also returning the properties written out explicitly
    (``BlockInput.properties``, used by ``overwriteWithDefinedProperties``)."""
    name, _, rest = text.partition("[")
    block = get(name.strip())
    state = block.default_state
    explicit: list[Property] = []
    if rest:
        for assignment in rest.rstrip("]").split(","):
            if not assignment.strip():
                continue
            key, _, value = assignment.partition("=")
            prop = next(p for p in block.properties if p.name == key.strip())
            state = state.with_(prop, prop.parse(value.strip()))
            explicit.append(prop)
    return state, explicit


# --- basic blocks ----------------------------------------------------------------------
AIR = register(AirBlock())
STONE = register(full_cube("minecraft:stone", destroy_speed=1.5))
SMOOTH_STONE = register(full_cube("minecraft:smooth_stone", destroy_speed=2.0))
COBBLESTONE = register(full_cube("minecraft:cobblestone", destroy_speed=2.0))
OAK_PLANKS = register(full_cube("minecraft:oak_planks", destroy_speed=2.0))
WHITE_WOOL = register(full_cube("minecraft:white_wool", destroy_speed=0.8))
WHITE_CONCRETE = register(full_cube("minecraft:white_concrete", destroy_speed=1.8))
#: Superflat terrain (the test server's world), so pushes along the ground match the game.
DIRT = register(full_cube("minecraft:dirt", destroy_speed=0.5))
GRASS_BLOCK = register(GrassBlock())
GLASS = register(non_conductor("minecraft:glass", destroy_speed=0.3))
GLOWSTONE = register(non_conductor("minecraft:glowstone", destroy_speed=0.3))
OBSIDIAN = register(immovable("minecraft:obsidian", destroy_speed=50.0))
BEDROCK = register(SimpleBlock("minecraft:bedrock", destroy_speed=-1.0))
#: Used by /clone as a placeholder (``CloneCommands``); invisible in game.
BARRIER = register(
    SimpleBlock("minecraft:barrier", destroy_speed=-1.0, push_reaction=PushReaction.IMMOVEABLE)
)
SLIME_BLOCK = register(full_cube("minecraft:slime_block", destroy_speed=0.0))
HONEY_BLOCK = register(HoneyBlock())
SMOOTH_STONE_SLAB = register(SlabBlock("minecraft:smooth_stone_slab"))
REDSTONE_BLOCK = register(RedstoneBlock())

# --- redstone components ---------------------------------------------------------------
LEVER = register(LeverBlock())
STONE_BUTTON = register(ButtonBlock("minecraft:stone_button", 20))
OAK_BUTTON = register(ButtonBlock("minecraft:oak_button", 30))
REDSTONE_LAMP = register(RedstoneLampBlock())
REDSTONE_TORCH = register(RedstoneTorchBlock())
REDSTONE_WALL_TORCH = register(RedstoneWallTorchBlock())
REDSTONE_WIRE = register(RedstoneWireBlock())
REPEATER = register(RepeaterBlock())
COMPARATOR = register(ComparatorBlock())
CAKE = register(CakeBlock())
BARREL = register(BarrelBlock())
LECTERN = register(LecternBlock())
PISTON = register(PistonBaseBlock(sticky=False))
STICKY_PISTON = register(PistonBaseBlock(sticky=True))
PISTON_HEAD = register(PistonHeadBlock())
MOVING_PISTON = register(MovingPistonBlock())

__all__ = [
    "AIR",
    "BARREL",
    "BARRIER",
    "BEDROCK",
    "CAKE",
    "COMPARATOR",
    "COBBLESTONE",
    "GLASS",
    "GLOWSTONE",
    "HONEY_BLOCK",
    "LECTERN",
    "LEVER",
    "OAK_BUTTON",
    "REDSTONE_LAMP",
    "REDSTONE_TORCH",
    "REDSTONE_WALL_TORCH",
    "REDSTONE_WIRE",
    "REPEATER",
    "STICKY_PISTON",
    "STONE_BUTTON",
    "OAK_PLANKS",
    "MOVING_PISTON",
    "OBSIDIAN",
    "PISTON",
    "PISTON_HEAD",
    "REDSTONE_BLOCK",
    "REGISTRY",
    "SLIME_BLOCK",
    "SMOOTH_STONE",
    "SMOOTH_STONE_SLAB",
    "STONE",
    "WHITE_CONCRETE",
    "WHITE_WOOL",
    "PushReaction",
    "SimpleBlock",
    "get",
    "parse_state",
    "parse_state_explicit",
    "register",
]
