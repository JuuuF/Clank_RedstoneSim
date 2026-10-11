"""Comparison scenarios, simplest first. Coordinates are relative (y=1: above the floor).

Inputs are redstone blocks placed/removed with ``/setblock`` between ticks, because the
dedicated server has no player to flip a lever. ``inputs[t]`` is applied after ``t`` ticks.
"""

from __future__ import annotations

from tools.gameserver.compare import Scenario

RB = "minecraft:redstone_block"
AIR = "minecraft:air"

LAMP_REDSTONE_BLOCK = Scenario(
    name="lamp_redstone_block",
    description="Lamp turns on instantly next to a redstone block and off 4 ticks after removal.",
    size=(4, 3),
    setup=[((2, 1, 1), "minecraft:redstone_lamp")],
    watch=[(2, 1, 1)],
    ticks=10,
    inputs={0: [((1, 1, 1), RB)], 3: [((1, 1, 1), AIR)]},
)

TORCH_INVERTER = Scenario(
    name="torch_inverter",
    description="Wire powers a block; the torch on top turns off and on with a 2-tick delay.",
    size=(4, 3),
    setup=[
        ((2, 1, 1), "minecraft:stone"),
        ((2, 2, 1), "minecraft:redstone_torch"),
        ((1, 1, 1), "minecraft:redstone_wire"),
    ],
    watch=[(1, 1, 1), (2, 2, 1)],
    ticks=12,
    inputs={1: [((0, 1, 1), RB)], 6: [((0, 1, 1), AIR)]},
)

WIRE_LINE_LAMP = Scenario(
    name="wire_line_lamp",
    description="15 wires from a redstone block decay to 1 and still light a lamp.",
    size=(18, 1),
    setup=[((x, 1, 0), "minecraft:redstone_wire") for x in range(1, 16)]
    + [((16, 1, 0), "minecraft:redstone_lamp")],
    watch=[(x, 1, 0) for x in range(1, 17)],
    ticks=10,
    inputs={0: [((0, 1, 0), RB)], 4: [((0, 1, 0), AIR)]},
)

AND_GATE = Scenario(
    name="and_gate",
    description="Torch AND gate: two inverted inputs joined by wire, inverted again.",
    size=(5, 3),
    setup=[
        ((2, 1, 0), "minecraft:stone"),
        ((2, 1, 1), "minecraft:stone"),
        ((2, 1, 2), "minecraft:stone"),
        ((2, 2, 0), "minecraft:redstone_torch"),
        ((2, 2, 2), "minecraft:redstone_torch"),
        ((2, 2, 1), "minecraft:redstone_wire"),
        ((3, 1, 1), "minecraft:redstone_wall_torch[facing=east]"),
        ((4, 1, 1), "minecraft:redstone_lamp"),
        ((1, 1, 0), "minecraft:redstone_wire"),
        ((1, 1, 2), "minecraft:redstone_wire"),
    ],
    watch=[(1, 1, 0), (1, 1, 2), (2, 2, 0), (2, 2, 2), (2, 2, 1), (3, 1, 1), (4, 1, 1)],
    ticks=30,
    inputs={
        4: [((0, 1, 0), RB)],
        10: [((0, 1, 2), RB)],
        17: [((0, 1, 0), AIR)],
        23: [((0, 1, 2), AIR)],
    },
)

TORCH_BURNOUT = Scenario(
    name="torch_burnout",
    description=(
        "Self-oscillating wall torch: it strongly powers the block above it, which powers a "
        "dust dot on the torch's own support block. 8 turn-offs within 60 ticks burn it out; "
        "it re-lights 160 ticks later (RedstoneTorchBlock.tick / isToggledTooFrequently)."
    ),
    size=(4, 3),
    setup=[
        ((1, 1, 1), "minecraft:stone"),
        ((2, 2, 1), "minecraft:stone"),
        ((2, 1, 1), "minecraft:redstone_wall_torch[facing=east]"),
        ((1, 2, 1), "minecraft:redstone_wire"),
    ],
    watch=[(2, 1, 1), (1, 2, 1)],
    ticks=260,
)

