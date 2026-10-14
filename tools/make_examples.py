"""Build the example world ``examples/showcase.redsim.json``.

Usage (from the repository root)::

    PYTHONPATH=src python -m tools.make_examples

Eight districts on a grass floor, each on its own stone square with a sign naming it.
Every station in a district is one row, with its input on the east (+x) side and its
output on the west, so with the stored camera (looking south) signals flow from left to
right on screen; a sign at the input end says what to try. Every station is a group with
ports (Circuit → Groups lists them; a double click takes the camera there). Components
are placed with player semantics (``Document.place``/``use``) or ``/setblock`` like the
game-verified scenarios (``tools/gameserver/scenarios.py``), and settled before saving.
The Sequences district holds a recorded history: pulses, lever flips, an inspector
change and placed/removed blocks on the timeline, with markers and monitor tracks.
"""

from __future__ import annotations

from pathlib import Path

from redsim.core.direction import Direction
from redsim.core.pos import Pos
from redsim.editor.builder import (
    LOOK_EAST_LEVEL,
    LOOK_WEST,
    ON_EAST_FACE,
    ON_WEST_FACE,
    Builder,
    inputs,
    items,
    outputs,
)
from redsim.editor.clipboard import Region
from redsim.editor.document import Document
from redsim.editor.placement import PlaceRequest
from redsim.world import blocks
from redsim.world.properties import DELAY

OUTPUT = Path(__file__).resolve().parents[1] / "examples" / "showcase.redsim.json"

#: The districts' origins (x, z): four columns from east (left on screen) to west, a
#: north row (nearer the camera) and a south row. Stations sit at local x 0…17 and local
#: z 0…34; the stone square under a district reaches 3 blocks around that.
COLUMNS = (52, 26, 0, -26)
ROWS = (-44, 4)
PAD = (-3, -6, 19, 36)  # local x0, z0, x1, z1 of a district's square
FLOOR_LOW, FLOOR_HIGH = (-36, -60), (78, 48)

#: Observers placed by a player looking west at eye level face east (they watch east).
LOOK_WEST_LEVEL = PlaceRequest(Direction.UP, yaw=90, pitch=0)
#: Looking north at the top of a block: diodes then output north.
LOOK_NORTH = PlaceRequest(Direction.UP, yaw=180, pitch=60)


def origin(column: int, row: int) -> Pos:
    return (COLUMNS[column], 0, ROWS[row])


