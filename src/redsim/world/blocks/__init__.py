"""Block registry: one instance per block id, like ``net/minecraft/world/level/block/Blocks``.

Component modules import this module lazily (inside functions) to refer to other blocks,
which avoids import cycles.
"""

from __future__ import annotations

from redsim.world.block import Block, BlockState, PushReaction
from redsim.world.blocks.attached import ButtonBlock, LeverBlock
from redsim.world.blocks.cake import CakeBlock
from redsim.world.blocks.catalog import catalog_blocks
from redsim.world.blocks.chest import ChestBlock, TrappedChestBlock
from redsim.world.blocks.comparator import ComparatorBlock
from redsim.world.blocks.composter import ComposterBlock
from redsim.world.blocks.container import BarrelBlock
from redsim.world.blocks.copper_bulb import COPPER_BULB_IDS, CopperBulbBlock
from redsim.world.blocks.diode import RepeaterBlock
from redsim.world.blocks.dispenser import DispenserBlock, DropperBlock
from redsim.world.blocks.hopper import HopperBlock
from redsim.world.blocks.lamp import RedstoneLampBlock
from redsim.world.blocks.lectern import LecternBlock
from redsim.world.blocks.note_block import NoteBlock
from redsim.world.blocks.observer import ObserverBlock
from redsim.world.blocks.piston import MovingPistonBlock, PistonBaseBlock, PistonHeadBlock
from redsim.world.blocks.pressure_plate import (
    PLATE_IDS,
    PressurePlateBlock,
    WeightedPressurePlateBlock,
)
from redsim.world.blocks.rail import PoweredRailBlock, RailBlock
from redsim.world.blocks.redstone_wire import RedstoneWireBlock
from redsim.world.blocks.scaffolding import ScaffoldingBlock
from redsim.world.blocks.sign import WOODS, StandingSignBlock, WallSignBlock
from redsim.world.blocks.simple import (
    AirBlock,
    GrassBlock,
    HoneyBlock,
    RedstoneBlock,
    SimpleBlock,
    SlabBlock,
    SlimeBlock,
    full_cube,
    immovable,
    non_conductor,
)
from redsim.world.blocks.target import TargetBlock
from redsim.world.blocks.torch import RedstoneTorchBlock, RedstoneWallTorchBlock
from redsim.world.blocks.tripwire import TripWireBlock, TripWireHookBlock
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
    (``BlockInput.properties``, used by ``overwriteWithDefinedProperties``). An id the
    simulator does not know gives a ``ForeignBlock`` state (kept as text)."""
    name, _, rest = text.partition("[")
    block_id = name.strip() if ":" in name else "minecraft:" + name.strip()
    if block_id not in REGISTRY:
        from redsim.world.blocks.foreign import foreign_block

        props = dict(part.split("=", 1) for part in rest.rstrip("]").split(",") if "=" in part)
        return foreign_block(
            block_id, {k.strip(): v.strip() for k, v in props.items()}
        ).default_state, []
    block = get(block_id)
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
SLIME_BLOCK = register(SlimeBlock())
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
OBSERVER = register(ObserverBlock())
RAIL = register(RailBlock())
POWERED_RAIL = register(PoweredRailBlock("minecraft:powered_rail"))
ACTIVATOR_RAIL = register(PoweredRailBlock("minecraft:activator_rail"))
TARGET = register(TargetBlock())
NOTE_BLOCK = register(NoteBlock())
DISPENSER = register(DispenserBlock())
CHEST = register(ChestBlock())
PRESSURE_PLATES = tuple(register(PressurePlateBlock(i)) for i in PLATE_IDS)
STONE_PRESSURE_PLATE = PRESSURE_PLATES[0]
OAK_PRESSURE_PLATE = PRESSURE_PLATES[2]
LIGHT_WEIGHTED_PRESSURE_PLATE = register(
    WeightedPressurePlateBlock("minecraft:light_weighted_pressure_plate", 15)
)
HEAVY_WEIGHTED_PRESSURE_PLATE = register(
    WeightedPressurePlateBlock("minecraft:heavy_weighted_pressure_plate", 150)
)
TRAPPED_CHEST = register(TrappedChestBlock())
DROPPER = register(DropperBlock())
COPPER_BULBS = tuple(register(CopperBulbBlock(i)) for i in COPPER_BULB_IDS)
COPPER_BULB = COPPER_BULBS[0]
HOPPER = register(HopperBlock())
PISTON = register(PistonBaseBlock(sticky=False))
STICKY_PISTON = register(PistonBaseBlock(sticky=True))
PISTON_HEAD = register(PistonHeadBlock())
MOVING_PISTON = register(MovingPistonBlock())
COMPOSTER = register(ComposterBlock())
SIGNS = tuple(register(StandingSignBlock(wood)) for wood in WOODS)
#: Buttons of every wood and stone (``woodenButton``: 30 ticks, stone ones 20).
BUTTONS = tuple(
    register(ButtonBlock(f"minecraft:{kind}_button", 20 if "stone" in kind else 30))
    for kind in (*WOODS, "polished_blackstone")
    if f"minecraft:{kind}_button" not in REGISTRY
)
WALL_SIGNS = tuple(register(WallSignBlock(wood)) for wood in WOODS)
OAK_SIGN, OAK_WALL_SIGN = SIGNS[0], WALL_SIGNS[0]
_HOOK = TripWireHookBlock()
TRIPWIRE_HOOK = register(_HOOK)
TRIPWIRE = register(TripWireBlock(_HOOK))
SCAFFOLDING = register(ScaffoldingBlock())

# --- the game's ordinary blocks, from the generated table (``catalog.py``) ---------------
CATALOG = tuple(register(block) for block in catalog_blocks(set(REGISTRY)))

__all__ = [
    "AIR",
    "BARREL",
    "BARRIER",
    "BEDROCK",
    "CAKE",
    "COMPARATOR",
    "COMPOSTER",
    "COBBLESTONE",
    "GLASS",
    "GLOWSTONE",
    "HONEY_BLOCK",
    "LECTERN",
    "LEVER",
    "COPPER_BULB",
    "COPPER_BULBS",
    "CHEST",
    "DISPENSER",
    "TRAPPED_CHEST",
    "DROPPER",
    "HEAVY_WEIGHTED_PRESSURE_PLATE",
    "LIGHT_WEIGHTED_PRESSURE_PLATE",
    "NOTE_BLOCK",
    "OAK_SIGN",
    "OAK_WALL_SIGN",
    "SIGNS",
    "WALL_SIGNS",
    "OAK_PRESSURE_PLATE",
    "PRESSURE_PLATES",
    "STONE_PRESSURE_PLATE",
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
    "OBSERVER",
    "OBSIDIAN",
    "PISTON",
    "PISTON_HEAD",
    "REDSTONE_BLOCK",
    "REGISTRY",
    "SLIME_BLOCK",
    "SMOOTH_STONE",
    "SMOOTH_STONE_SLAB",
    "SCAFFOLDING",
    "STONE",
    "TRIPWIRE",
    "TRIPWIRE_HOOK",
    "WHITE_CONCRETE",
    "WHITE_WOOL",
    "PushReaction",
    "SimpleBlock",
    "get",
    "parse_state",
    "parse_state_explicit",
    "register",
]