TORCH_BURNOUT_UPDATE = Scenario(
    name="torch_burnout_update",
    description=(
        "Same loop as torch_burnout; a block placed next to the burnt-out torch at tick 100 "
        "(more than 60 ticks after the last toggle) sends the update that relights it."
    ),
    size=(4, 3),
    setup=TORCH_BURNOUT.setup,
    watch=[(2, 1, 1), (1, 2, 1)],
    ticks=140,
    inputs={100: [((3, 1, 1), "minecraft:stone")]},
)

GLASS_UP_NOT_DOWN = Scenario(
    name="glass_up_not_down",
    description="Wire climbs onto glass from one side but cannot descend on the other side.",
    size=(5, 1),
    setup=[
        ((1, 1, 0), "minecraft:glass"),
        ((1, 2, 0), "minecraft:redstone_wire"),
        ((0, 1, 0), "minecraft:redstone_wire"),
        ((2, 1, 0), "minecraft:redstone_wire"),
    ],
    watch=[(0, 1, 0), (1, 2, 0), (2, 1, 0)],
    ticks=4,
    inputs={0: [((3, 1, 0), RB)], 2: [((3, 1, 0), AIR), ((0, 1, -1), RB)]},
)

REPEATER_DELAYS = Scenario(
    name="repeater_delays",
    description="Repeaters with delay 1-4 (2/4/6/8 ticks) light lamps; rows spaced apart.",
    size=(4, 7),
    setup=[((1, 1, 2 * d), f"minecraft:repeater[facing=west,delay={d + 1}]") for d in range(4)]
    + [((2, 1, 2 * d), "minecraft:redstone_lamp") for d in range(4)],
    watch=[(1, 1, 2 * d) for d in range(4)] + [(2, 1, 2 * d) for d in range(4)],
    ticks=30,
    inputs={
        0: [((0, 1, 2 * d), RB) for d in range(4)],
        12: [((0, 1, 2 * d), AIR) for d in range(4)],
    },
)

REPEATER_PULSE_EXTENSION = Scenario(
    name="repeater_pulse_extension",
    description="A 1-tick input pulse into a delay-4 repeater becomes an 8-tick output pulse.",
    size=(4, 1),
    setup=[
        ((1, 1, 0), "minecraft:repeater[facing=west,delay=4]"),
        ((2, 1, 0), "minecraft:redstone_lamp"),
    ],
    watch=[(1, 1, 0), (2, 1, 0)],
    ticks=24,
    inputs={0: [((0, 1, 0), RB)], 1: [((0, 1, 0), AIR)]},
)

REPEATER_LOCK_PRIORITY = Scenario(
    name="repeater_lock_priority",
    description=(
        "Race in one game tick: repeater L (scheduled second) locks repeater M. L outputs into "
        "a diode's side, so it ticks at EXTREMELY_HIGH and wins against M's HIGH: M stays off "
        "until L turns off again."
    ),
    size=(4, 3),
    setup=[
        ((2, 1, 1), "minecraft:repeater[facing=north,delay=1]"),
        ((2, 1, 2), "minecraft:repeater[facing=west,delay=1]"),
        ((3, 1, 2), "minecraft:redstone_lamp"),
    ],
    watch=[(2, 1, 1), (2, 1, 2), (3, 1, 2)],
    ticks=14,
    inputs={0: [((1, 1, 2), RB), ((2, 1, 0), RB)], 6: [((2, 1, 0), AIR)]},
)

REPEATER_CHAIN = Scenario(
    name="repeater_chain",
    description="Three delay-1 repeaters in a row add 2 ticks each.",
    size=(6, 1),
    setup=[((x, 1, 0), "minecraft:repeater[facing=west,delay=1]") for x in (1, 2, 3)]
    + [((4, 1, 0), "minecraft:redstone_lamp")],
    watch=[(1, 1, 0), (2, 1, 0), (3, 1, 0), (4, 1, 0)],
    ticks=20,
    inputs={0: [((0, 1, 0), RB)], 8: [((0, 1, 0), AIR)]},
)