# ------------------------------------------------------------------ A: basics
def basics(b: Builder) -> None:
    b.sign((8, 1, -4), "A  BASICS", "One idea per", "row. Inputs on", "the left.")

    # 1. Lever and lamp.
    b.place((6, 1, 0), blocks.LEVER)
    b.place((5, 1, 0), blocks.REDSTONE_LAMP)
    b.sign((9, 1, 0), "LEVER + LAMP", "Right-click the", "lever (NORMAL", "mode: Esc)")
    b.group(
        "A1 lever and lamp",
        (5, 1, 0),
        (6, 1, 0),
        [*inputs(("lever", (6, 1, 0))), *outputs(("lamp", (5, 1, 0)))],
    )

    # 2. Inverter: wall lever powers a block, a wall torch on its far side inverts.
    b.solid((5, 1, 3))
    b.place((6, 1, 3), blocks.LEVER, ON_EAST_FACE)
    b.place((4, 1, 3), blocks.REDSTONE_TORCH, ON_WEST_FACE)
    b.place((3, 1, 3), blocks.REDSTONE_LAMP)
    b.mark("processing", (5, 1, 3), (4, 1, 3))
    b.sign((9, 1, 3), "INVERTER", "A torch on a", "powered block", "turns off")
    b.group(
        "A2 inverter",
        (3, 1, 3),
        (6, 1, 3),
        [*inputs(("lever", (6, 1, 3))), *outputs(("lamp", (3, 1, 3)))],
    )

    # 3. Dust line into a delay-4 repeater.
    b.place((7, 1, 6), blocks.LEVER)
    for x in range(3, 7):
        b.place((x, 1, 6), blocks.REDSTONE_WIRE)
    b.place((2, 1, 6), blocks.REPEATER, LOOK_WEST)
    b.use((2, 1, 6), 3)  # delay 1 → 4 (8 game ticks)
    b.place((1, 1, 6), blocks.REDSTONE_LAMP)
    b.mark("processing", *[(x, 1, 6) for x in range(2, 7)])
    b.sign((9, 1, 6), "DUST + REPEATER", "Delay 4: the", "lamp follows", "8 ticks later")
    b.group(
        "A3 dust and repeater (delay 4)",
        (1, 1, 6),
        (7, 1, 6),
        [*inputs(("lever", (7, 1, 6))), *outputs(("lamp", (1, 1, 6)))],
    )

    # 4. Torch AND gate: two inverted inputs joined by dust, inverted again.
    for z in (9, 11):
        b.solid((6, 1, z))
        b.place((7, 1, z), blocks.LEVER, ON_EAST_FACE)
        b.place((6, 2, z), blocks.REDSTONE_TORCH)
    b.solid((6, 1, 10))
    b.place((6, 2, 10), blocks.REDSTONE_WIRE)
    b.place((5, 1, 10), blocks.REDSTONE_TORCH, ON_WEST_FACE)
    b.place((4, 1, 10), blocks.REDSTONE_LAMP)
    b.mark("processing", (6, 2, 9), (6, 2, 11), (6, 2, 10), (5, 1, 10))
    b.sign((9, 1, 10), "AND GATE", "The lamp is on", "only when both", "levers are on")
    b.group(
        "A4 AND gate",
        (4, 1, 9),
        (7, 2, 11),
        [*inputs(("A", (7, 1, 9)), ("B", (7, 1, 11))), *outputs(("A and B", (4, 1, 10)))],
    )

    # 5. Comparator in subtract mode: a barrel signal source (14) minus a dust side input.
    b.source((6, 1, 14), "barrel", 14)
    b.place((5, 1, 14), blocks.COMPARATOR, LOOK_WEST)
    b.use((5, 1, 14))  # compare → subtract
    b.place((4, 1, 14), blocks.REDSTONE_WIRE)
    b.place((3, 1, 14), blocks.REDSTONE_LAMP)
    b.place((5, 1, 17), blocks.LEVER)
    b.place((5, 1, 16), blocks.REDSTONE_WIRE)
    b.place((5, 1, 15), blocks.REDSTONE_WIRE)
    b.mark("processing", (6, 1, 14), (5, 1, 14), (4, 1, 14), (5, 1, 15), (5, 1, 16))
    b.sign((9, 1, 14), "COMPARATOR", "Barrel (14)", "minus the side:", "flip the lever")
    b.group(
        "A5 comparator subtract",
        (3, 1, 14),
        (6, 1, 17),
        [
            *inputs(("side lever", (5, 1, 17))),
            *outputs(("comparator", (5, 1, 14)), ("lamp", (3, 1, 14))),
        ],
    )

    # 6. Sliding block: sticky piston.
    b.place((7, 1, 20), blocks.LEVER)
    b.place((6, 1, 20), blocks.STICKY_PISTON, LOOK_EAST_LEVEL)
    b.solid((5, 1, 20), blocks.OAK_PLANKS)
    b.mark("processing", (6, 1, 20))
    b.sign((9, 1, 20), "STICKY PISTON", "Pushes the", "planks and", "pulls them back")
    b.group(
        "A6 sliding block (sticky piston)",
        (3, 1, 20),
        (7, 1, 20),
        [*inputs(("lever", (7, 1, 20))), *outputs(("piston", (6, 1, 20)))],
    )

    # 7. 1x2 piston door: one lever powers the top piston directly and the bottom one by
    #    quasi-connectivity; the lever also updates the bottom piston (game-verified, EXP-018).
    b.solid((7, 1, 23))
    b.place((6, 1, 23), blocks.STICKY_PISTON, LOOK_EAST_LEVEL)
    b.place((6, 2, 23), blocks.STICKY_PISTON, LOOK_EAST_LEVEL)
    b.solid((5, 1, 23), blocks.OAK_PLANKS)
    b.solid((5, 2, 23), blocks.OAK_PLANKS)
    b.place((7, 2, 23), blocks.LEVER)
    b.mark("processing", (6, 1, 23), (6, 2, 23))
    b.sign((9, 1, 23), "PISTON DOOR", "One lever, two", "pistons: quasi-", "connectivity")
    b.group(
        "A7 piston door (QC)",
        (4, 1, 23),
        (7, 2, 23),
        [
            *inputs(("lever", (7, 2, 23))),
            *outputs(("top piston", (6, 2, 23)), ("bottom piston", (6, 1, 23))),
        ],
    )

    # 8. Torch burnout loop (a quirk): the torch powers the block above it, which powers dust
    #    on the torch's own block. Run it: it flickers, burns out after 8 turn-offs within 60
    #    ticks and stays out until something updates it (EXP-005/006).
    b.solid((6, 1, 27))
    b.place((5, 1, 27), blocks.REDSTONE_TORCH, ON_WEST_FACE)
    b.solid((5, 2, 27))
    b.place((6, 2, 27), blocks.REDSTONE_WIRE)
    b.mark("clock", (6, 1, 27), (5, 1, 27), (5, 2, 27), (6, 2, 27))
    b.sign((9, 1, 27), "TORCH BURNOUT", "Press P to run:", "it flickers,", "then burns out")
    b.group("A8 torch burnout loop (quirk)", (5, 1, 27), (6, 2, 27), outputs(("torch", (5, 1, 27))))


