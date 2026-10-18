# R-028: a lamp can turn off and on within one tick

- **Date:** 2026-10-19 · **Simulator:** 6b2b5f7 · **Game:** Java 26.3
- **Script:** `experiments/redstone/R-028-lamp-flicker.cli.txt` · **Status:** verified, game EXP-076 (match)
- **Question:** In SacredRedstone's 3x3 door a corner block is pulled out and pushed back
  in while the door closes: the observer powering its piston fires, though the lamp it
  watches is lit at every tick ([[../doors/analyses/3x3-piston-door-sacredredstone]]).
  Can a lamp change twice within one tick, and when?
- **Hypothesis** (decompiled source): a lit lamp that loses its power schedules its
  turn-off 4 ticks later (`RedstoneLampBlock.neighborChanged`, normal priority); when the
  tick runs it turns off if it is still unpowered (`tick`). An unlit lamp that gets power
  turns on at once. Ticks due in the same game tick run by priority, then in the order
  they were scheduled (`LevelTicks`). An observer schedules its pulse at normal
  priority; a repeater at high priority or above (`DiodeBlock.checkTickOnNeighbor`). So
  if the power goes and comes back from an observer exactly 4 ticks later, the lamp's
  earlier-scheduled turn-off runs first, the observer's pulse relights it in the same
  tick, and an observer watching the lamp sees both changes. With a repeater as the
  power, the repeater runs first and the lamp stays lit.
- **Setup:** four copies of observer O (watching block X) powering lamp L, with observer
  W watching L; in (d), L is powered by a repeater (delay 1) that a redstone block
  switches.
- **Procedure:** X is set at 2 and changed again at 8 (a), 7 (b), 9 (c), so O's pulses
  are 4–5 and 10–11, 9–10, 11–12; in (d) the redstone block is set at 2, removed at 4,
  set again at 8 (the repeater on 4–5 and from 10). `check` of the target `flicker`;
  `changes` of L and W.
- **Observations:**

```
(a) gap 6: L lit 4..15 at every tick; W pulses 6..7, 12..13, 18..19  (12: the flicker at 10)
(b) gap 5: L lit 4..14;               W pulses 6..7, 17..18
(c) gap 7: L off at 10 only, on at 11; W pulses 6..7, 12..13, 19..20
(d) repeater: L lit from 4;           W pulses 6..7 only
```

- **Result:** as predicted, 4 of 4 cases.
- **Conclusion** (in [[../components]], Redstone lamp):
  - **A lamp re-powered exactly 4 ticks after it lost its power turns off and on within
    one tick if the new power comes from a normal-priority tick (an observer)**. No tick
    shows the lamp off, but an observer watching it fires. A re-power 1 tick earlier
    keeps it lit, 1 tick later shows it off for a tick.
  - A repeater's re-power at that tick runs first (higher priority): no flicker.
  - Design rule: don't watch a lamp with an observer when it can be pulsed at exactly
    its delay, or expect the extra pulse (Sacred's corner block blinks for 8 ticks).
- **Used by:** [[../doors/analyses/3x3-piston-door-sacredredstone]].
