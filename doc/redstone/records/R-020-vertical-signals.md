# R-020: sending a signal up

- **Date:** 2026-10-16 · **Simulator:** 864a6da · **Game:** Java 26.3
- **Script:** `experiments/redstone/R-020-vertical-signals.cli.txt` · **Status:** verified
- **Question:** Which ways of carrying a signal upward exist, how fast are they, and
  what do they pass (levels, pulses, polarity)?
- **Hypothesis:** wire staircases are instant and lose 1 per step (R-004); a wire ladder
  on glass is the same going up but one-way (R-019); a torch tower (a torch strongly
  powers the block above it; the next torch stands on that block) adds 2 ticks per
  torch and inverts each time; an observer column (each watching the one below) adds 2
  ticks per observer and turns every change into one 2-tick pulse (R-008).
- **Setup:** a 48×48 world: a 6-step wire staircase on stones (lamp at the top); a torch
  tower of 4 torches over 8 blocks (stone, torch, stone, torch, …; the lever hangs on
  the bottom stone); 6 observers stacked facing down above a wire; a 4-step wire
  staircase on glass.
- **Procedure:** all levers on at 2, off at 30; `waves` of the tops.
- **Observations:**

```
wire staircase, top wire        ..9999…9999 (2..29)        instant, power 9 after 6 steps
glass ladder, top wire          ..bbbb…bbbb (2..29)        instant, power 11 after 4 steps
torch tower T1 / T2 / T3 / T4   off 4 / on 6 / off 8 / on 10; back at 32 / 34 / 36 / 38
observer column, top            pulses 14..15 and 42..43   (2 ticks per observer, each edge)
```

- **Result:** as predicted.
- **Conclusion** (in [[signals]], vertical table):

| Method | Delay up | What arrives | Down too? | Size |
|---|---|---|---|---|
| Wire staircase on solid blocks | 0 | the level, −1 per step | yes (R-004) | one block wider per step |
| Wire ladder on glass, glowstone, top slabs | 0 | the level, −1 per step | **no** (one-way, R-019) | as above |
| Torch tower (block, torch, block, torch …) | 2 per torch = 1 per block | the level, inverted at each torch | no (torches power up) | 1×1 column |
| Observer column | 2 per block | one 2-tick pulse per change | yes, with observers facing up | 1×1 column |

  Use a repeater after an observer column or torch tower if the signal must be clean
  15; mind torch burnout for fast signals through towers (R-007).
  Confidence: high (V).
- **Not tested here:** sticky pistons moving a redstone block up (a block-moving
  elevator), bubble columns (water: not simulated, L).
- **Used by:** [[signals]].
