# R-023: instant piston wire

- **Date:** 2026-10-17 · **Simulator:** 8c5bb46 · **Game:** Java 26.3
- **Script:** `experiments/redstone/R-023-instant-piston-wire.cli.txt` · **Status:** verified
- **Question** (backlog Q11): can pistons carry a signal over many blocks in 0 ticks,
  faster than wire with repeaters (2 ticks per 15 blocks)?
- **Hypothesis** (`PistonBaseBlock.moveBlocks`, `checkIfExtend`,
  `ServerLevel.runBlockEvents`):
  - A piston's block event moves its blocks at once: the cells they leave become air (or
    the moving head) and their neighbors are updated inside the event, and a
    `moving_piston` gives no power. So a redstone block a piston moves stops powering its
    old neighbors in that block event.
  - A piston that loses its power this way queues its retract event, and the block-event
    queue is drained in a loop: the event runs in the same phase. A chain of extended
    sticky pistons, each holding a redstone block against the back of the next one,
    therefore collapses within one tick, however long it is: an edge that **removes**
    power crosses it at once. Wire between the stages (up to 15 blocks) is instant too.
  - Re-arming is slow: a pushed block lands in the block-entity phase 2 ticks after the
    push, after that tick's block events, so the next piston starts in the following
    tick: **3 ticks per stage**.
  - Both ends can be turned around: an input that *pushes* the first redstone block away
    from the second piston starts the collapse on its rising edge, and a last stage that
    pulls a stone off a wire step (a solid block above the lower wire cuts the step)
    lights the lower wire in the same block event.
- **Setup** (96×96 world, floor y=0; the same layout as the game-server scenario
  `instant_piston_wire`):
  - *Row A* (z=1): sticky pistons facing east at x = 1, 4, 7, 10, 13, a redstone block in
    front of each; extended, each block sits against the next piston's back. Probe wires
    3+3k 1 2 beside the blocks' extended cells. Lever 0 1 1.
  - *Row B* (z=6): sticky pistons at x = 1, 18, 35; each extended block powers a 14-wire
    line (x+4 … x+17) whose end points into the next piston. Probes 4 1 6, 21 1 6 and
    38 1 6 (38 blocks from the lever 0 1 6).
  - *Row C* (y=2, z=10): a sticky piston 2 2 11 facing north holds the redstone block
    2 2 10 against the back of the chain's first piston (3 2 10); the chain (pistons
    3, 6, 9) ends in a stone that sits over the step from the upper wire 12 2 10 (powered
    by a redstone block 13 2 10) down to the output wire 11 1 10. Probes 5 1 10 and
    8 1 10 under the blocks. Lever 1 2 11 (on a stone).
- **Procedure:** levers A and B on, settle (every chain extends); at 10 lever A and B off
  and lever C on; at 25 all three back.
- **Observations** (`waves`, ticks 5..45; `trace 11`):

```
@LA lever            fffff...............fffffffffffffffffffff
@A0 redstone_wire    ffffff.................ffffffffffffffffff     on again 28
@A1 redstone_wire    ffffff....................fffffffffffffff     31
@A2 redstone_wire    ffffff.......................ffffffffffff     34
@A3 redstone_wire    ffffff..........................fffffffff     37
@A4 redstone_wire    ffffff.............................ffffff     40
@B0 redstone_wire    ffffff.................ffffffffffffffffff
@B1 redstone_wire    ffffff....................fffffffffffffff
@B2 redstone_wire    ffffff.......................ffffffffffff     38 blocks away
@LC lever            .....fffffffffffffff.....................
@C1 redstone_wire    ffffff....................fffffffffffffff
@C2 redstone_wire    ffffff.......................ffffffffffff
@COUT redstone_wire  ......eeeeeeeeeeeeeeeeeeeeeeeeee.........     on at 11, off at 37
```

  `trace 11`: the five pistons of row A retract in consecutive block-event steps of tick 11
  (steps 176…180); each step removes a redstone block and updates the next piston.
  **Game** (EXP-058, inputs by `/setblock` at 1, 30 and 45): every watched block matched
  the simulator in all 64 ticks; the probes of A and B all go off at 31, row C's output
  comes on at 31, the stages re-extend at 48, 51, 54, 57, 60, and C's output goes off at 57.
- **Result:** as predicted.
- **Conclusion** (in [[timing]], [[components]] Piston):
  - **Instant piston wire:** a chain of extended sticky pistons, each holding a redstone
    block against the next piston's back, collapses in **0 ticks** when the first one
    moves: 3 blocks per stage, or up to 17 when a wire line (≤ 15 blocks) joins the stages.
    An input from a player or `/setblock` acts in the next tick's block-event phase, like
    any piston input; from a component, in the same tick.
  - **One edge only:** the edge that removes the redstone blocks is instant. Re-arming
    takes **3 ticks per stage** (the pushed block lands 2 ticks after the push, the next
    piston starts a tick later), as slow as repeaters. The chain is ready for the next
    instant edge only when it has fully re-extended.
  - **Polarity at the ends:** an input piston that pushes the first block away makes the
    input's **rising** edge instant; a last stage that pulls a stone off a wire step makes
    the output **rise** at once (the step connects when the cutting block leaves). Pistons
    pulling (retracting) are the instant part; pushes always wait 2 ticks for the block.
  - Unlike the 0-tick pulses of [[R-018-piston-zero-tick]], no ordering race is involved:
    each piston is depowered by the stage before it, and the queue runs in order.
  Confidence: high (V; G EXP-058; S).
- **Open** ([[backlog]]): a pasteable instant-wire module (rising edge in, rising edge out)
  with its re-arm time as a contract; two chains to carry both edges instantly; vertical
  and turning stages.
- **Used by:** [[timing]], [[components]].
