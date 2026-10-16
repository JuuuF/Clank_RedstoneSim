# R-002: which sources power a solid block, strongly or weakly

- **Date:** 2026-10-16 · **Simulator:** 864a6da · **Game:** Java 26.3
- **Script:** `experiments/redstone/R-002-what-powers-a-block.cli.txt` · **Status:** verified
- **Question:** Which neighbors make a solid block (stone) powered, and is that power
  *strong* (the block then powers wire beside it) or *weak* (it powers components only)?
  What does a powered block drive, and does power chain from block to block?
- **Hypothesis:** strong: a lever or button attached to the block, a torch under it, a
  repeater, comparator or observer pointing into it. Weak: wire pointing into it or lying
  on it. Not at all: a lever on the floor beside it, a torch standing beside it or
  hanging on it, wire running past it, a redstone block beside it. A powered block never
  powers the next block. A weakly powered block still switches torches, repeaters and
  pistons.
- **Setup:** a 48×48 world. Each row has a stone block B and two probes: a **lamp**
  beside B (lit = B is powered at all) and a **wire** beside B (power 15 = B is strongly
  powered; wire ignores blocks powered only by wire). Column x=0, B at (0,1,z), lamp at
  (0,1,z+1), wire at (1,1,z):

| Row z | Source |
|---|---|
| −20 | lever on top of B (`face=floor` on B) |
| −16 | lever on B's west face (`face=wall facing=west`) |
| −12 | lever on the floor west of B (attached to the floor) |
| −8 | stone button on B's west face |
| −4 | standing torch under B (B at y=2, probes at y=2, the probe wire on glass) |
| 0 | standing torch west of B |
| 4, 8, 12 | repeater, comparator, observer at (−1,1,z) pointing east into B, lever west of it |
| 16 | lever and two wires pointing east into B |
| 20 | wire running north–south past B's west face (lever at its north end) |

Column x=12, B at (12,1,z):

| Row z | Case |
|---|---|
| −20 | wire on top of B (fed by a lever hanging on a floating stone at its north); probe wire west of B, with a stone above the probe so the top wire cannot step down to it |
| −16 | lever on top of B; a second stone C east of B with a lamp and a wire beside C |
| −12 | redstone block set west of B at tick 2; a control lamp beside the redstone block |
| −8 | wall torch hanging on B's east face; control lamp east of the torch |
| 0, 4, 8 | lever and two wires into B; on B: a wall torch, a repeater `out=east`, a piston beside B |

- **Procedure:** all levers flipped at tick 2, the button pressed at tick 2, the redstone
  block set at tick 2; `run 12`, `waves`.
- **Observations** (`waves` ticks 0..12, abridged):

```
@LAMP_LEVER_TOP / @WIRE_LEVER_TOP      ..fffffffffff / ..fffffffffff
@LAMP_LEVER_WALL / @WIRE_LEVER_WALL    ..fffffffffff / ..fffffffffff
@LAMP_LEVER_NEAR / @WIRE_LEVER_NEAR    ............. / .............
@LAMP_BUTTON / @WIRE_BUTTON            ..fffffffffff / ..fffffffffff
@LAMP_TORCH_BELOW / @WIRE_TORCH_BELOW  fffffffffffff / fffffffffffff
@LAMP_TORCH_BESIDE / @WIRE_TORCH_BESIDE ............ / .............
@LAMP_REPEATER / @WIRE_REPEATER        ....fffffffff / ....fffffffff
@LAMP_COMPARATOR / @WIRE_COMPARATOR    ....fffffffff / ....fffffffff
@LAMP_OBSERVER / @WIRE_OBSERVER        ....ffffff... / ....ff.......
@LAMP_WIRE_INTO / @WIRE_WIRE_INTO      ..fffffffffff / .............
@LAMP_WIRE_BESIDE / @WIRE_WIRE_BESIDE  ............. / .............
@LAMP_WIRE_TOP / @WIRE_WIRE_TOP        ..fffffffffff / .............
@LAMP_NO_CHAIN_B / @LAMP_NO_CHAIN_C    ..fffffffffff / .............
@LAMP_RBLOCK_CONTROL / @LAMP_RBLOCK    ..fffffffffff / .............
@LAMP_TORCH_CONTROL / @LAMP_TORCH_ON_B fffffffffffff / .............
@WEAK_TORCH                            ffff.........
@WEAK_REPEATER                         ....fffffffff
@WEAK_PISTON                           ...ffffffffff
```

- **Result:** every hypothesis held.
- **Conclusion:** the power rules in [[signals]]:
  - *Strong power into a block* comes from a lever or button **attached to it**, a torch
    **under** it, and a repeater, comparator or observer **pointing into** it.
  - *Weak power* comes from wire **pointing into** it or **lying on** it: components
    around the block react (lamp, torch on it, repeater, piston), wire beside it does not.
  - *No power:* a lever or button beside it but attached elsewhere, a torch beside it or
    hanging on it, wire running past it (not pointing in), a redstone block beside it
    (the redstone block powers components and wire directly, never a block).
  - Power does not chain from block to block.
  Confidence: high (V; S in [[power-queries]]; G for torches and wire in EXP-002, 004,
  007).
- **Open:** wire *shapes* decide what "pointing into" means (dot, line, cross, steps):
  R-004. Strength through a block (a block takes the strongest strong input, so 15 from a
  lever, or the repeater's 15) is I here; a comparator into a block with less than 15 is
  in [[backlog]].
- **Used by:** [[signals]], every circuit that powers a component through a block.