# ------------------------------------------------------------------ B: logic and memory
def logic(b: Builder) -> None:
    b.sign((9, 1, -4), "B  LOGIC", "Gates, memory", "and pulses")

    # 1. OR gate: either lever powers the dust line.
    b.place((9, 1, 0), blocks.LEVER)
    for x in range(4, 9):
        b.place((x, 1, 0), blocks.REDSTONE_WIRE)
    b.place((6, 1, 1), blocks.LEVER)
    b.place((3, 1, 0), blocks.REDSTONE_LAMP)
    b.sign((11, 1, 0), "OR GATE", "Either lever", "lights the lamp")
    b.group(
        "B1 OR gate",
        (3, 1, 0),
        (9, 1, 1),
        [*inputs(("A", (9, 1, 0)), ("B", (6, 1, 1))), *outputs(("A or B", (3, 1, 0)))],
    )

    # 2. Repeater lock: a powered repeater at the side locks the data repeater.
    b.place((9, 1, 4), blocks.LEVER)
    for x in range(6, 9):
        b.place((x, 1, 4), blocks.REDSTONE_WIRE)
    b.place((5, 1, 4), blocks.REPEATER, LOOK_WEST)
    b.place((4, 1, 4), blocks.REDSTONE_LAMP)
    b.place((5, 1, 5), blocks.REPEATER, LOOK_NORTH)
    b.place((5, 1, 6), blocks.LEVER)
    b.mark("processing", (5, 1, 4), (5, 1, 5))
    b.sign((11, 1, 4), "REPEATER LOCK", "Flip LOCK (the", "front lever):", "the lamp holds")
    b.group(
        "B2 repeater lock (memory)",
        (4, 1, 4),
        (9, 1, 6),
        [*inputs(("data", (9, 1, 4)), ("lock", (5, 1, 6))), *outputs(("lamp", (4, 1, 4)))],
    )

    # 3. T flip-flop: a copper bulb toggles on every press; a comparator reads it.
    b.place((9, 1, 8), blocks.STONE_BUTTON)
    b.set((8, 1, 8), "minecraft:copper_bulb")
    b.place((7, 1, 8), blocks.COMPARATOR, LOOK_WEST)
    b.place((6, 1, 8), blocks.REDSTONE_LAMP)
    b.mark("processing", (8, 1, 8), (7, 1, 8))
    b.sign((11, 1, 8), "COPPER BULB", "Each press", "toggles it", "(T flip-flop)")
    b.group(
        "B3 T flip-flop (copper bulb)",
        (6, 1, 8),
        (9, 1, 8),
        [*inputs(("button", (9, 1, 8))), *outputs(("bulb", (8, 1, 8)), ("lamp", (6, 1, 8)))],
    )

    # 4. Observer chain: an observer watches the lever; each observer watches the next.
    b.place((10, 1, 12), blocks.LEVER)
    for x in (9, 8, 7, 6):
        b.set((x, 1, 12), "minecraft:observer[facing=east]")
    b.place((5, 1, 12), blocks.REDSTONE_LAMP)
    b.mark("processing", *[(x, 1, 12) for x in (9, 8, 7, 6)])
    b.sign((12, 1, 12), "OBSERVERS", "See a change,", "send a 2-tick", "pulse")
    b.group(
        "B4 observer chain",
        (5, 1, 12),
        (10, 1, 12),
        [*inputs(("lever", (10, 1, 12))), *outputs(("lamp", (5, 1, 12)))],
    )

    # 5. Buttons: stone stays pressed 20 ticks, wood 30.
    b.place((7, 1, 16), blocks.REDSTONE_LAMP)
    b.place((8, 1, 16), blocks.STONE_BUTTON, ON_EAST_FACE)
    b.place((3, 1, 16), blocks.REDSTONE_LAMP)
    b.place((4, 1, 16), blocks.OAK_BUTTON, ON_EAST_FACE)
    b.sign((10, 1, 16), "BUTTONS", "Stone: 20 ticks", "Wood: 30 ticks")
    b.group(
        "B5 stone and wooden buttons",
        (3, 1, 16),
        (8, 1, 16),
        [
            *inputs(("stone button", (8, 1, 16)), ("oak button", (4, 1, 16))),
            *outputs(("stone lamp", (7, 1, 16)), ("oak lamp", (3, 1, 16))),
        ],
    )

    # 6. Torch tower: four torches stacked up (even: the lamp follows the lever).
    b.place((10, 1, 20), blocks.LEVER)
    b.set((9, 1, 20), "minecraft:repeater[facing=east,delay=1]")
    b.solid((8, 1, 20))
    for i in range(1, 5):
        b.set((8, 2 * i, 20), "minecraft:redstone_torch")
        if i < 4:
            b.solid((8, 2 * i + 1, 20))
    b.set((8, 9, 20), "minecraft:redstone_lamp")
    b.mark("processing", *[(8, y, 20) for y in range(1, 9)])
    b.sign((12, 1, 20), "TORCH TOWER", "The signal goes", "up: 2 ticks per", "torch")
    b.group(
        "B6 torch tower",
        (8, 1, 20),
        (10, 9, 20),
        [*inputs(("lever", (10, 1, 20))), *outputs(("lamp", (8, 9, 20)))],
    )

    # 7. Pressure plates (entities are not simulated: the inspector's "Step on it").
    b.place((9, 1, 24), blocks.STONE_PRESSURE_PLATE)
    b.place((8, 1, 24), blocks.REDSTONE_LAMP)
    b.place((5, 1, 24), blocks.LIGHT_WEIGHTED_PRESSURE_PLATE)
    for x in range(1, 5):
        b.place((x, 1, 24), blocks.REDSTONE_WIRE)
    b.place((0, 1, 24), blocks.REDSTONE_LAMP)
    b.sign((11, 1, 24), "PRESSURE PLATES", "Inspector: Step", "on it. Weighted:", "one per entity")
    b.group(
        "B7 pressure plates",
        (0, 1, 24),
        (9, 1, 24),
        [
            *inputs(("stone plate", (9, 1, 24)), ("weighted plate", (5, 1, 24))),
            *outputs(("lamp", (8, 1, 24)), ("far lamp", (0, 1, 24))),
        ],
    )

    # 8. Target block: an arrow (inspector) powers it for 20 ticks, a snowball for 8.
    b.place((8, 1, 28), blocks.TARGET)
    for x in (7, 6, 5):
        b.place((x, 1, 28), blocks.REDSTONE_WIRE)
    b.place((4, 1, 28), blocks.REDSTONE_LAMP)
    b.sign((10, 1, 28), "TARGET BLOCK", "Inspector: hit", "it with an", "arrow")
    b.group(
        "B8 target block",
        (4, 1, 28),
        (8, 1, 28),
        [*inputs(("target", (8, 1, 28))), *outputs(("lamp", (4, 1, 28)))],
    )

    # 9. Note block: every note change is a state change an observer sees.
    b.place((10, 1, 32), blocks.LEVER)
    b.place((9, 1, 32), blocks.NOTE_BLOCK)
    b.set((8, 1, 32), "minecraft:observer[facing=east]")
    b.place((7, 1, 32), blocks.REDSTONE_LAMP)
    b.sign((12, 1, 32), "NOTE BLOCK", "Right-click it:", "next note; the", "observer sees it")
    b.group(
        "B9 note block and observer",
        (7, 1, 32),
        (10, 1, 32),
        [
            *inputs(("lever", (10, 1, 32)), ("note block", (9, 1, 32))),
            *outputs(("lamp", (7, 1, 32))),
        ],
    )


