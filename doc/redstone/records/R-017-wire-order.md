# R-017: races decided by wire update order depend on where the build stands

- **Date:** 2026-10-16 · **Simulator:** 864a6da · **Game:** Java 26.3
- **Script:** `experiments/redstone/R-017-wire-order.cli.txt` · **Status:** verified (Q6)
- **Question:** When one wire change powers two components in the same moment, which
  reacts first? Is it the same for an identical build placed elsewhere?
- **Hypothesis** ([[redstone-wire]], Q-WIRE-HASH): when wire power changes, the game
  collects the positions to update in a Java `HashSet<BlockPos>` and updates them in that
  set's iteration order, which depends on the coordinates' hash codes. Two pistons fed by
  one wire network queue their block events in that order; the first queued wins a race
  for one cell (R-012). So the winner can change when the same build is moved.
- **Setup:** a 112×112 world. One build, copied to many positions: two pistons facing
  each other across a cell M (west piston pushes a stone, east piston a wool block), each
  standing on a stone; one lever drives a wire bus (row z+2) whose two ends turn north
  into those stones (row z+1). Exploration (scratch worlds): 32 copies at x = −42…42,
  z = −26…26, then z = −5…1 one by one. The script keeps six copies.
- **Procedure:** every copy's lever on at tick 2; read M at tick 8.
- **Observations:** the winner never depended on x; it flipped with z:

```
copy at z (bus row z+2)   −26  −12  −6  −5  −4  −3 | −2  −1   0   1   5  10  26
winner                      E    E   E   E   E   E |  W   W   W   W   W   W   W
(E: the east piston's wool fills M; W: the west piston's stone; tested at several x each)
```

  The flip is where the bus row crosses from z = −1 to z = 0 (copy z = −3 → −2).
- **Result:** as predicted: the outcome depends on position.
- **Conclusion** (in [[timing]] and the [[circuits]] composition rules):
  - **Never build anything whose result depends on which of several components fed by
    the same wire change reacts first.** The order follows the hash of the wire
    positions: a build that works here may fail when moved, rotated or mirrored.
  - Make such orders explicit: different delays (a repeater on one branch), or separate
    sources whose order you control (R-012's pistons on two levers were deterministic).
  - The same applies to anything else updated by a wire change in one moment (several
    torches, comparators, observers on one network schedule their ticks in that order,
    which decides ties at equal priority, R-012).
  Confidence: high (V; S Q-WIRE-HASH; the simulator's hash order is checked against a
  real JDK, and wire grids match the game, G EXP-029, EXP-031).
- **Used by:** [[timing]], [[circuits]] composition rules.
