# R-029: a pull that meets a moving block pulls nothing

- **Date:** 2026-10-20 · **Simulator:** 919b1fe · **Game:** Java 26.3
- **Script:** `experiments/redstone/R-029-pull-meets-moving-piston.cli.txt` (world
  `…redsim.json` beside it) · **Status:** verified (EXP-079)
- **Question:** Two door explanations found that a stack's pull must not come while its
  rider is still retracting: Lutal's hub stack (repeater delay 4 exact, delay 3 or 2
  leaves the rider one cell out, [[../doors/analyses/3x3-spiral-vault-door-lutal]]) and
  Rubik's center stack (delay 3 pushes the center block back,
  [[../doors/analyses/3x3-piston-door-rubik]]). R-026 says a *push* into a moving block
  is refused until the block lands. What does a sticky piston's *pull* do when the block
  in front of its head is still moving?
- **Hypothesis** (decompiled source, `PistonBaseBlock.triggerEvent` retract branch,
  ported in `piston.py trigger_event`): the retraction always runs (the piston queues it
  whatever is in front); when the block two cells on is a `moving_piston` (a retracting
  piston's own base is one for the two ticks of its retraction), `isPushable` is false, so
  the head comes back and the block is left where it is. One tick after the block lands,
  the same pull takes it.
- **Setup:** two identical stacks. S (sticky, facing up) at the bottom (0 1 0 and 5 1 0),
  R (sticky, facing up) on top of it (0 2 0, 5 2 0). Redstone blocks set at 1 beside S
  (1 1 0, 6 1 0) and beside R's landing cell (1 3 0, 6 3 0).
- **Procedure** (recorded `set` edits, between ticks): at 1 the four redstone blocks: S
  extends at 2 and lifts R to y 3 (lands 4); R lands next to its block and extends at 5
  (a landing check, [[../components]]). At 20 R's block goes: R retracts at 21 (its base
  is a moving piston during 21–23). (a) S's block goes at 21: S retracts at 22. (b) S's
  block goes at 24: S retracts at 25.
- **Observations** (replay events, `tools.doorlab.replay`):

```
2   S extends, pushes R 0 2 0 -> 0 3 0 (both stacks)
5   R extends (landing check), both
21  R retracts, both
22  (a) S retracts: pulled nothing; R stays at 0 3 0 (retracted, one cell up)
25  (b) S retracts: pulled R 5 3 0 -> 5 2 0
```

- **Game check:** EXP-079 and EXP-080: both worlds run on the 26.3 server with
  `run_world` (recorded edits), 40 ticks, 4 watched blocks each: **match**.
- **Conclusion:** a sticky piston's pull that meets a block still moving pulls nothing
  and leaves the block; the pull one tick after the landing takes it. With R-026 (a
  push into a moving block is refused until it lands): **a moving block is untouchable
  for pistons in both directions**, and a stack that fetches a rider must wait for the
  rider's own motion to end: the rider retracts at 21 and its base is a moving piston
  through 23; a pull at 22 or 23 leaves it, a pull at 24 or 25 takes it (all four
  game-verified: EXP-079 for 22 / 25, EXP-080 for 23 / 24, the same script with S's
  block removed at 22 / 23, `experiments/redstone/R-029b-pull-boundary.redsim.json`). So the first pull that works is at retraction + 3, the tick after the base is
  back, exactly as R-026's push one tick after the landing.
- **Where it matters:** Lutal's hub (delay 4 exact), Rubik's center (delay 3 breaks),
  Purplers' spiral (gap 11: the opening pulse lands inside the center piston's own
  retraction, [[../doors/robustness]] D11), the staircase's lifters.
