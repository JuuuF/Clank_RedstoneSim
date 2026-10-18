# Metrics and trade-offs

The mission's optimization goals measured per door, kept as separate objectives with no
combined score:

- **size**: the box around the contraption above the floor, the blocks in it, and the
  blocks the trim keeps;
- **components**: pistons and logic blocks;
- **speed**: ticks from the input flip until the doorway is closed / open for good. In
  parentheses: when it is first fully closed, if that is earlier. Sacred's doorway is
  full at 19, then moves blocks through it again until 38; the seamless door's whole
  panel makes one more move from 27 to 33;
- **robustness**: the shortest gap between the two flips from which every gap ends
  clean ([[robustness]]); how many of the 8 orientations work ([[symmetry]]).

`python -m tools.doorlab.metrics --extra WORLD …` (2026-10-19) writes
`experiments/doors/metrics.json` and the table below. "Dominated by" names a door of the
same doorway size that is at least as good in all six of box, blocks, close, open, safe
gap and orientations, and better in one. "Intent" is read from the title (spiral,
vault, staircase, seamless, glass, lamp, enchanting): a showpiece, where the look or
motion matters more than size or speed, and is not one of the measured objectives.

Columns: box (x × y × z) and its volume; blocks above the floor; blocks needed (after the
trim, [[robustness]]); pistons; logic blocks (wire, repeaters, comparators, observers,
torches, other signal parts); close and open in ticks; the safe gap in ticks;
orientations that work. LegDen's 7x7 and 8x8 stop part-way (backlog D3) and are being
removed from the dataset; their rows are only for completeness.

<!-- generated -->
| world | door | intent | box | volume | blocks | needed | pistons | logic | close | open | safe gap | orientations | dominated by |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `3x3-piston-door-sacredredstone` | 3x3 | functional | 2×8×7 | 112 | 48 | 48 | 10 | 19 | 38 (19) | 42 | 21 | 8 | – |
| `3x3-piston-door-zhus` | 3x3 | functional | 2×9×7 | 126 | 51 | 50 | 11 | 18 | 14 | 14 | 11 | 8 | – |
| `3x3-piston-door-monchicarp` | 3x3 | functional | 7×9×2 | 126 | 53 | 50 | 11 | 17 | 14 | 14 | 11 | 8 | `3x3-piston-door-zhus` |
| `3x3-spiral-piston-door-purplers` | 3x3 | showpiece | 3×8×7 | 168 | 81 | 70 | 12 | 34 | 19 | 21 | 12 | 8 | `3x3-piston-door-zhus` |
| `3x3-piston-door-rubik` | 3x3 | functional | 9×10×2 | 180 | 61 | 56 | 10 | 23 | 14 | 26 | 20 | 8 | `3x3-piston-door-zhus` |
| `3x3-piston-door-mumbo-jumbo` | 3x3 | functional | 3×9×7 | 189 | 87 | 78 | 12 | 25 | 10 | 24 | 10 | 8 | – |
| `3x3-flush-enchanting-table-door-purplers` | 3x3 | showpiece | 6×10×6 | 360 | 220 | 172 | 27 | 72 | 36 | 56 | 55 | 8 | `3x3-piston-door-mumbo-jumbo` |
| `3x3-seamless-glass-door-nile` | 3x3 | showpiece | 8×16×4 | 512 | 252 | 225 | 35 | 96 | 33 (27) | 39 | 16 | 8 | `3x3-piston-door-mumbo-jumbo` |
| `3x3-spiral-vault-door-lutal` | 3x3 | showpiece | 11×8×10 | 880 | 205 | 145 | 19 | 56 | 14 | 14 | 17 | 8 | `3x3-piston-door-zhus` |
| `3x3-flush-door-redsim` | 3x3 | functional | 17×8×13 | 1768 | 225 | 209 | 10 | 93 | 17 | 32 | 1 | 8 | – |
| `3x4-piston-door-pal1` | 3x4 | functional | 10×14×2 | 280 | 92 | 89 | 15 | 39 | 28 | 44 | 20 | 8 | – |
| `1-wide-hidden-staircase-purplers` | 4x4 | showpiece | 6×4×7 | 168 | 107 | 71 | 13 | 24 | 25 | – | 10 | 8 | – |
| `4x4-piston-door-sydney600mc` | 4x4 | functional | 3×9×10 | 270 | 125 | 113 | 24 | 38 | 16 | 26 | 19 | 8 | – |
| `4x4-sliding-piston-door-purplers` | 4x4 | functional | 20×11×4 | 880 | 401 | 381 | 66 | 112 | 9 | 4 | 9 | 8 | – |
| `4x4-piston-door-kwipla` | 4x4 | functional | 10×9×12 | 1080 | 158 | 142 | 28 | 57 | 27 | 39 | 25 | 8 | `4x4-piston-door-sydney600mc` |
| `5x5-vault-lamp-door-purplers` | 5x5 | showpiece | 5×12×11 | 660 | 373 | 322 | 46 | 114 | 7 | 2 | 10 | 6 | – |
| `5x5-vault-door-nile` | 5x5 | showpiece | 15×14×5 | 1050 | 425 | 387 | 69 | 154 | 9 | 9 | 13 | 8 | – |
| `5x5-glass-piston-door-ashevoy` | 5x5 | showpiece | 15×23×25 | 8625 | 1954 | – | 171 | 760 | 36 | 37 | 38 | 8 | `5x5-vault-door-nile` |
| `7x7-piston-door-legden` | 7x7 | functional | 23×13×13 | 3887 | 2368 | – | 447 | 938 | 18 | – | – | 1 | – |
| `8x8-piston-door-legden` | 8x8 | functional | 23×16×9 | 3312 | 1963 | – | 379 | 735 | 21 | – | – | 1 | – |
<!-- end generated -->