# ------------------------------------------------------------------ C: signal strength
#: Station rows: (z, source kind, strength, sign lines).
SOURCES = (
    (0, "barrel", 15, ("BARREL 15", "Items inside set", "the strength")),
    (4, "lectern", 9, ("LECTERN 9", "The page sets", "it: Page > in", "the inspector")),
    (8, "cake", 14, ("CAKE 14", "Full cake: 14,", "2 less a bite")),
    (12, "composter", 6, ("COMPOSTER 6", "Its fill level", "(0 to 8)")),
    (16, "hopper", 3, ("HOPPER 3", "Items inside", "set it too")),
    (20, "chest", 8, ("CHEST 8", "Any container", "can be read")),
)


def strength(b: Builder) -> None:
    b.sign((10, 1, -4), "C  STRENGTH", "Comparators", "read items;", "Alt+H: heat")
    for z, kind, power, lines in SOURCES:
        b.source((15, 1, z), kind, power)
        b.place((14, 1, z), blocks.COMPARATOR, LOOK_WEST)
        for x in range(1, 14):
            b.place((x, 1, z), blocks.REDSTONE_WIRE)
        b.place((0, 1, z), blocks.REDSTONE_LAMP)
        b.sign((17, 1, z), *lines)
        b.group(
            f"C{z // 4 + 1} {kind} source ({power})",
            (0, 1, z),
            (15, 1, z),
            [
                *inputs((kind, (15, 1, z))),
                *outputs(("comparator", (14, 1, z)), ("lamp", (0, 1, z))),
            ],
        )

    # 7. Dust loses 1 per block: 15 dust from a lever still light a lamp.
    b.place((16, 1, 24), blocks.LEVER)
    for x in range(1, 16):
        b.place((x, 1, 24), blocks.REDSTONE_WIRE)
    b.place((0, 1, 24), blocks.REDSTONE_LAMP)
    b.sign((18, 1, 24), "DUST", "Loses 1 a block:", "15 blocks reach", "the lamp")
    b.group(
        "C7 dust line (15)",
        (0, 1, 24),
        (16, 1, 24),
        [*inputs(("lever", (16, 1, 24))), *outputs(("lamp", (0, 1, 24)))],
    )

    # 8. A comparator reads a container through a solid block.
    b.source((16, 1, 28), "barrel", 10)
    b.solid((15, 1, 28))
    b.place((14, 1, 28), blocks.COMPARATOR, LOOK_WEST)
    for x in range(5, 14):
        b.place((x, 1, 28), blocks.REDSTONE_WIRE)
    b.place((4, 1, 28), blocks.REDSTONE_LAMP)
    b.sign((18, 1, 28), "THROUGH A BLOCK", "Comparators", "read containers", "behind a block")
    b.group(
        "C8 comparator through a block",
        (4, 1, 28),
        (16, 1, 28),
        [
            *inputs(("barrel", (16, 1, 28))),
            *outputs(("comparator", (14, 1, 28)), ("lamp", (4, 1, 28))),
        ],
    )