COMPARATOR_MODES = Scenario(
    name="comparator_modes",
    description=(
        "Cake (14 - 2*bites) behind a comparator, wire side input 13: compare, then side > rear, "
        "then subtract mode (set by /setblock), then side removed."
    ),
    size=(4, 6),
    setup=[
        ((0, 1, 1), "minecraft:cake"),
        ((1, 1, 1), "minecraft:comparator[facing=west]"),
        ((2, 1, 1), "minecraft:redstone_wire"),
        ((3, 1, 1), "minecraft:redstone_wire"),
        ((1, 1, 2), "minecraft:redstone_wire"),
        ((1, 1, 3), "minecraft:redstone_wire"),
        ((1, 1, 4), "minecraft:redstone_wire"),
    ],
    watch=[(1, 1, 1), (2, 1, 1), (3, 1, 1), (1, 1, 2)],
    ticks=20,
    inputs={
        0: [((1, 1, 5), RB)],
        4: [((0, 1, 1), "minecraft:cake[bites=1]")],
        8: [((1, 1, 1), "minecraft:comparator[facing=west,mode=subtract]")],
        10: [((0, 1, 1), "minecraft:cake[bites=0]")],
        14: [((1, 1, 5), AIR)],
    },
)

COMPARATOR_THROUGH_BLOCK = Scenario(
    name="comparator_through_block",
    description=(
        "Comparator reads cake through a stone block; a torch under the stone gives the stone "
        "strong power 15, which skips the through-block lookup (open question OQ-6)."
    ),
    size=(4, 3),
    setup=[
        ((0, 1, 1), "minecraft:cake"),
        ((1, 1, 1), "minecraft:stone"),
        ((2, 1, 1), "minecraft:comparator[facing=west]"),
        ((3, 1, 1), "minecraft:redstone_wire"),
    ],
    watch=[(2, 1, 1), (3, 1, 1)],
    ticks=16,
    inputs={
        4: [((0, 1, 1), "minecraft:cake[bites=3]")],
        8: [((1, 0, 1), "minecraft:redstone_torch")],
        12: [((1, 0, 1), "minecraft:stone")],
    },
)

COMPARATOR_SIDE_TORCH = Scenario(
    name="comparator_side_torch",
    description=(
        "A lit torch beside a subtracting comparator is not a side input (only direct signal "
        "counts); a powered wire in the same place is."
    ),
    size=(3, 5),
    setup=[
        ((0, 1, 1), RB),
        ((1, 1, 1), "minecraft:comparator[facing=west,mode=subtract]"),
        ((2, 1, 1), "minecraft:redstone_wire"),
    ],
    watch=[(1, 1, 1), (2, 1, 1), (1, 1, 2)],
    ticks=12,
    inputs={
        0: [((1, 1, 2), "minecraft:redstone_torch")],
        4: [((1, 1, 2), "minecraft:redstone_wire")],
        6: [((1, 1, 3), RB)],
    },
)

PISTON_PUSH_PULL = Scenario(
    name="piston_push_pull",
    description=(
        "Sliding piston: a normal piston (row z=0) and a sticky piston (row z=2) push a stone "
        "block and retract; only the sticky one pulls it back. Moving blocks are compared "
        "including their block-entity progress."
    ),
    size=(5, 3),
    setup=[
        ((1, 1, 0), "minecraft:piston[facing=east]"),
        ((2, 1, 0), "minecraft:stone"),
        ((1, 1, 2), "minecraft:sticky_piston[facing=east]"),
        ((2, 1, 2), "minecraft:stone"),
    ],
    watch=[(x, 1, z) for z in (0, 2) for x in (1, 2, 3)],
    ticks=14,
    inputs={0: [((0, 1, 0), RB), ((0, 1, 2), RB)], 6: [((0, 1, 0), AIR), ((0, 1, 2), AIR)]},
)

