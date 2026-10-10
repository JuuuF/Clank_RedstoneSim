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

ALL = [
    LAMP_REDSTONE_BLOCK,
    TORCH_INVERTER,
    WIRE_LINE_LAMP,
    AND_GATE,
    TORCH_BURNOUT,
    TORCH_BURNOUT_UPDATE,
    GLASS_UP_NOT_DOWN,
]

BY_NAME = {scenario.name: scenario for scenario in ALL}