# ------------------------------------------------------------------ D: pistons
def pistons(b: Builder) -> None:
    b.sign((10, 1, -4), "D  PISTONS", "Push, pull,", "stick, and", "wait for updates")

    # 1. Push limit: 12 blocks move.
    b.place((16, 1, 0), blocks.LEVER)
    b.place((15, 1, 0), blocks.PISTON, LOOK_EAST_LEVEL)
    for x in range(3, 15):
        b.solid((x, 1, 0), blocks.OAK_PLANKS)
    b.sign((18, 1, 0), "PUSH LIMIT", "12 blocks move;", "a 13th would", "stop the piston")
    b.group(
        "D1 push limit (12 blocks)",
        (2, 1, 0),
        (16, 1, 0),
        [*inputs(("lever", (16, 1, 0))), *outputs(("piston", (15, 1, 0)))],
    )

    # 2. Slime and honey (in the air: slime would drag the floor): the slime block
    #    carries the stone on top and at the side; the honey block beside it stays.
    b.solid((13, 1, 4))
    b.place((14, 1, 4), blocks.LEVER, ON_EAST_FACE)
    b.set((13, 2, 4), "minecraft:sticky_piston[facing=west]")
    b.set((12, 2, 4), "minecraft:slime_block")
    b.solid((12, 3, 4))
    b.solid((12, 2, 5))
    b.set((12, 2, 3), "minecraft:honey_block")
    b.sign((16, 1, 4), "SLIME + HONEY", "Slime drags its", "neighbors along;", "not honey")
    b.group(
        "D2 slime and honey",
        (10, 1, 3),
        (14, 3, 5),
        [*inputs(("lever", (14, 1, 4))), *outputs(("piston", (13, 2, 4)))],
    )

    # 3. Moving power: a sticky piston pushes a redstone block next to a lamp.
    b.place((16, 1, 8), blocks.LEVER)
    b.place((15, 1, 8), blocks.STICKY_PISTON, LOOK_EAST_LEVEL)
    b.set((14, 1, 8), "minecraft:redstone_block")
    b.place((12, 1, 8), blocks.REDSTONE_LAMP)
    b.sign((18, 1, 8), "MOVING POWER", "The piston moves", "a redstone", "block to a lamp")
    b.group(
        "D3 moving power",
        (12, 1, 8),
        (16, 1, 8),
        [*inputs(("lever", (16, 1, 8))), *outputs(("lamp", (12, 1, 8)))],
    )

    # 4. Quasi-connectivity: power above-behind the piston; it waits for an update
    #    (a "budded" piston; EXP-016). The redstone block goes last: nothing updates it.
    b.set((14, 1, 12), "minecraft:piston[facing=west]")
    b.solid((13, 1, 12), blocks.OAK_PLANKS)
    b.set((15, 2, 12), "minecraft:redstone_block")
    b.sign((17, 1, 12), "BUD PISTON", "Powered from", "above: place a", "block beside it")
    b.group("D4 budded piston (QC)", (12, 1, 12), (15, 2, 12), outputs(("piston", (14, 1, 12))))

    # 5. An observer watches a piston extend.
    b.place((14, 1, 16), blocks.LEVER)
    b.set((13, 1, 16), "minecraft:piston[facing=up]")
    b.set((13, 1, 17), "minecraft:observer[facing=north]")
    b.place((13, 1, 18), blocks.REDSTONE_LAMP)
    b.sign((16, 1, 16), "OBSERVER", "watches the", "piston: the", "lamp blinks")
    b.group(
        "D5 observer and piston",
        (13, 1, 16),
        (14, 2, 18),
        [*inputs(("lever", (14, 1, 16))), *outputs(("lamp", (13, 1, 18)))],
    )

    # 6. Powered rails: power reaches 8 rails past the powered one.
    b.place((15, 1, 22), blocks.LEVER)
    for x in range(3, 15):
        b.set((x, 1, 22), "minecraft:powered_rail[shape=east_west]")
    b.sign((17, 1, 22), "POWERED RAILS", "Power reaches", "8 more rails")
    b.group(
        "D6 powered rails",
        (3, 1, 22),
        (15, 1, 22),
        [*inputs(("lever", (15, 1, 22))), *outputs(("last rail", (3, 1, 22)))],
    )

    # 7. A rail junction switches when powered.
    for pos in ((12, 1, 27), (11, 1, 27), (10, 1, 27), (11, 1, 28)):
        b.set(pos, "minecraft:rail")
    b.place((11, 1, 26), blocks.LEVER)
    b.sign((15, 1, 27), "RAIL JUNCTION", "Power switches", "the T junction")
    b.group(
        "D7 rail junction",
        (10, 1, 26),
        (12, 1, 28),
        [*inputs(("lever", (11, 1, 26))), *outputs(("junction", (11, 1, 27)))],
    )


