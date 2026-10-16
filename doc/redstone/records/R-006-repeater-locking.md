# R-006: what locks a repeater, and what a locked repeater does with its input

- **Date:** 2026-10-16 · **Simulator:** 864a6da · **Game:** Java 26.3
- **Script:** `experiments/redstone/R-006-repeater-locking.cli.txt` · **Status:** verified
- **Question:** Which neighbors at a repeater's side lock it? How fast does a lock take
  effect, what happens to input changes while locked, and to a change already waiting
  (a scheduled tick) when the lock arrives?
- **Hypothesis** ([[repeater]], `RepeaterBlock.isLocked`, `getAlternateSignal` with
  "diodes only"): only repeaters and comparators pointing into the side lock it, at any
  strength above 0; wire, torches, powered blocks, redstone blocks and observers do not.
  `locked` changes in the same tick as the side signal. A locked repeater's tick does
  nothing, so a waiting change is dropped; unlocking re-checks the input.
- **Setup:** a 48×48 world, rows 5 blocks apart: data lever `D_x` at (−1,1,z), repeater
  `Q_x` at (0,1,z) facing east, and at Q's south side (0,1,z+1): a repeater pointing
  north with a lever behind it (REP, PEND), a comparator reading a barrel of strength 1
  (COMP1), wire fed by a lever (WIRE), a wall torch (TORCH), a stone with a lever on top
  (BLOCK), a redstone block set at tick 2 (RBLOCK), an observer watching a lever (OBS).
- **Procedure:** the side sources on at tick 2 (PEND: at 1), the data levers on at 10
  (OBS: 3; PEND: 2), the REP and PEND side levers off at 20.
- **Observations** (`waves`, `changes`):

```
@Q_REP     locked at 4 (side repeater on), D at 10 ignored, unlocked at 22, powered at 24
@Q_COMP1   locked from the build (comparator output 1), never powered
@Q_WIRE / @Q_TORCH / @Q_BLOCK / @Q_RBLOCK   never locked, powered at 12
@Q_OBS     never locked (observer pulse at 4..5 on its side), powered at 5 (D at 3)
@Q_PEND    locked at 3; D at 2 would have switched it at 4: nothing; unlocked at 22, powered at 24
```

- **Result:** every hypothesis held.
- **Conclusion** (in [[components]], Repeater):
  - **Lockers:** a repeater or comparator pointing into the side, at any strength ≥ 1.
    Nothing else: not wire (R-004), torches, powered blocks, redstone blocks or observers.
  - The lock takes effect in the tick the side diode turns on (a lever → side repeater →
    lock 2 ticks after the lever).
  - While locked the output holds; input changes are **ignored, not remembered**. A
    change whose tick was already waiting when the lock came is **dropped**.
  - On unlock the repeater re-reads its input and switches after its delay (unlock at 22
    → on at 24 with delay 1).
  Confidence: high (V, S; G for locking by a repeater in EXP-010).
- **Used by:** [[circuits]] D latch (its setup time follows from the dropped tick).