STICKY_SHORT_PULSES = Scenario(
    name="sticky_short_pulses",
    description=(
        "Sticky pistons fed 1-, 2- and 3-tick pulses (placed/removed between ticks). A pulse "
        "that ends while the pushed block is still moving leaves it behind (event 2, open "
        "question OQ-3); longer pulses pull it back."
    ),
    size=(5, 5),
    setup=[((1, 1, z), "minecraft:sticky_piston[facing=east]") for z in (0, 2, 4)]
    + [((2, 1, z), "minecraft:stone") for z in (0, 2, 4)],
    watch=[(x, 1, z) for z in (0, 2, 4) for x in (1, 2, 3)],
    ticks=12,
    inputs={
        0: [((0, 1, 0), RB), ((0, 1, 2), RB), ((0, 1, 4), RB)],
        1: [((0, 1, 0), AIR)],
        2: [((0, 1, 2), AIR)],
        3: [((0, 1, 4), AIR)],
    },
)

PISTON_QC_BUD = Scenario(
    name="piston_qc_bud",
    description=(
        "Quasi-connectivity: a redstone block diagonally above a piston powers it, but the "
        "piston only notices after a neighbor update (a block placed beside it later)."
    ),
    size=(4, 3),
    setup=[((1, 1, 1), "minecraft:piston[facing=east]")],
    watch=[(1, 1, 1), (2, 1, 1)],
    ticks=10,
    inputs={0: [((0, 2, 1), RB)], 4: [((1, 1, 0), "minecraft:stone")]},
)

PISTON_DOOR = Scenario(
    name="piston_door",
    description=(
        "A 1x2 door: two stacked sticky pistons hold stone blocks. One redstone block powers "
        "the top piston directly and the bottom piston through quasi-connectivity; the top "
        "piston's own update wakes the bottom one in the same block-event phase."
    ),
    size=(5, 3),
    setup=[
        ((1, 1, 1), "minecraft:sticky_piston[facing=east]"),
        ((1, 2, 1), "minecraft:sticky_piston[facing=east]"),
        ((2, 1, 1), "minecraft:stone"),
        ((2, 2, 1), "minecraft:stone"),
    ],
    watch=[(x, y, 1) for y in (1, 2) for x in (1, 2, 3)],
    ticks=14,
    inputs={0: [((0, 2, 1), RB)], 6: [((0, 2, 1), AIR)]},
)

SLIME_BRANCH_PUSH = Scenario(
    name="slime_branch_push",
    description=(
        "Sticky piston (in the air) pushes a slime block that drags a stone on top and one at "
        "the side; a honey block beside the slime stays. Retraction pulls the group back."
    ),
    size=(5, 4),
    setup=[
        ((1, 3, 1), "minecraft:sticky_piston[facing=east]"),
        ((2, 3, 1), "minecraft:slime_block"),
        ((2, 4, 1), "minecraft:stone"),
        ((2, 3, 2), "minecraft:stone"),
        ((2, 3, 0), "minecraft:honey_block"),
    ],
    watch=[(x, y, z) for x in (2, 3) for y, z in ((3, 1), (4, 1), (3, 2), (3, 0))],
    ticks=12,
    inputs={0: [((0, 3, 1), RB)], 5: [((0, 3, 1), AIR)]},
)

PISTON_POPS_COMPONENTS = Scenario(
    name="piston_pops_components",
    description=(
        "A piston pushes a stone carrying dust and a wall torch on its far side; the dust "
        "pops when its support starts moving and the torch is destroyed by the push line."
    ),
    size=(6, 3),
    setup=[
        ((1, 1, 1), "minecraft:piston[facing=east]"),
        ((2, 1, 1), "minecraft:stone"),
        ((2, 2, 1), "minecraft:redstone_wire"),
        ((3, 1, 1), "minecraft:redstone_wall_torch[facing=east]"),
    ],
    watch=[(2, 1, 1), (3, 1, 1), (2, 2, 1), (3, 2, 1)],
    ticks=6,
    inputs={0: [((0, 1, 1), RB)]},
)

