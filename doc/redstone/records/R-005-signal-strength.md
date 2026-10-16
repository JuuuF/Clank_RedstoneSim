# R-005: signal strength through blocks and components; comparator modes and side inputs; container levels

- **Date:** 2026-10-16 · **Simulator:** 864a6da · **Game:** Java 26.3
- **Script:** `experiments/redstone/R-005-signal-strength.cli.txt` · **Status:** verified
- **Question:** How does a signal's strength (1–15) change through a solid block, wire,
  repeaters and comparators? What do compare and subtract mode output, and what counts
  as a comparator side input? How many items give each comparator reading?
- **Hypothesis** ([[comparator]], [[power-queries]], [[analog-sources]]): a block powered
  with N by a comparator powers wire beside it with N (Q1 in [[backlog]]); wire loses 1
  per block; a comparator passes its input strength unchanged, a repeater always gives
  15. Compare: rear if rear ≥ side else 0; subtract: max(rear − side, 0). Side inputs:
  wire (its power, any shape), redstone blocks (15), diodes pointing in, other sources
  only by their *direct* signal (torches and levers: 0); the larger side wins.
  Containers: 1 + ⌊14 × fullness⌋ when not empty, fullness = Σ(count / max stack) / slots.
  An observer's 2-tick pulse on a side input is lost (R-003).
- **Setup:** a 64×64 world, four columns (the script's header describes every row):
  - x=−28: barrel 7 → comparator → stone → 2 wires (A1); barrel 7 → comparator → 2
    wires (A2); barrel 1 → comparator → repeater → wire (A3); barrel 7 → comparator →
    comparator → wire (A4); barrel 7 → comparator → stone → comparator (A5); lever →
    6 wires (power 10 at the end) → stone → comparator (A6); barrel 9 → stone →
    comparator (A7); the same with a lever on top of the stone (A8).
  - x=−12: rear barrel R → comparator (mode) with a side comparator reading barrel S
    pointing into its south side: (R, S, mode) = (12, 5, subtract), (12, 5, compare),
    (5, 12, compare), (7, 7, compare), (7, 7, subtract), (5, 12, subtract) (B1–B6).
  - x=4: a subtracting comparator with a redstone block behind it (rear 15), and at its
    side: wire fed by a lever (C1); comparators 5 (south) and 9 (north) (C2); a standing
    torch (C3); a redstone block set at tick 2 (C4); a lever on the floor (C5); a
    repeater from a lever (C6); a stone with a lever on top (C7); wire at power 5 (C8);
    an observer watching a lever (C9).
  - x=20: barrels (27 slots), hoppers (5), droppers (9) with stone or ender pearls at the
    thresholds, each read by a comparator.
- **Observations** (`waves`, values in hex; levers and the redstone block at tick 2):

```
@A1_COMP / @A1_W1 / @A1_W2        7 / 7 / 6        comparator 7 → block → wire 7, 6
@A2_W1 / @A2_W2                   7 / 6
@A3_COMP / @A3_W                  1 / f            repeater restores 15
@A4_COMP2 / @A4_W                 7 / 7            comparator → comparator keeps 7
@A5_COMP2                         7                comparator reads the block's 7
@A6_WEND / @A6_COMP               ..aaaa / ....aa  wire 10 → block → comparator 10
@A7_COMP                          9                barrel read through stone
@A8_COMP                          9999ffff         the lever's 15 on the stone wins
@B1..@B6                          7, c, 0, 7, 0, 0
@C1 wire 15                       ffff.........    15 − 15
@C2 sides 5 and 9                 6                15 − max(5, 9)
@C3 torch / @C5 lever / @C7 powered stone / @C9 observer pulse   f (no side input)
@C4 redstone block                ffff.........
@C6 repeater                      ffffff.......
@C8 wire 5                        a                15 − 5
barrel 1, 64, 123 items → 1; 124 → 2; 1727 → 14; 1728 (full) → 15
barrel 1 ender pearl → 1; 31 and 32 pearls → 2 (16 per slot)
hopper 22 → 1; 23 → 2; 320 → 15. dropper 41 → 1; 42 → 2; 576 → 15
```

- **Result:** every hypothesis held. (The pearl rows were chosen with a wrong threshold in
  mind: 31 pearls is already 1.94 slots, so 2; the formula predicts both.)
- **Conclusion** (in [[signals]], section Signal strength):
  - A block takes the strength of what powers it: a comparator at 7 into a block makes
    wire beside it 7 (answers Q1); a comparator behind a block powered by wire at 10
    reads 10.
  - Wire −1 per block; comparators keep the strength (compare mode, no side input);
    repeaters always output 15.
  - Compare mode: output = rear if rear ≥ side, else 0. Subtract: max(rear − side, 0).
  - Side inputs: wire at its power, redstone blocks 15, repeaters and comparators
    pointing in, the larger of the two sides. Not side inputs: torches, levers, powered
    solid blocks. An observer's 2-tick pulse on a side is lost like on the rear.
  - A comparator reads a container (or other analog block) directly behind it, or
    behind one solid block, unless that block itself has power 15.
  - Containers: strength = 1 + ⌊14 × fullness⌋ (0 when empty), fullness = Σ(count / max
    stack size) / slots. Thresholds: [[signals]].
  Confidence: high (V, S; G in EXP-012, 013, 014, 024, 038, 045).
- **Open:** item frames (not simulated, L), cauldrons, jukeboxes, other analog sources
  ([[analog-sources]] lists the simulated ones).
- **Used by:** [[signals]], [[components]], analog circuits in [[circuits]].
