# R-021: how long may a chain of latches be unlocked?

- **Date:** 2026-10-16 · **Simulator:** 864a6da · **Game:** Java 26.3
- **Script:** `experiments/redstone/R-021-unlock-window.cli.txt` · **Status:** verified
- **Question:** A row of repeater latches (each locked by a side repeater) shares one
  lock bus. If the bus is released for w ticks, how far does data move along the row?
  (This is the clocking problem of a shift register.)
- **Hypothesis** ([[R-006-repeater-locking]], [[R-012-same-tick-order]]): released at
  t, the lock repeaters turn off at t+2; each latch whose input differs switches at t+4;
  its right neighbor would switch at t+6. The lock repeaters turn on again at t+w+2 and,
  in a tie, before the latches (priority −3 vs −1/−2); a locked latch drops its waiting
  change. So: w ≤ 2 → the locks return at t+4, before the first switch: nothing moves;
  w = 3, 4 → one stage; w ≥ 5 → the second stage switches at t+6 before the lock (t+7):
  two stages.
- **Setup:** a 64×64 world, four copies (w = 2, 3, 4, 5) of: a data lever, four
  repeaters facing east with wire between, a lock repeater facing south into each
  latch's north side, a lock bus wire feeding them from a lever (on = locked).
- **Procedure:** data on at 4, off at 34; the bus switched off for w ticks at 10, 30 and
  50 (the data lever's change at 34 falls between windows).
- **Observations** (`waves`):

```
w=2   Q0..Q3 never change
w=3   Q0 on 14..53, Q1 on from 34, Q2 on from 54, Q3 never   (one stage per window)
w=4   the same as w=3
w=5   Q0 on 14, Q1 on 16 (same window), …, Q3 on from 36       (two stages per window)
```

- **Result:** as predicted.
- **Conclusion** (in [[components]] Repeater, [[circuits]] Shift register): a shared lock
  bus released for **3 or 4 ticks** moves a latch chain exactly one stage; 2 ticks or less
  moves nothing; 5 or more lets data race through. A rising-edge detector (4-tick pulse)
  inverted by a torch gives a 4-tick window per clock edge.
  Confidence: high (V, S).
- **Used by:** [[circuits]] (Shift register).
