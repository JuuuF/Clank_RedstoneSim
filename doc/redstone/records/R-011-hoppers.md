# R-011: hoppers and droppers as timing elements

- **Date:** 2026-10-16 · **Simulator:** 864a6da · **Game:** Java 26.3
- **Script:** `experiments/redstone/R-011-hoppers.cli.txt` · **Status:** verified
- **Question:** How fast does a hopper empty, and how long does an item take through a
  chain of hoppers? What does locking do to a running transfer? (Items make long,
  countable delays: timers, clocks, counters.)
- **Hypothesis** ([[hopper]]): a hopper moves one item per 8 ticks (cooldown 8), in the
  block-entity phase; a locked hopper's cooldown runs down to 0, so it moves on the first
  tick after unlocking. An item arriving in an empty hopper waits 8 ticks, or 7 if that
  hopper already ticked in this game tick at or after the sender (Q-HOPPER-COOLDOWN-7). A
  dropper fires 4 ticks after its rising edge (R-001).
- **Setup:** a 48×48 world: hoppers with 1, 2, 5 stone (D1, D2, D5) facing a barrel,
  locked by a lever beside them, a comparator reading each; a lever, a dropper with one
  stone, three hoppers in a row and a barrel (CHAIN); a hopper with 5 stone (RELOCK).
- **Procedure:** the D levers off (unlock) at 2; the chain's lever on at 2; RELOCK
  unlocked at 2, locked at 12, unlocked at 30.
- **Observations** (`waves`; hoppers show their comparator reading, barrels too):

```
@H_D1 hopper       111.........           empty at 3; comparator off at 5
@H_D2 hopper       11111111111.....       empty at 11; comparator off at 13
@H_D5 hopper       1111…1111 (to 34) .    empty at 35; comparator off at 37
@H1 / @H2 / @H3    item at 6..12 / 13..19 / 20..26; barrel from 27
@H_RELOCK          items out at 3, 11; locked 12..29; out at 31, 39, 47: empty at 47
```

- **Result:** as predicted.
- **Conclusion** (in [[components]], Hopper; [[timing]]):
  - **Drain:** an unlocked hopper with N items is empty **1 + 8·(N − 1) ticks** after it is
    unlocked (first item at once, then one per 8 ticks); a comparator reading it turns off
    2 ticks later. 5 slots × 64 = 320 items → about 2550 ticks (2 minutes) from one hopper.
  - **Travel:** an item spends **7 ticks** in each hopper of a straight chain (the
    receiving hopper ticks after the sender in the same tick, so 1 of its 8 cooldown ticks
    passes at once); the dropper feeding the chain adds 4.
  - **Locking** stops a hopper between moves without losing anything; unlocked, it moves
    on the very next tick (its cooldown kept running down).
  - The comparator reading of a hopper only steps at the thresholds (1–22 items → 1,
    [[signals]] table), so for timing use "empty or not" (comparator off) or many items.
  Confidence: high (V, S; G in EXP-038, 039, 040).
- **Open:** throughput of longer chains with several items (G EXP-038: one item per 8
  ticks); hopper clocks: [[circuits]].
- **Used by:** [[components]], [[circuits]] (hopper clock).
