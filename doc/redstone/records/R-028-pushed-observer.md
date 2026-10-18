# R-028: a pushed observer fires when it lands

- **Date:** 2026-10-19 · **Simulator:** b7b5c14 · **Game:** Java 26.3
- **Script:** `experiments/redstone/R-028-pushed-observer.cli.txt` · **Status:** verified in the simulator; game check queued (EXP-075)
- **Question:** MYuen222's 5x5 guide (claim G4, [[../doors/guide-5x5]]) times its
  sequences with observers that pistons push: "a piston pushing an observer gives block
  updates at 0, 3 and 4 gt after it starts; the observer then powers from 2 to 4 gt".
  When does a pushed observer fire, and does it depend on what it watches?
- **Hypothesis** (decompiled source): the observer travels as a moving block for 2 ticks.
  When it lands, the moving block entity places it through
  `Block.updateFromNeighbourShapes` (`PistonMovingBlockEntity.tick` / `finalTick`,
  `piston.py`). That runs the observer's `updateShape` once for each of the six
  directions, the one it faces included. `ObserverBlock.updateShape` starts the signal
  when the update comes from the faced side (`startSignal`: a tick in 2), whatever
  block is there. So it should fire 2 ticks after landing and stay on for 2 ticks (its
  `tick`), in every orientation. Its `onPlace` does not start a signal.
- **Setup:** three sticky pistons facing east, each with an observer in front: watching
  north (sideways), east (along the push) and up. Each piston gets a redstone block set
  beside it at tick 2.
- **Procedure:** `check` of the target `pushed`; the observers' states by `changes`.
- **Observations** (the same for all three):

```
push starts (block event)   3
observer moving             3..4
observer landed, off        5..6
observer powered            7..8
observer off again          from 9
```

- **Result:** as predicted. In all three orientations, the observer lands 2 ticks
  after the push starts. It fires 2 ticks after landing, for 2 ticks (4..6 ticks after
  the push starts).
- **Conclusion** (in [[../components]], Observer):
  - **A pushed observer pulses once when it lands, whatever it watches**: on 2 ticks
    after it lands, off 2 ticks later. A piston line that moves an observer is
    therefore a 4-tick delay from the push to the pulse.
  - The guide's "powers from 2 to 4 gt" is this pulse counted from the landing. Its
    "updates at 0, 3 and 4 gt" do not map to these ticks. Counted from the push, the
    updates are at 0 (the moving block appears), 2 (it lands), 4 (the pulse starts)
    and 6 (it ends). G4 is verified with that reading.
- **Used by:** [[../doors/guide-5x5]] (G4).