CLONE_INVERTER = Scenario(
    name="clone_inverter",
    description=(
        "A powered torch inverter (wire into a block, torch on top, lamp) at rest is copied "
        "with /clone; the copy settles, then its input is removed and both are compared."
    ),
    size=(5, 7),
    setup=[
        ((0, 1, 1), RB),
        ((1, 1, 1), "minecraft:redstone_wire"),
        ((2, 1, 1), "minecraft:stone"),
        ((2, 2, 1), "minecraft:redstone_torch"),
        ((3, 2, 1), "minecraft:redstone_lamp"),
    ],
    watch=[(1, 1, z) for z in (1, 5)] + [(2, 2, z) for z in (1, 5)] + [(3, 2, z) for z in (1, 5)],
    ticks=14,
    commands={3: [("clone", (0, 1, 0), (3, 2, 2), (0, 1, 4))]},
    inputs={8: [((0, 1, 5), AIR)]},
)

FILL_REMOVES_LINE = Scenario(
    name="fill_removes_line",
    description=(
        "/fill with air deletes the middle of a powered wire line: the rest depowers and a "
        "torch fed by the line's end turns back on."
    ),
    size=(9, 3),
    setup=[((0, 1, 1), RB)]
    + [((x, 1, 1), "minecraft:redstone_wire") for x in range(1, 7)]
    + [((7, 1, 1), "minecraft:stone"), ((7, 2, 1), "minecraft:redstone_torch")],
    watch=[(x, 1, 1) for x in range(1, 7)] + [(7, 2, 1)],
    ticks=8,
    commands={3: [("fill", (3, 1, 1), (4, 1, 1), "minecraft:air")]},
)

CLONE_MOVE_RUNNING = Scenario(
    name="clone_move_running",
    description=(
        "/clone ... replace move while circuits run: a delay-4 repeater is moved away from "
        "its input while its scheduled tick is pending (the tick is copied, so the moved "
        "repeater still turns on); a powered wire line is moved one block onto itself "
        "(overlap: the source is cleared first)."
    ),
    size=(8, 10),
    setup=[
        ((1, 1, 1), "minecraft:repeater[facing=west,delay=4]"),
        ((2, 1, 1), "minecraft:redstone_lamp"),
        ((0, 1, 7), RB),
        ((1, 1, 7), "minecraft:redstone_wire"),
        ((2, 1, 7), "minecraft:redstone_wire"),
        ((3, 1, 7), "minecraft:redstone_wire"),
        ((4, 1, 7), "minecraft:redstone_lamp"),
    ],
    watch=[(1, 1, 1), (2, 1, 1), (1, 1, 4), (2, 1, 4)] + [(x, 1, 7) for x in range(1, 6)],
    ticks=16,
    inputs={0: [((0, 1, 1), RB)]},
    commands={
        3: [("clone_move", (1, 1, 1), (2, 1, 1), (1, 1, 4))],
        5: [("clone_move", (1, 1, 7), (4, 1, 7), (2, 1, 7))],
    },
)

ALL = [
    LAMP_REDSTONE_BLOCK,
    TORCH_INVERTER,
    WIRE_LINE_LAMP,
    AND_GATE,
    TORCH_BURNOUT,
    TORCH_BURNOUT_UPDATE,
    GLASS_UP_NOT_DOWN,
    REPEATER_DELAYS,
    REPEATER_PULSE_EXTENSION,
    REPEATER_LOCK_PRIORITY,
    REPEATER_CHAIN,
    COMPARATOR_MODES,
    COMPARATOR_THROUGH_BLOCK,
    COMPARATOR_SIDE_TORCH,
    PISTON_PUSH_PULL,
    STICKY_SHORT_PULSES,
    PISTON_QC_BUD,
    PISTON_DOOR,
    SLIME_BRANCH_PUSH,
    PISTON_POPS_COMPONENTS,
    CLONE_INVERTER,
    FILL_REMOVES_LINE,
    CLONE_MOVE_RUNNING,
]

BY_NAME = {scenario.name: scenario for scenario in ALL}