# ------------------------------------------------------------------ E: items
def item_district(b: Builder) -> None:
    b.sign((10, 1, -4), "E  ITEMS", "Droppers and", "hoppers move", "items: press P")
    dust, pearl = "redstone", "ender_pearl"

    # 1. A dropper pushes one item per press into a hopper, which fills a chest.
    b.set((14, 1, 0), "minecraft:dropper[facing=west]", items((dust, 3)))
    b.set((13, 1, 0), "minecraft:hopper[facing=west]")
    b.set((12, 1, 0), "minecraft:chest[facing=north]")
    b.place((15, 1, 0), blocks.STONE_BUTTON, ON_EAST_FACE)
    for x in (14, 12):
        b.set((x, 1, 1), "minecraft:comparator[facing=north]")
        b.place((x, 1, 2), blocks.REDSTONE_LAMP)
    b.sign((17, 1, 0), "DROPPER", "A press moves", "one item on")
    b.group(
        "E1 dropper, hopper, chest",
        (12, 1, 0),
        (15, 1, 2),
        [
            *inputs(("button", (15, 1, 0))),
            *outputs(("dropper reading", (14, 1, 1)), ("chest reading", (12, 1, 1))),
        ],
    )

    # 2. Hopper chain: a barrel feeds three hoppers into a second barrel (EXP: hopper_chain).
    #    Comparators on both sides, so no two lamps touch (a powered lamp lights its
    #    neighbor).
    b.set((15, 2, 6), "minecraft:barrel[facing=up]")
    b.set_later((15, 2, 6), "minecraft:barrel[facing=up]", items((dust, 5), (pearl, 3)))
    for x in (15, 13, 14):  # the last hopper first: it ticks first (game-verified)
        b.set((x, 1, 6), "minecraft:hopper[facing=west]")
    b.set((12, 1, 6), "minecraft:barrel[facing=up]")
    readings = {15: (7, "north", 8), 14: (5, "south", 4), 13: (7, "north", 8), 12: (5, "south", 4)}
    for x, (z, facing, lamp) in readings.items():
        b.set((x, 1, z), f"minecraft:comparator[facing={facing}]")
        b.place((x, 1, lamp), blocks.REDSTONE_LAMP)
    b.sign((17, 1, 6), "HOPPER CHAIN", "One item every", "8 ticks; lamps", "show contents")
    b.group(
        "E2 hopper chain",
        (12, 1, 4),
        (15, 2, 8),
        outputs(
            *[(f"reading {i + 1}", (x, 1, readings[x][0])) for i, x in enumerate((15, 14, 13, 12))]
        ),
    )

    # 3. A powered hopper is locked.
    b.set((14, 2, 10), "minecraft:barrel[facing=up]")
    b.set_later((14, 2, 10), "minecraft:barrel[facing=up]", items((dust, 20)))
    b.set((14, 1, 10), "minecraft:hopper[facing=west]")
    b.set((13, 1, 10), "minecraft:hopper[facing=west]")
    b.set((12, 1, 10), "minecraft:barrel[facing=up]")
    b.place((14, 1, 11), blocks.LEVER)
    b.set((12, 1, 11), "minecraft:comparator[facing=north]")
    b.place((12, 1, 12), blocks.REDSTONE_LAMP)
    b.sign((17, 1, 10), "HOPPER LOCK", "Power stops a", "hopper: flip", "the lever")
    b.group(
        "E3 hopper lock",
        (12, 1, 10),
        (14, 2, 12),
        [*inputs(("lock lever", (14, 1, 11))), *outputs(("barrel reading", (12, 1, 11)))],
    )

    # 4. A double chest is one container: both halves read the same.
    b.set((15, 2, 15), "minecraft:barrel[facing=up]")
    b.set_later((15, 2, 15), "minecraft:barrel[facing=up]", items((dust, 64), (dust, 64)))
    b.set((15, 1, 15), "minecraft:hopper[facing=west]")
    b.set((14, 1, 15), "minecraft:chest[facing=north,type=right]")
    b.set((13, 1, 15), "minecraft:chest[facing=north,type=left]")
    for x in (14, 13):
        b.set((x, 1, 16), "minecraft:comparator[facing=north]")
        b.place((x, 1, 17), blocks.REDSTONE_LAMP)
    b.sign((17, 1, 15), "DOUBLE CHEST", "Both halves are", "one container")
    b.group(
        "E4 double chest",
        (13, 1, 15),
        (15, 2, 17),
        outputs(("right half", (14, 1, 16)), ("left half", (13, 1, 16))),
    )

    # 5. A composter at level 7 is ready 20 ticks later; the hopper below empties it.
    b.set((14, 1, 20), "minecraft:hopper[facing=west]")
    b.set((13, 1, 20), "minecraft:chest[facing=north]")
    b.set((14, 2, 20), "minecraft:composter")
    b.set_later((14, 2, 20), "minecraft:composter[level=7]")
    b.solid((14, 1, 21))
    b.set((14, 2, 21), "minecraft:comparator[facing=north]")
    b.solid((14, 1, 22))
    b.place((14, 2, 22), blocks.REDSTONE_LAMP)
    b.sign((17, 1, 20), "COMPOSTER", "7, then ready (8)", "after 20 ticks;", "the hopper takes")
    b.group(
        "E5 composter and hopper",
        (13, 1, 20),
        (14, 2, 22),
        outputs(("composter reading", (14, 2, 21)), ("chest", (13, 1, 20))),
    )


