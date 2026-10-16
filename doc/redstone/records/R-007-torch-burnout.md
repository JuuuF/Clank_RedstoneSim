# R-007: torch burnout: when it happens and how a torch recovers

- **Date:** 2026-10-16 · **Simulator:** 864a6da · **Game:** Java 26.3
- **Script:** `experiments/redstone/R-007-torch-burnout.cli.txt` · **Status:** verified
- **Question:** How often can a torch switch before it burns out? Is the limit sharp?
  When and how does a burnt-out torch come back?
- **Hypothesis** ([[redstone-torch]], `RedstoneTorchBlock.tick`, `isToggledTooFrequently`):
  every turn-off is recorded with its game time; records older than 60 ticks are
  forgotten; a turn-off that brings the count to 8 burns the torch out: it stays off and
  schedules a re-check 160 ticks later, which lights it again if its block is unpowered.
  So a torch turned off every P ticks burns out iff 7·P ≤ 60 (P ≤ 8). The re-check is a
  scheduled tick: if the torch already has a tick waiting, the request is dropped
  (Q-SCHED-DEDUP). A torch whose own turn-off unpowers its block at once (an instant wire
  loop) schedules a 2-tick re-check first, which finds it still "too frequent" and
  schedules nothing: it stays out until some later update (Q-TORCH-BURNOUT-STUCK).
- **Setup:** a 48×48 world:

| Row | Build |
|---|---|
| P8 (z=−20) | stone, lever on top, wall torch on its east face; the lever is on for 4 ticks every 8 ticks, 8 times (ticks 2..62) |
| P9 (z=−16) | the same, every 9 ticks, 10 times (ticks 2..87) |
| INST (z=−10) | wall torch on a stone; 10 wires from the torch loop back into the stone (period 4) |
| KICK (z=−2) | as INST; a stone is placed beside the torch at tick 200 |
| DELAY (z=6) | wall torch on a stone; its wire loops back through a delay-1 repeater (period 8) |

- **Observations** (`changes` of the torches):

```
P8     off 4, 12, …, 52, 60 (8th) → stays off → lit at 220 (60 + 160)
P9     off 4, 13, …, 85 (10 times) → lit again at 89 and every time: no burnout
INST   off 2, 6, …, 30 (8th) → off until the end (460)
KICK   off at 30 → lit at 202 (2 ticks after the stone was placed) → period 4 → off at 232 (8th) → stays off
DELAY  off 3, 11, …, 59 (8th) → lit at 219 (59 + 160) → off at 279 (8th) → lit at 439 → …
```

- **Result:** every hypothesis held.
- **Conclusion** (in [[components]], Redstone torch, and [[timing]]):
  - **Limit:** a torch burns out on its 8th turn-off within 60 ticks. Turned off every
    **8** ticks (or faster) it burns out; every **9** ticks or slower it never does.
    So the fastest safe torch oscillation has a period of 9 ticks; a 4-tick torch clock
    burns out after 30 ticks, an 8-tick one after 59.
  - **Burnt out:** the torch stays off and ignores its input. 160 ticks after burning out
    it lights again if its block is unpowered at that moment.
  - **Stuck:** if the torch's own turn-off immediately unpowers its block (a pure wire
    feedback loop), the 160-tick restart is lost and it stays off **until another update
    reaches it** (any block change next to it); then it restarts (and will burn out again
    if nothing changed).
  - Design rule: avoid torches in loops faster than period 9; use the comparator
    [[circuits]] Clock (no torch) instead.
  Confidence: high (V, S; G in EXP-005, EXP-006, EXP-030).
- **Open:** a torch with several burnt-out torches nearby: the records are per position,
  so neighbors do not interact (S, not tested).
- **Used by:** [[components]], [[circuits]] (clock choice).