## Trade-offs

- **3x3, the one size with many designs (ten).** Four are not dominated, and each wins
  a different objective:
  - Sacred: the smallest box (112) and the fewest blocks (48, none spare), but the
    slowest compact door (closed for good at 38, open at 42, safe gap 21);
  - Zhus: nearly as small (126 / 51) and fast both ways (14 / 14), safe gap 11. It
    dominates five other 3x3s: monchiCARP (its mirror image with 2 more blocks),
    Rubik's door, Purplers' spiral, Lutal's vault (same speed in a 7 times larger box);
  - Mumbo Jumbo: the fastest close (10) and the shortest safe gap of the dataset's 3x3s
    (10), at 87 blocks (78 needed) and a slow open (24);
  - `door_3x3` (ours): the only door that is safe at any gap (a lockout), at 2.6 times
    Mumbo Jumbo's blocks and 9 times its box ([[demonstration]]).
- **The showpieces are all dominated, by functional doors, in these objectives.** The
  enchanting-table and seamless doors by Mumbo Jumbo's, the spiral and Lutal's vault by
  Zhus's, Ashevoy's glass door by Nile's vault. Their goal (a hidden table, a flush
  glass face, the motion) is not measured, so this only prices the look. Lutal's vault
  costs a 7 times larger box than Zhus's door for the same speed. The seamless face
  costs about 3 times Mumbo Jumbo's blocks and box (252 / 512 vs 87 / 189), 23 ticks of
  close and 15 of open.
- **4x4:** Sydney's door beats Kwipla's in five objectives and ties in the sixth (box
  270 vs 1080, 125 vs 158 blocks, 16 / 26 vs 27 / 39 ticks, safe gap 19 vs 25, both
  work in all 8 orientations). Purplers' sliding door is the fastest
  4x4 (9 / 4) and has the shortest safe gap in the dataset (9). It pays for that with the
  largest 4x4 build (box 880, 401 blocks, 66 pistons). The staircase has no open time:
  its open state is a staircase, not an empty doorway.
- **5x5:** the vault lamp door is smaller, faster and safer than Nile's vault (box 660
  vs 1050, 7 / 2 vs 9 / 9 ticks, safe gap 10 vs 13). It still does not dominate it:
  the lamp door works in only 6 of 8 orientations, because a same-tick double-extender
  race goes the other way in two of them ([[../records/R-027-double-extender-order]]).
  This is the one place where orientation robustness decides.
- **Components scale with the doorway, and with the look.** The dataset's compact 3x3s use 10–12
  pistons for 9 cells and 17–25 logic blocks. The showpiece 3x3s use 12–35 pistons and
  34–96 logic blocks. The 4x4s use 13–66 pistons for 16 cells, the 5x5s 46–171 for 25.
- **Speed does not cost size in the compact 3x3s:** Zhus's door is both one of the
  smallest and one of the fastest. Its rivals trade along only one axis: Sacred is
  smaller and slower; Mumbo Jumbo closes faster and opens slower in a larger box.
- **Input safety is not an objective any dataset design optimized.** Every safe gap
  but the sliding door's is 10 ticks or more. The one door safe at gap 1 is the
  project's own. What sets the safe gap, and what a too-short gap does, is in
  [[robustness]].