# ------------------------------------------------------------------ F: clocks
def clocks(b: Builder) -> None:
    b.sign((10, 1, -4), "F  CLOCKS", "Timing: press P", "to run, T to", "step one tick")

    # 1. Repeater delays 1 to 4 from one lever (rows 2 apart: lamps side by side would
    #    power each other).
    b.place((13, 1, 0), blocks.LEVER)
    for z in range(7):
        b.place((12, 1, z), blocks.REDSTONE_WIRE)
    for i, z in enumerate((0, 2, 4, 6)):
        b.set((11, 1, z), f"minecraft:repeater[facing=east,delay={i + 1}]")
        b.place((10, 1, z), blocks.REDSTONE_LAMP)
    b.sign((15, 1, 0), "REPEATER DELAY", "1, 2, 3, 4: the", "lamps light one", "after another")
    b.group(
        "F1 repeater delays",
        (10, 1, 0),
        (13, 1, 6),
        [
            *inputs(("lever", (13, 1, 0))),
            *outputs(*[(f"delay {i + 1}", (10, 1, z)) for i, z in enumerate((0, 2, 4, 6))]),
        ],
    )

    # 2. Observer clock: two observers watching each other (always running); dust
    #    behind them shows each pulse (a lamp would stay lit: it turns off 4 ticks late).
    b.set((13, 1, 9), "minecraft:observer[facing=west]")
    b.set((12, 1, 9), "minecraft:observer[facing=east]")
    b.place((14, 1, 9), blocks.REDSTONE_WIRE)
    b.place((11, 1, 9), blocks.REDSTONE_WIRE)
    b.mark("clock", (13, 1, 9), (12, 1, 9))
    b.sign((16, 1, 9), "OBSERVER CLOCK", "Two observers", "watch each other")
    b.group(
        "F2 observer clock",
        (11, 1, 9),
        (14, 1, 9),
        outputs(("east dust", (14, 1, 9)), ("west dust", (11, 1, 9))),
    )

    # 3. Repeater loop: a button starts a pulse running around; lamps in the floor
    #    under the corners light up with the dust above them.
    ring = {
        (11, 1, 12): "minecraft:repeater[facing=east,delay=4]",
        (10, 1, 13): "minecraft:repeater[facing=north,delay=4]",
        (11, 1, 14): "minecraft:repeater[facing=west,delay=4]",
        (12, 1, 13): "minecraft:repeater[facing=south,delay=4]",
    }
    corners = ((12, 1, 12), (10, 1, 12), (10, 1, 14), (12, 1, 14))
    for x, _, z in corners:
        b.set((x, 0, z), "minecraft:redstone_lamp")
    for pos, state in ring.items():
        b.set(pos, state)
    for pos in corners:
        b.place(pos, blocks.REDSTONE_WIRE)
    b.place((13, 1, 12), blocks.STONE_BUTTON)
    b.mark("clock", *ring, *corners)
    b.sign((15, 1, 13), "REPEATER LOOP", "Press it: a", "pulse runs", "around")
    b.group(
        "F3 repeater loop clock",
        (10, 0, 12),
        (13, 1, 14),
        [
            *inputs(("button", (13, 1, 12))),
            *outputs(*[(f"lamp {i + 1}", (x, 0, z)) for i, (x, _, z) in enumerate(corners)]),
        ],
    )

    # 4. Hopper clock: two hoppers pass one item back and forth (always running); one
    #    comparator on each side, so the lamps do not touch.
    b.set((13, 1, 18), "minecraft:hopper[facing=west]", items(("redstone", 1)))
    b.set((12, 1, 18), "minecraft:hopper[facing=east]")
    b.set((13, 1, 17), "minecraft:comparator[facing=south]")
    b.place((13, 1, 16), blocks.REDSTONE_LAMP)
    b.set((12, 1, 19), "minecraft:comparator[facing=north]")
    b.place((12, 1, 20), blocks.REDSTONE_LAMP)
    b.mark("clock", (13, 1, 18), (12, 1, 18))
    b.sign((15, 1, 18), "HOPPER CLOCK", "One item goes", "back and forth")
    b.group(
        "F4 hopper clock",
        (12, 1, 16),
        (13, 1, 20),
        outputs(("east lamp", (13, 1, 16)), ("west lamp", (12, 1, 20))),
    )


# ------------------------------------------------------------------ G: sequences
#: Ticks of the recorded edits (also timeline markers).
CHASER_START, ZERO_TICK, LONG_PULSE = 10, 20, 40
LEVER_ON, DELAY_CHANGE, LEVER_OFF, BLOCK_PLACED, BLOCK_REMOVED = 30, 50, 70, 90, 110


def sequences_build(b: Builder) -> None:
    """The build of the Sequences district; its recorded edits come in ``record``."""
    b.sign((10, 1, -4), "G  SEQUENCES", "Press P: pulses", "and edits on the", "timeline replay")
    # 1. Chaser: eight lamps powered one after another by pulses (ANIMATE mode, K).
    for x in range(7, 15):
        b.place((x, 1, 0), blocks.REDSTONE_LAMP)
    b.sign((16, 1, 0), "PULSES", "Each lamp gets a", "pulse (K mode);", "see the timeline")
    b.group(
        "G1 chaser (pulses)",
        (7, 1, 0),
        (14, 1, 0),
        outputs(("first lamp", (14, 1, 0)), ("last lamp", (7, 1, 0))),
    )
    # 2. A 0-tick pulse spits the block; a long pulse pulls it back.
    b.place((13, 1, 4), blocks.STICKY_PISTON, LOOK_EAST_LEVEL)
    b.solid((12, 1, 4), blocks.OAK_PLANKS)
    b.sign((15, 1, 4), "0-TICK PULSE", "Spits the block;", "a long pulse", "pulls it back")
    b.group("G2 0-tick piston", (10, 1, 4), (13, 1, 4), outputs(("piston", (13, 1, 4))))
    # 3. Recorded edits: a lever flipped, a repeater changed, a block placed and removed.
    b.place((14, 1, 8), blocks.LEVER)
    b.place((13, 1, 8), blocks.REPEATER, LOOK_WEST)
    b.place((12, 1, 8), blocks.REDSTONE_LAMP)
    b.place((9, 1, 8), blocks.REDSTONE_LAMP)
    b.sign((16, 1, 8), "KEYFRAMES", "Edits made while", "running replay:", "see the diamonds")
    b.group(
        "G3 recorded edits",
        (9, 1, 8),
        (14, 1, 8),
        [
            *inputs(("lever", (14, 1, 8))),
            *outputs(("lamp", (12, 1, 8)), ("second lamp", (9, 1, 8))),
        ],
    )


