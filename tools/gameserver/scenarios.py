"""Comparison scenarios, simplest first. Coordinates are relative (y=1: above the floor).

Inputs are redstone blocks placed/removed with ``/setblock`` between ticks, because the
dedicated server has no player to flip a lever. ``inputs[t]`` is applied after ``t`` ticks.
"""

from __future__ import annotations

from typing import Any

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


def _items(total: int, item: str = "minecraft:redstone", stack: int = 64) -> dict[str, Any]:
    """Barrel NBT holding ``total`` items in full stacks plus one partial stack."""
    counts = [stack] * (total // stack) + ([total % stack] if total % stack else [])
    return {"Items": [{"Slot": i, "id": item, "count": c} for i, c in enumerate(counts)]}


BARREL_FILLS = [1, 123, 124, 863, 864, 1727, 1728]
BARREL_SIGNALS = Scenario(
    name="barrel_signals",
    description=(
        "Comparators read barrels at the fill thresholds of signals 1/2, 7/8 and 14/15 "
        "(64-stacks), and 14 slots of ender pearls (16-stacks); later /item replace adds "
        "one item (123 -> 124: signal 1 -> 2) and empties a slot (1728 -> 1664: 15 -> 14)."
    ),
    size=(2 * len(BARREL_FILLS) + 1, 3),
    setup=[((2 * i, 1, 1), "minecraft:comparator[facing=north]") for i in range(8)]
    + [
        ((2 * i, 1, 0), "minecraft:barrel[facing=up]", _items(total))
        for i, total in enumerate(BARREL_FILLS)
    ]
    + [((14, 1, 0), "minecraft:barrel[facing=up]", _items(14 * 16, "minecraft:ender_pearl", 16))],
    watch=[(2 * i, 1, 1) for i in range(8)],
    ticks=12,
    commands={
        3: [("item", (2, 1, 0), 26, ("minecraft:redstone", 1))],
        6: [("item", (12, 1, 0), 0, (None, 1))],
    },
)

LECTERN_PAGES = [(1, 0), (2, 0), (2, 1), (3, 1), (15, 0), (15, 7), (15, 14), (10, 3), (10, 20),
                 (100, 50), (100, 99)]  # fmt: skip
LECTERN_SIGNALS = Scenario(
    name="lectern_signals",
    description=(
        "Comparators read lecterns holding writable books of N pages open at page p "
        "(floor(p / (N - 1) * 14) + 1, page clamped to the book), a lectern without a book "
        "(0) and one whose state says has_book=false although it holds a book (0)."
    ),
    size=(2 * len(LECTERN_PAGES) + 5, 3),
    setup=[
        ((2 * i, 1, 1), "minecraft:comparator[facing=north]") for i in range(len(LECTERN_PAGES) + 2)
    ]
    + [
        (
            (2 * i, 1, 0),
            "minecraft:lectern[has_book=true]",
            {"Book": {"id": "minecraft:writable_book", "count": 1, "pages": n}, "Page": page},
        )
        for i, (n, page) in enumerate(LECTERN_PAGES)
    ]
    + [
        ((2 * len(LECTERN_PAGES), 1, 0), "minecraft:lectern"),
        (
            (2 * len(LECTERN_PAGES) + 2, 1, 0),
            "minecraft:lectern[has_book=false]",
            {"Book": {"id": "minecraft:writable_book", "count": 1, "pages": 5}, "Page": 2},
        ),
    ],
    watch=[(2 * i, 1, 1) for i in range(len(LECTERN_PAGES) + 2)]
    + [(2 * i, 1, 0) for i in range(len(LECTERN_PAGES) + 2)],
    ticks=4,
)

CLONE_STRICT_BUD = Scenario(
    name="clone_strict_bud",
    description=(
        "A budded piston (powered only by quasi-connectivity, never updated) is cloned: "
        "with /clone ... strict the copy stays budded (no updates); with a normal /clone the "
        "final neighbor updates make the copy extend; a strict move leaves both budded."
    ),
    size=(4, 18),
    setup=[((1, 1, z), "minecraft:piston[facing=east]") for z in (1, 7, 13)]
    + [((1, 3, z), RB) for z in (1, 7, 13)],
    watch=[(x, 1, z) for z in (1, 4, 7, 10, 13, 16) for x in (1, 2)],
    ticks=8,
    commands={
        2: [
            ("clone_strict", (1, 1, 1), (1, 3, 1), (1, 1, 4)),
            ("clone", (1, 1, 7), (1, 3, 7), (1, 1, 10)),
            ("clone_move_strict", (1, 1, 13), (1, 3, 13), (1, 1, 16)),
        ]
    },
)

# ------------------------------------------------------------------ stress tests
# A 0-tick input: placed and removed at the same tick boundary (two /setblock in a row).
ZERO_TICK_INPUTS = Scenario(
    name="zero_tick_inputs",
    description=(
        "0-tick pulses (a redstone block placed and removed at the same boundary) next to a "
        "piston, a sticky piston with a block, a repeater, a comparator, a torch on a block, "
        "a lamp and a dust line; then a normal pulse for contrast."
    ),
    size=(16, 4),
    setup=[
        ((1, 1, 1), "minecraft:piston[facing=up]"),
        ((3, 1, 1), "minecraft:sticky_piston[facing=up]"),
        ((3, 2, 1), "minecraft:stone"),
        ((5, 1, 1), "minecraft:repeater[facing=west,delay=2]"),
        ((6, 1, 1), "minecraft:redstone_lamp"),
        ((8, 1, 1), "minecraft:comparator[facing=west]"),
        ((9, 1, 1), "minecraft:redstone_lamp"),
        ((11, 1, 1), "minecraft:stone"),
        ((11, 2, 1), "minecraft:redstone_torch"),
        ((13, 1, 1), "minecraft:redstone_lamp"),
        ((14, 1, 2), "minecraft:redstone_wire"),
        ((14, 1, 3), "minecraft:redstone_wire"),
    ],
    watch=[(1, 1, 1), (1, 2, 1), (3, 1, 1), (3, 2, 1), (3, 3, 1), (5, 1, 1), (6, 1, 1)]
    + [(8, 1, 1), (9, 1, 1), (11, 2, 1), (13, 1, 1), (14, 1, 2), (14, 1, 3)],
    ticks=24,
    inputs={
        2: [
            ((1, 1, 0), RB), ((1, 1, 0), AIR),
            ((3, 1, 0), RB), ((3, 1, 0), AIR),
            ((4, 1, 1), RB), ((4, 1, 1), AIR),
            ((7, 1, 1), RB), ((7, 1, 1), AIR),
            ((10, 1, 1), RB), ((10, 1, 1), AIR),
            ((12, 1, 1), RB), ((12, 1, 1), AIR),
            ((14, 1, 1), RB), ((14, 1, 1), AIR),
        ],
        10: [((1, 1, 0), RB), ((3, 1, 0), RB), ((4, 1, 1), RB), ((10, 1, 1), RB)],
        12: [((1, 1, 0), AIR), ((3, 1, 0), AIR), ((4, 1, 1), AIR), ((10, 1, 1), AIR)],
    },
)  # fmt: skip

PISTON_RACE = Scenario(
    name="piston_race",
    description=(
        "Two pistons push into the same gap in the same tick; which one is powered first "
        "(the order of block events) decides who wins. Row 2 swaps the order. Then a piston "
        "is powered, unpowered and powered again at one boundary (block-event dedup)."
    ),
    size=(8, 8),
    setup=[
        ((0, 1, 1), "minecraft:piston[facing=east]"),
        ((1, 1, 1), "minecraft:stone"),
        ((3, 1, 1), "minecraft:oak_planks"),
        ((4, 1, 1), "minecraft:piston[facing=west]"),
        ((0, 1, 4), "minecraft:piston[facing=east]"),
        ((1, 1, 4), "minecraft:stone"),
        ((3, 1, 4), "minecraft:oak_planks"),
        ((4, 1, 4), "minecraft:piston[facing=west]"),
        ((2, 1, 7), "minecraft:sticky_piston[facing=east]"),
        ((3, 1, 7), "minecraft:oak_planks"),
    ],
    watch=[(x, 1, z) for z in (1, 4, 7) for x in range(0, 7)],
    ticks=12,
    inputs={
        1: [((0, 2, 1), RB), ((4, 2, 1), RB), ((4, 2, 4), RB), ((0, 2, 4), RB)],
        2: [((1, 1, 7), RB), ((1, 1, 7), AIR), ((1, 1, 7), RB)],
        6: [((0, 2, 1), AIR), ((4, 2, 1), AIR), ((4, 2, 4), AIR), ((0, 2, 4), AIR)],
        8: [((1, 1, 7), AIR)],
    },
)

WIRE_GRID = Scenario(
    name="wire_grid",
    description=(
        "A 6×6 dust carpet powered from its corners and edges at different ticks, with "
        "lamps around it: dust update order, power levels and shapes in a dense grid."
    ),
    size=(9, 9),
    setup=[((x, 1, z), "minecraft:redstone_wire") for z in range(1, 7) for x in range(1, 7)]
    + [((7, 1, 3), "minecraft:redstone_lamp"), ((3, 1, 7), "minecraft:redstone_lamp")],
    watch=[(x, 1, z) for z in range(1, 8) for x in range(1, 8)],
    ticks=20,
    inputs={
        0: [((0, 1, 1), RB)],
        3: [((6, 1, 0), RB)],
        6: [((0, 1, 1), AIR), ((0, 1, 5), RB)],
        9: [((7, 1, 6), RB), ((0, 1, 5), AIR)],
        12: [((6, 1, 0), AIR)],
        15: [((7, 1, 6), AIR)],
    },
)

TORCH_TOWER = Scenario(
    name="torch_tower",
    description=(
        "A torch tower (block, torch, block, ... four stages, lamp on top) driven by short "
        "and long pulses, then toggled every tick until the bottom torch burns out."
    ),
    size=(4, 3),
    # The input drives a repeater into the base block (a redstone block next to it would
    # not power it: it gives no strong power).
    setup=[((1, 1, 1), "minecraft:repeater[facing=west,delay=1]"), ((2, 1, 1), "minecraft:stone")]
    + [((2, 2 * i, 1), "minecraft:redstone_torch") for i in range(1, 5)]
    + [((2, 2 * i + 1, 1), "minecraft:stone") for i in range(1, 4)]
    + [((2, 9, 1), "minecraft:redstone_lamp")],
    watch=[(1, 1, 1)] + [(2, y, 1) for y in range(2, 10)],
    ticks=90,
    inputs={
        0: [((0, 1, 1), RB)],
        1: [((0, 1, 1), AIR)],
        6: [((0, 1, 1), RB)],
        16: [((0, 1, 1), AIR)],
        # 3 ticks on, 3 off: the torch can follow (it re-checks 2 ticks after a change), and
        # 8 turn-offs within 60 ticks burn it out.
        **{t: [((0, 1, 1), RB if (t - 24) % 6 == 0 else AIR)] for t in range(24, 78, 3)},
    },
)

# ------------------------------------------------------------------ observers
OBSERVER_CLOCK = Scenario(
    name="observer_clock",
    description="Two observers facing each other (a clock), each with a lamp behind it.",
    size=(6, 3),
    setup=[
        ((2, 1, 1), "minecraft:observer[facing=east]"),
        ((3, 1, 1), "minecraft:observer[facing=west]"),
        ((1, 1, 1), "minecraft:redstone_lamp"),
        ((4, 1, 1), "minecraft:redstone_lamp"),
    ],
    watch=[(x, 1, 1) for x in range(1, 5)],
    ticks=30,
)

OBSERVER_DETECTS = Scenario(
    name="observer_detects",
    description=(
        "Observers watching dust that gets powered, a lamp, a piston extending and a chain "
        "of observers fired by a block placed in front of the first; lamps and dust behind."
    ),
    size=(12, 10),
    setup=[
        ((1, 1, 1), "minecraft:redstone_wire"),
        ((2, 1, 1), "minecraft:redstone_wire"),
        ((2, 1, 2), "minecraft:observer[facing=north]"),
        ((2, 1, 3), "minecraft:redstone_lamp"),
        ((5, 1, 1), "minecraft:redstone_lamp"),
        ((5, 1, 2), "minecraft:observer[facing=north]"),
        ((5, 1, 3), "minecraft:redstone_wire"),
        ((5, 1, 4), "minecraft:redstone_wire"),
        ((8, 1, 1), "minecraft:piston[facing=up]"),
        ((8, 1, 2), "minecraft:observer[facing=north]"),
        ((8, 1, 3), "minecraft:redstone_lamp"),
        ((1, 1, 6), "minecraft:observer[facing=west]"),
        ((2, 1, 6), "minecraft:observer[facing=west]"),
        ((3, 1, 6), "minecraft:observer[facing=west]"),
        ((4, 1, 6), "minecraft:observer[facing=west]"),
        ((5, 1, 6), "minecraft:redstone_lamp"),
    ],
    watch=[(x, 1, z) for z in (1, 2, 3, 4) for x in (1, 2, 5, 8)]
    + [(8, 2, 1)]
    + [(x, 1, 6) for x in range(0, 6)],
    ticks=24,
    inputs={
        2: [((0, 1, 1), RB), ((4, 1, 1), RB), ((7, 1, 1), RB), ((0, 1, 6), "minecraft:stone")],
        12: [((0, 1, 1), AIR), ((4, 1, 1), AIR), ((7, 1, 1), AIR)],
    },
)

OBSERVER_PUSHED = Scenario(
    name="observer_pushed",
    description=(
        "A sticky piston moves an observer back and forth while the observer is pulsing "
        "(onPlace and removal rules), with dust behind the observer."
    ),
    size=(8, 4),
    setup=[
        ((1, 1, 1), "minecraft:sticky_piston[facing=east]"),
        ((2, 1, 1), "minecraft:observer[facing=north]"),
        ((2, 1, 0), "minecraft:stone"),
        ((2, 1, 2), "minecraft:redstone_wire"),
        ((3, 1, 2), "minecraft:redstone_wire"),
        ((4, 1, 2), "minecraft:redstone_lamp"),
    ],
    watch=[(x, 1, z) for z in (0, 1, 2) for x in range(1, 5)],
    ticks=24,
    inputs={
        1: [((2, 1, 0), AIR)],
        2: [((0, 1, 1), RB)],
        3: [((0, 1, 1), AIR)],
        9: [((0, 1, 1), RB)],
        15: [((0, 1, 1), AIR)],
    },
)

# ------------------------------------------------------------------ rails
RAIL_SHAPES = Scenario(
    name="rail_shapes",
    description=(
        "Plain rails choose their shapes from their neighbors: a straight line, a corner, a "
        "T junction that switches when a redstone block next to it powers it, and a slope "
        "up a step."
    ),
    size=(12, 10),
    setup=[((x, 1, 1), "minecraft:rail") for x in range(1, 5)]
    + [((1, 1, 4), "minecraft:rail"), ((2, 1, 4), "minecraft:rail"), ((2, 1, 5), "minecraft:rail")]
    + [((7, 1, 1), "minecraft:rail"), ((8, 1, 1), "minecraft:rail"), ((9, 1, 1), "minecraft:rail")]
    + [((8, 1, 2), "minecraft:rail")]
    + [((5, 1, 8), "minecraft:stone"), ((5, 2, 8), "minecraft:rail"), ((4, 1, 8), "minecraft:rail")]
    + [((3, 1, 8), "minecraft:rail")],
    watch=[(x, 1, z) for z in (1, 2, 4, 5, 8) for x in range(0, 11)] + [(5, 2, 8)],
    ticks=10,
    inputs={2: [((8, 1, 0), RB)], 6: [((8, 1, 0), AIR)]},
)

POWERED_RAILS = Scenario(
    name="powered_rails",
    description=(
        "A line of 12 powered rails fed from one end (power reaches 8 rails past the "
        "powered one), a line of activator rails, a mixed line (powered rails do not pass "
        "power through activator rails), then the inputs are removed."
    ),
    size=(16, 8),
    setup=[((x, 1, 1), "minecraft:powered_rail[shape=east_west]") for x in range(1, 13)]
    + [((x, 1, 3), "minecraft:activator_rail[shape=east_west]") for x in range(1, 13)]
    + [((x, 1, 5), "minecraft:powered_rail[shape=east_west]") for x in (1, 2, 3, 5, 6)]
    + [((4, 1, 5), "minecraft:activator_rail[shape=east_west]")],
    watch=[(x, 1, z) for z in (1, 3, 5) for x in range(1, 13)],
    ticks=12,
    inputs={
        2: [((0, 1, 1), RB), ((0, 1, 3), RB), ((0, 1, 5), RB)],
        7: [((0, 1, 1), AIR), ((0, 1, 3), AIR), ((0, 1, 5), AIR)],
    },
)

# ------------------------------------------------------------------ target block
TARGET_BLOCK = Scenario(
    name="target_block",
    description=(
        "Dust passing a target block bends into it; an arrow hitting the target's top center "
        "powers it (15) for 20 ticks, a snowball for 8; the dust line and a lamp follow. A "
        "target placed with power is reset to 0."
    ),
    size=(10, 8),
    setup=[
        ((2, 1, 1), "minecraft:target"),
        ((1, 1, 2), "minecraft:redstone_wire"),
        ((2, 1, 2), "minecraft:redstone_wire"),
        ((3, 1, 2), "minecraft:redstone_wire"),
        ((4, 1, 2), "minecraft:redstone_lamp"),
        ((7, 1, 1), "minecraft:target"),
        ((7, 1, 2), "minecraft:redstone_wire"),
        ((7, 1, 3), "minecraft:redstone_wire"),
        ((7, 1, 4), "minecraft:redstone_lamp"),
        ((7, 1, 6), "minecraft:target[power=12]"),
    ],
    watch=[(x, 1, z) for z in (1, 2, 3, 4, 6) for x in (1, 2, 3, 4, 7)],
    ticks=34,
    commands={2: [("hit", (2, 1, 1), "arrow")], 4: [("hit", (7, 1, 1), "snowball")]},
)


def _slots(*stacks: tuple[str, int]) -> dict[str, Any]:
    return {
        "Items": [
            {"Slot": slot, "id": item, "count": count} for slot, (item, count) in enumerate(stacks)
        ]
    }


REDSTONE = "minecraft:redstone"
PEARL = "minecraft:ender_pearl"


def _comparators_with_lamps(xs: tuple[int, ...]) -> list[tuple[Any, ...]]:
    """Comparators at z=2 reading the block at z=1, lamps at z=3."""
    return [((x, 1, 2), "minecraft:comparator[facing=north]") for x in xs] + [
        ((x, 1, 3), "minecraft:redstone_lamp") for x in xs
    ]


HOPPER_CHAIN = Scenario(
    name="hopper_chain",
    description=(
        "A barrel feeds a chain of three hoppers into a second barrel: 5 redstone dust, then "
        "3 ender pearls (stack size 16), one item per 8 ticks; the third hopper ticks before "
        "the second (placed first). Comparators read every hopper and the target barrel; "
        "contents and cooldowns are compared every tick."
    ),
    size=(7, 5),
    setup=[
        ((1, 2, 1), "minecraft:barrel[facing=up]", _slots((REDSTONE, 5), (PEARL, 3))),
        ((1, 1, 1), "minecraft:hopper[facing=east]"),
        ((3, 1, 1), "minecraft:hopper[facing=east]"),
        ((2, 1, 1), "minecraft:hopper[facing=east]"),
        ((4, 1, 1), "minecraft:barrel[facing=up]"),
        *_comparators_with_lamps((1, 2, 3, 4)),
    ],
    watch=[(1, 2, 1)] + [(x, 1, z) for z in (1, 2, 3) for x in (1, 2, 3, 4)],
    ticks=90,
    watch_items=True,
)

HOPPER_LOCK = Scenario(
    name="hopper_lock",
    description=(
        "Redstone locks hoppers (enabled=false): a redstone block beside the first hopper from "
        "tick 10 to 30, a 0-tick lock on the second (placed and removed at tick 40), a "
        "redstone block on top of the second from tick 50 to 60 (it cannot pull then either). "
        "An observer watching the first hopper sees each lock change."
    ),
    size=(7, 5),
    setup=[
        ((2, 2, 1), "minecraft:barrel[facing=up]", _slots((REDSTONE, 20))),
        ((2, 1, 1), "minecraft:hopper[facing=east]"),
        ((3, 1, 1), "minecraft:hopper[facing=east]"),
        ((4, 1, 1), "minecraft:barrel[facing=up]"),
        *_comparators_with_lamps((2, 3, 4))[:3],
        ((1, 1, 1), "minecraft:observer[facing=east]"),
        ((0, 1, 1), "minecraft:redstone_lamp"),
    ],
    watch=[(2, 2, 1), (3, 2, 1), (2, 1, 0), (3, 1, 0)]
    + [(x, 1, z) for z in (1, 2) for x in (0, 1, 2, 3, 4)],
    ticks=80,
    inputs={
        10: [((2, 1, 0), RB)],
        30: [((2, 1, 0), AIR)],
        40: [((3, 1, 0), RB), ((3, 1, 0), AIR)],
        50: [((3, 2, 1), RB)],
        60: [((3, 2, 1), AIR)],
    },
    watch_items=True,
)

HOPPER_CLOCK = Scenario(
    name="hopper_clock",
    description=(
        "Two hoppers facing each other pass 4 items back and forth (cooldowns 7/8 by ticker "
        "order); next to them a barrel above a down-facing hopper feeds a second facing pair, "
        "whose lower hopper also pulls from the hopper above. Comparators and lamps follow."
    ),
    size=(10, 5),
    setup=[
        ((2, 1, 1), "minecraft:hopper[facing=east]", _slots((REDSTONE, 4))),
        ((3, 1, 1), "minecraft:hopper[facing=west]"),
        ((6, 3, 1), "minecraft:barrel[facing=up]", _slots((REDSTONE, 6))),
        ((6, 2, 1), "minecraft:hopper[facing=down]"),
        ((7, 1, 1), "minecraft:hopper[facing=west]"),
        ((6, 1, 1), "minecraft:hopper[facing=east]"),
        *_comparators_with_lamps((2, 3, 6, 7)),
    ],
    watch=[(6, 3, 1), (6, 2, 1)] + [(x, 1, z) for z in (1, 2, 3) for x in (2, 3, 6, 7)],
    ticks=80,
    watch_items=True,
)

HOPPER_ITEM_REPLACE = Scenario(
    name="hopper_item_replace",
    description=(
        "`/item replace` puts 64 dust into an idle hopper, a barrel and a hopper facing a "
        "barrel. The barrel's comparator updates at once (setChanged); the idle hopper's "
        "does not (HopperBlockEntity.setItem has no setChanged) until a block placed next to "
        "the comparator updates it; the third hopper's comparator updates when the hopper "
        "moves its first item."
    ),
    size=(10, 5),
    setup=[
        ((1, 1, 1), "minecraft:hopper[facing=down]"),
        ((4, 1, 1), "minecraft:barrel[facing=up]"),
        ((7, 1, 1), "minecraft:hopper[facing=east]"),
        ((8, 1, 1), "minecraft:barrel[facing=up]"),
        *_comparators_with_lamps((1, 4, 7)),
    ],
    watch=[(x, 1, z) for z in (1, 2, 3) for x in (0, 1, 4, 7, 8)],
    ticks=16,
    inputs={10: [((0, 1, 2), "minecraft:stone")]},
    commands={
        2: [
            ("item", (1, 1, 1), 0, (REDSTONE, 64)),
            ("item", (4, 1, 1), 0, (REDSTONE, 64)),
            ("item", (7, 1, 1), 0, (REDSTONE, 64)),
        ]
    },
    watch_items=True,
)

NOTE_BLOCKS = Scenario(
    name="note_blocks",
    description=(
        "Note blocks: instrument from the block below (stone, glass, planks, wool), "
        "powered from a redstone block and through a repeater; an observer watches one "
        "(each powered change is a state change) and lights a lamp."
    ),
    size=(8, 4),
    setup=[
        ((1, 1, 0), "minecraft:note_block"),
        ((2, 0, 1), "minecraft:glass"),
        ((2, 1, 1), "minecraft:note_block"),
        ((3, 0, 2), "minecraft:oak_planks"),
        ((3, 1, 2), "minecraft:note_block"),
        ((4, 0, 3), "minecraft:white_wool"),
        ((4, 1, 3), "minecraft:note_block[note=7]"),
        ((2, 1, 0), "minecraft:observer[facing=west]"),
        ((3, 1, 0), "minecraft:redstone_lamp"),
        ((5, 1, 3), "minecraft:repeater[facing=west,delay=2]"),
    ],
    watch=[(1, 1, 0), (2, 1, 1), (3, 1, 2), (4, 1, 3), (2, 1, 0), (3, 1, 0), (5, 1, 3)],
    ticks=24,
    inputs={
        2: [((0, 1, 0), RB), ((1, 1, 1), RB)],
        6: [((6, 1, 3), RB)],
        9: [((0, 1, 0), AIR)],
        12: [((3, 2, 2), RB)],  # power from above, with a block on top: no note
        15: [((1, 1, 1), AIR), ((6, 1, 3), AIR)],
        18: [((3, 2, 2), AIR)],
    },
)

COPPER_BULBS = Scenario(
    name="copper_bulbs",
    description=(
        "Copper bulbs as T flip-flops: each rising edge toggles lit; a comparator reads "
        "15 from a lit bulb into a lamp; bulbs never conduct (a bulb between a redstone "
        "block and a lamp leaves it off); placing a bulb next to power lights it."
    ),
    size=(8, 4),
    setup=[
        ((1, 1, 0), "minecraft:copper_bulb"),
        ((2, 1, 0), "minecraft:comparator[facing=west]"),
        ((3, 1, 0), "minecraft:redstone_lamp"),
        ((1, 1, 2), "minecraft:oxidized_copper_bulb"),
        ((2, 1, 2), "minecraft:redstone_lamp"),
        ((5, 1, 0), "minecraft:waxed_exposed_copper_bulb"),
    ],
    watch=[(1, 1, 0), (2, 1, 0), (3, 1, 0), (1, 1, 2), (2, 1, 2), (5, 1, 0), (6, 1, 2)],
    ticks=30,
    inputs={
        2: [((0, 1, 0), RB)],
        5: [((0, 1, 0), AIR)],
        8: [((0, 1, 0), RB), ((0, 1, 2), RB)],
        11: [((0, 1, 0), AIR)],
        14: [((0, 1, 0), RB), ((5, 1, 1), RB)],
        17: [((0, 1, 0), AIR), ((5, 1, 1), AIR)],
        20: [((6, 1, 3), RB), ((6, 1, 2), "minecraft:weathered_copper_bulb")],
    },
)

DROPPERS = Scenario(
    name="droppers",
    description=(
        "A dropper pushes one item per rising edge into a hopper chain ending in a chest; "
        "a dispenser with one stack fires only after a later neighbor update (power at "
        "the block above: quasi-connectivity); comparators read both."
    ),
    size=(8, 5),
    setup=[
        ((1, 1, 1), "minecraft:dropper[facing=east]", _slots((REDSTONE, 3))),
        ((2, 1, 1), "minecraft:hopper[facing=east]"),
        ((3, 1, 1), "minecraft:chest[facing=north]"),
        ((1, 1, 2), "minecraft:comparator[facing=north]"),
        ((3, 1, 2), "minecraft:comparator[facing=north]"),
        ((5, 1, 1), "minecraft:dispenser[facing=up]", _slots((PEARL, 2))),
        ((5, 1, 2), "minecraft:comparator[facing=north]"),
    ],
    watch=[(1, 1, 1), (2, 1, 1), (3, 1, 1), (1, 1, 2), (3, 1, 2), (5, 1, 1), (5, 1, 2)],
    ticks=40,
    watch_items=True,
    inputs={
        2: [((0, 1, 1), RB)],
        8: [((0, 1, 1), AIR)],
        12: [((0, 1, 1), RB), ((6, 2, 1), RB)],  # (6,2,1) powers the air above the dispenser
        16: [((0, 1, 1), AIR)],
        22: [((6, 1, 1), "minecraft:stone")],  # a neighbor update: the dispenser notices
        30: [((6, 2, 1), AIR), ((6, 1, 1), AIR)],
    },
)

CHESTS = Scenario(
    name="chests",
    description=(
        "A barrel feeds a double chest through a hopper; comparators read each half (one "
        "54-slot container); a block on top of one half makes both comparators read 0; a "
        "trapped chest is a signal source of 0 (wire beside it points at it)."
    ),
    size=(8, 5),
    setup=[
        ((1, 2, 1), "minecraft:barrel[facing=up]", _slots((REDSTONE, 64), (REDSTONE, 64))),
        ((1, 1, 1), "minecraft:hopper[facing=east]"),
        ((2, 1, 1), "minecraft:chest[facing=north,type=left]"),
        ((3, 1, 1), "minecraft:chest[facing=north,type=right]"),
        ((2, 1, 2), "minecraft:comparator[facing=north]"),
        ((3, 1, 2), "minecraft:comparator[facing=north]"),
        ((2, 1, 3), "minecraft:redstone_lamp"),
        ((3, 1, 3), "minecraft:redstone_lamp"),
        ((6, 1, 1), "minecraft:trapped_chest[facing=north]"),
        ((6, 1, 2), "minecraft:redstone_wire"),
    ],
    watch=[(1, 1, 1), (2, 1, 1), (3, 1, 1), (2, 1, 2), (3, 1, 2), (2, 1, 3), (3, 1, 3), (6, 1, 2)],
    ticks=60,
    watch_items=True,
    inputs={30: [((3, 2, 1), "minecraft:stone")], 45: [((3, 2, 1), AIR)]},
)

PRESSURE_PLATES = Scenario(
    name="pressure_plates",
    description=(
        "Entities on pressure plates: an armor stand (a mob) presses a stone and an oak "
        "plate, an item only the oak plate; weighted plates count entities. Each lamp "
        "shows its plate; plates release at their next recheck after the entities go."
    ),
    size=(10, 4),
    setup=[
        ((1, 1, 1), "minecraft:stone_pressure_plate"),
        ((1, 1, 2), "minecraft:redstone_lamp"),
        ((3, 1, 1), "minecraft:oak_pressure_plate"),
        ((3, 1, 2), "minecraft:redstone_lamp"),
        ((5, 1, 1), "minecraft:stone_pressure_plate"),
        ((5, 1, 2), "minecraft:redstone_lamp"),
        ((7, 1, 1), "minecraft:light_weighted_pressure_plate"),
        ((7, 1, 2), "minecraft:comparator[facing=south]"),
        ((7, 1, 3), "minecraft:redstone_lamp"),
    ],
    watch=[(1, 1, 1), (1, 1, 2), (3, 1, 1), (3, 1, 2), (5, 1, 1), (5, 1, 2), (7, 1, 1), (7, 1, 2)],
    ticks=60,
    commands={
        2: [
            ("summon", (1, 1, 1), "armor_stand"),
            ("summon", (3, 1, 1), "item"),
            ("summon", (5, 1, 1), "item"),  # stone plates ignore items
            ("summon", (7, 1, 1), "armor_stand"),
            ("summon", (7, 1, 1), "armor_stand"),
        ],
        9: [("kill", (1, 1, 1))],
        17: [("kill", (3, 1, 1)), ("kill", (7, 1, 1))],
        30: [("summon", (3, 1, 1), "armor_stand")],
        41: [("kill", (3, 1, 1))],
    },
)

PISTON_SCHEDULED_PULSES = Scenario(
    name="piston_scheduled_pulses",
    description=(
        "Sticky pistons driven by pulses that start and end in scheduled ticks "
        "(isHandlingTick): a 2-tick input pulse through a 1-tick repeater, an observer's "
        "2-tick pulse, and an observer pulse shortened by a repeater; does each piston "
        "push, pull back, or spit its block?"
    ),
    size=(8, 7),
    setup=[
        # Row z=0: input pulse → repeater (delay 1) → sticky piston pushing stone east.
        ((1, 1, 0), "minecraft:repeater[facing=west,delay=1]"),
        ((2, 1, 0), "minecraft:sticky_piston[facing=east]"),
        ((3, 1, 0), "minecraft:stone"),
        # Row z=2: an observer watching (0,1,2) powers a sticky piston.
        ((1, 1, 2), "minecraft:observer[facing=west]"),
        ((2, 1, 2), "minecraft:sticky_piston[facing=east]"),
        ((3, 1, 2), "minecraft:stone"),
        # Row z=4: observer → repeater (delay 1) → sticky piston.
        ((1, 1, 4), "minecraft:observer[facing=west]"),
        ((2, 1, 4), "minecraft:repeater[facing=west,delay=1]"),
        ((3, 1, 4), "minecraft:sticky_piston[facing=east]"),
        ((4, 1, 4), "minecraft:stone"),
    ],
    watch=[
        (1, 1, 0),
        (2, 1, 0),
        (3, 1, 0),
        (4, 1, 0),
        (1, 1, 2),
        (2, 1, 2),
        (3, 1, 2),
        (4, 1, 2),
        (1, 1, 4),
        (2, 1, 4),
        (3, 1, 4),
        (4, 1, 4),
        (5, 1, 4),
    ],
    ticks=30,
    inputs={
        2: [((0, 1, 0), RB)],
        4: [((0, 1, 0), AIR)],
        6: [((0, 1, 2), "minecraft:stone"), ((0, 1, 4), "minecraft:stone")],
        16: [((0, 1, 2), AIR), ((0, 1, 4), AIR)],
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
    BARREL_SIGNALS,
    LECTERN_SIGNALS,
    CLONE_STRICT_BUD,
    ZERO_TICK_INPUTS,
    PISTON_RACE,
    WIRE_GRID,
    TORCH_TOWER,
    OBSERVER_CLOCK,
    OBSERVER_DETECTS,
    OBSERVER_PUSHED,
    RAIL_SHAPES,
    POWERED_RAILS,
    TARGET_BLOCK,
    HOPPER_CHAIN,
    HOPPER_LOCK,
    HOPPER_CLOCK,
    HOPPER_ITEM_REPLACE,
    NOTE_BLOCKS,
    COPPER_BULBS,
    DROPPERS,
    CHESTS,
    PRESSURE_PLATES,
    PISTON_SCHEDULED_PULSES,
]

BY_NAME = {scenario.name: scenario for scenario in ALL}


def lookup(name: str) -> Scenario:
    """A scenario by name; ``fuzz_<seed>`` builds a random circuit (``tools.gameserver.fuzz``)."""
    if name.startswith("fuzz_"):
        from tools.gameserver.fuzz import fuzz_scenario

        return fuzz_scenario(int(name.removeprefix("fuzz_")))
    return BY_NAME[name]
