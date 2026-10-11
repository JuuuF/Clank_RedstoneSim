"""Random circuits for differential testing against the real game (seeded, reproducible).

``fuzz_<seed>`` builds a dense random circuit from every block the simulator supports
(dust, torches, repeaters, comparators, lamps, pistons, slime, honey, barrels, lecterns,
redstone blocks, solid and transparent blocks) on a few layers, then toggles redstone-block
inputs at the border at random ticks, including 0-tick pulses (placed and removed at the
same tick boundary). Every block of the volume is compared tick by tick.

The point is coverage of update orders no one would think of: any difference from the game
is a bug in the simulator (or in the harness).
"""

from __future__ import annotations

import random
from collections.abc import Callable
from typing import Any

from tools.gameserver.compare import Scenario

RB = "minecraft:redstone_block"
AIR = "minecraft:air"
HORIZONTAL = ("north", "east", "south", "west")
ALL_SIX = (*HORIZONTAL, "up", "down")

Entry = tuple[Any, ...]


def _palette(rng: random.Random) -> list[tuple[int, Callable[[], Entry | str]]]:
    def facing() -> str:
        return rng.choice(HORIZONTAL)

    return [
        (30, lambda: "minecraft:redstone_wire"),
        (14, lambda: "minecraft:stone"),
        (5, lambda: "minecraft:glass"),
        (7, lambda: "minecraft:redstone_torch"),
        (4, lambda: f"minecraft:redstone_wall_torch[facing={facing()}]"),
        (8, lambda: f"minecraft:repeater[facing={facing()},delay={rng.randint(1, 4)}]"),
        (
            6,
            lambda: (
                f"minecraft:comparator[facing={facing()},"
                f"mode={rng.choice(('compare', 'subtract'))}]"
            ),
        ),
        (7, lambda: "minecraft:redstone_lamp"),
        (3, lambda: f"minecraft:piston[facing={rng.choice(ALL_SIX)}]"),
        (3, lambda: f"minecraft:sticky_piston[facing={rng.choice(ALL_SIX)}]"),
        (2, lambda: "minecraft:slime_block"),
        (1, lambda: "minecraft:honey_block"),
        (1, lambda: RB),
        (
            2,
            lambda: (
                f"minecraft:barrel[facing={rng.choice(ALL_SIX)}]",
                {"Items": [{"Slot": 0, "id": "minecraft:redstone", "count": rng.randint(1, 64)}]},
            ),
        ),
        (
            1,
            lambda: (
                f"minecraft:lectern[facing={facing()},has_book=true]",
                {
                    "Book": {"id": "minecraft:writable_book", "count": 1, "pages": 9},
                    "Page": rng.randint(0, 8),
                },
            ),
        ),
    ]


def fuzz_scenario(seed: int, size: int = 10, layers: int = 2, ticks: int = 50) -> Scenario:
    rng = random.Random(seed)
    palette = _palette(rng)
    weights = [weight for weight, _ in palette]
    setup: list[Entry] = []
    for y in range(1, layers + 1):
        density = 0.65 if y == 1 else 0.3
        for z in range(1, size - 1):
            for x in range(1, size - 1):
                if rng.random() >= density:
                    continue
                made = rng.choices(palette, weights)[0][1]()
                if isinstance(made, tuple):
                    setup.append(((x, y, z), made[0], made[1]))
                else:
                    setup.append(((x, y, z), made))
    inputs: dict[int, list[tuple[Any, str]]] = {}
    for z in rng.sample(range(1, size - 1), 4):
        pos = (0, 1, z)
        on = False
        for tick in sorted(rng.sample(range(0, ticks - 6), 8)):
            if rng.random() < 0.25:  # a 0-tick pulse: on and off at the same boundary
                inputs.setdefault(tick, []).extend([(pos, RB), (pos, AIR)])
            else:
                on = not on
                inputs.setdefault(tick, []).append((pos, RB if on else AIR))
    # Live edits inside the circuit: redstone blocks, air or random blocks (no data).
    plain = [(w, make) for w, make in palette if not isinstance(make(), tuple)]
    for _ in range(10):
        tick = rng.randrange(1, ticks - 4)
        pos = (rng.randrange(1, size - 1), rng.randint(1, layers), rng.randrange(1, size - 1))
        roll = rng.random()
        if roll < 0.35:
            state = RB
        elif roll < 0.6:
            state = AIR
        else:
            made = rng.choices(plain, [w for w, _ in plain])[0][1]()
            state = made if isinstance(made, str) else made[0]
        inputs.setdefault(tick, []).append((pos, state))
    watch = [
        (x, y, z)
        for y in range(1, layers + 2)
        for z in range(1, size - 1)
        for x in range(1, size - 1)
    ]
    return Scenario(
        name=f"fuzz_{seed}",
        description=(
            f"Random circuit #{seed}: {len(setup)} blocks of every supported kind on {layers} "
            f"layers, four redstone-block inputs toggled at random ticks (some 0-tick), and "
            f"ten random live edits inside the circuit."
        ),
        size=(size, size),
        setup=setup,
        watch=watch,
        ticks=ticks,
        inputs=inputs,
    )