def record(b: Builder) -> None:
    """The Sequences district's history (after the build is settled): edits and pulses at
    later ticks, markers and monitor tracks; ends at tick 0."""
    doc = b.doc
    b.origin = origin(2, 1)

    def at_tick(tick: int) -> None:
        doc.seek_tick(min(tick, doc.end_tick))
        if doc.tick < tick:
            doc.run_ticks(tick - doc.tick)

    lever, repeater, spot = b.at((14, 1, 8)), b.at((13, 1, 8)), b.at((10, 1, 8))
    at_tick(LEVER_ON)
    doc.use(lever)
    at_tick(DELAY_CHANGE)
    doc.set_state(repeater, doc.state_at(repeater).with_(DELAY, 4))
    at_tick(LEVER_OFF)
    doc.use(lever)
    at_tick(BLOCK_PLACED)
    doc.setblock(spot, blocks.REDSTONE_BLOCK.default_state)
    at_tick(BLOCK_REMOVED)
    doc.break_block(spot)
    at_tick(BLOCK_REMOVED + 30)
    # Pulses last: an edit made at an earlier tick drops the recorded future, while a
    # pulse re-runs the history keeping every other edit.
    chaser = [b.at((x, 1, 0)) for x in range(14, 6, -1)]
    for i, pos in enumerate(chaser):
        doc.add_pulse(pos, CHASER_START + 2 * i, 15, 2)
        doc.add_pulse(pos, CHASER_START + 60 + 2 * i, 15, 2)
    piston = b.at((13, 1, 4))
    doc.add_pulse(piston, ZERO_TICK, 15, 0)
    doc.add_pulse(piston, LONG_PULSE, 15, 10)
    lines = doc.lines_of("power")
    lines.sync(chaser, "Chaser")
    lines.add_group("0-tick piston", [piston])

    for tick, name in (
        (CHASER_START, "chaser"),
        (ZERO_TICK, "0-tick"),
        (LEVER_ON, "lever on"),
        (LONG_PULSE, "long pulse"),
        (DELAY_CHANGE, "delay 4"),
        (LEVER_OFF, "lever off"),
        (BLOCK_PLACED, "block placed"),
        (BLOCK_REMOVED, "block removed"),
    ):
        doc.set_marker(tick, name)
    for pos in (chaser[0], piston, b.at((12, 1, 8))):
        doc.toggle_monitor(pos)
    doc.jump("start")
    doc._undo.clear()


# ------------------------------------------------------------------ H: sandbox
def sandbox(b: Builder) -> None:
    b.sign((10, 1, -4), "H  SANDBOX", "Room to build:", "B, pick a block,", "left click")


DISTRICTS = (
    (basics, 0, 0),
    (logic, 1, 0),
    (strength, 2, 0),
    (pistons, 3, 0),
    (item_district, 0, 1),
    (clocks, 1, 1),
    (sequences_build, 2, 1),
    (sandbox, 3, 1),
)


def welcome(b: Builder) -> None:
    """Signs at the north edge, in front of the camera."""
    b.origin = (COLUMNS[0], 0, ROWS[0])
    b.sign((12, 1, -9), "WELCOME!", "8 districts:", "A to D here,", "E to H behind")
    b.sign((9, 1, -9), "New here?", "Help > Tutorial", "teaches every", "feature")
    b.sign((6, 1, -9), "Find a station:", "Circuit tab >", "Groups, double-", "click a name")


def build() -> Document:
    pads = []
    for _, column, row in DISTRICTS:
        x0, z0, x1, z1 = PAD
        ox, _, oz = origin(column, row)
        pads.append(((ox + x0, oz + z0, ox + x1, oz + z1), "minecraft:smooth_stone"))
    b = Builder(FLOOR_LOW, FLOOR_HIGH, "minecraft:grass_block", pads)
    for district, column, row in DISTRICTS:
        b.origin = origin(column, row)
        district(b)
    welcome(b)
    # Settle everything (the clocks and the burnout loop keep running) and make it tick 0.
    b.settle(20)
    doc = b.doc
    b.origin = origin(0, 0)
    doc.save_prefab("AND gate", Region.from_corners(b.at((4, 1, 9)), b.at((7, 2, 11))))
    b.origin = origin(1, 0)
    doc.save_prefab("T flip-flop", Region.from_corners(b.at((6, 1, 8)), b.at((9, 1, 8))))
    doc.save_prefab("Repeater lock", Region.from_corners(b.at((4, 1, 4)), b.at((9, 1, 6))))
    record(b)
    # Orbit camera (redsim.ui.camera): over district A, looking south.
    ox, _, oz = origin(0, 0)
    doc.extra["camera"] = {
        "pivot": [ox + 6.5, 1.0, oz + 6.0],
        "distance": 30.0,
        "yaw": 0.0,
        "pitch": 40.0,
    }
    return doc


def main() -> None:
    doc = build()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(OUTPUT)
    print(
        f"wrote {OUTPUT} ({len(doc.level.blocks)} blocks, {len(doc.groups.groups)} groups, "
        f"{len(doc.pulses())} pulses, {len(doc.history.inputs)} recorded edits)"
    )


if __name__ == "__main__":
    main()
