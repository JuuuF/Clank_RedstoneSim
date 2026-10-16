# R-015: observers moved by pistons; sticky pistons pulling across a gap

- **Date:** 2026-10-16 · **Simulator:** 864a6da · **Game:** Java 26.3
- **Script:** `experiments/redstone/R-015-moving-observers.cli.txt` · **Status:** verified
- **Question:** Moving-block machines (flying machines) trigger themselves with
  observers that ride along. Does an observer fire after a piston moves it? What if it
  is pulsing while it is moved? And does a sticky piston that extends into air (a gap
  before the block) pull that block on a short pulse?
- **Hypothesis** ([[observer]], [[pistons]]): a moved block is placed with
  `updateFromNeighbourShapes`, which runs the observer's shape update for its watched
  side → it schedules a pulse, 2 ticks after landing, if it is not powered. An observer
  moved while powered keeps `powered=true` in the moved state; on landing, `onPlace` turns
  a powered observer with no pending tick off at once → no pulse. A sticky piston whose
  head moved into air has nothing "still extending" to spit, so its retraction pulls the
  block beyond the head even after a 2-tick pulse (unlike R-003's pushed blocks).
- **Setup:** a 32×32 world: three observers (facing south, east, west) each pushed east
  by a piston; an observer watching a lever, pushed at the moment it pulses, with a
  repeater where its output points after the move; a sticky piston with one cell of air
  and then a stone in front.
- **Procedure:** pistons' levers on at 2; the watched lever flipped at 2 (pulse at 4..5)
  and its observer's piston lever at 3 (the piston moves it in tick 4's block events,
  after the pulse began); the gap piston's lever on at 2, off at 4.
- **Observations:**

```
pushed observers (any facing)   land at 5, pulse 7..8
observer pushed while powered   tick 4: scheduled tick → powered=true; block event → moving
                                tick 6: lands as observer[powered=true] → at once powered=false
                                no pulse; the repeater behind it never turns on
gap piston (2-tick pulse)       head out at 3; retracts at 5: the stone moves from 2 to 1, solid at 7
```

- **Result:** as predicted.
- **Conclusion** (in [[components]], Observer and Piston):
  - **A pushed observer pulses once, 2 ticks after it lands** (whatever it faces): it
    sees its own arrival. This is what drives flying machines.
  - **An observer moved while powered loses its pulse:** it lands powered, switches off
    at once and fires nothing. Do not move observers during their own pulse (in practice:
    let the structure settle before starting it).
  - **A sticky piston extending into air pulls** the block beyond its head when it
    retracts, also after a 2-tick pulse; only a block it was still *pushing* is left
    behind (R-003).
  - Together with honey/slime separation ([[R-009-pistons]]) this gives the
    [[circuits]] Flying machine: 10 ticks per block, direction set by which group's
    observer is triggered first.
  Confidence: high (V, S; G EXP-034, EXP-047 for observers moved by pistons).
- **Found while building the flying machine:** blocks built with `set` can leave
  observers with pending ticks; the first version fired both pistons together and did
  not move, another lost the front observer's pulse because it was moved while powered.
  `settle` after building fixes both.
- **Used by:** [[circuits]] (Flying machine), [[components]].
