# R-018: making 0-tick pulses with pistons

- **Date:** 2026-10-16 · **Simulator:** e2b5f81 · **Game:** Java 26.3
- **Script:** `experiments/redstone/R-018-piston-zero-tick.cli.txt` · **Status:** verified
  (V, G EXP-057, S)
- **Question:** [[R-013-zero-tick]] made 0-tick pulses with editor edits (a redstone
  block set and removed between ticks). Can pistons alone make one, a block that powers a
  cell and leaves it with no tick in between? Related questions: when does a block that a
  sticky piston "spits" (drops on a short pulse) arrive, and do 0-tick pulses made
  *inside* a tick act like the R-013 ones?
- **Hypothesis** (`PistonBaseBlock.triggerEvent`, `checkIfExtend`,
  `PistonMovingBlockEntity.finalTick`, `ServerLevel.runBlockEvents`):
  - A sticky piston that loses power while its block is still moving gets a retract
    event that calls `finalTick` on the moving block: the block is placed **at its
    destination at once**, during that tick's block-event phase, and is not pulled back
    (the spit). It therefore arrives when the retract happens, which can be earlier than a
    full push (2 ticks after the start).
  - Block events queued during the block-event phase run in **the same phase** (the
    queue is emptied in a loop). A piston beside the landing cell D that is powered by
    quasi-connectivity but was never updated (BUD) is woken by the block arriving at D
    and pushes it out of D in the same phase: a 0-tick pulse at D's other neighbors.
  - A component reacting to the pulse acts as in R-013, except pistons: a piston's
    extend event re-checks power when it runs; one queued *before* the remover's event
    runs while the block is still there and extends. The arrival updates D's neighbors in
    the fixed order **west, east, down, up, north, south** (`NeighborUpdater.UPDATE_ORDER`),
    so neighbors earlier in that order than the remover queue first. A sticky piston that
    extends and loses power in the same phase spits its own block at once: the block moves
    one cell in 0 ticks.
- **Setup** (48×48 world; D = the cell in front of a sticky piston's head):
  - *Spit timing:* a sticky piston facing east with a redstone block in front, powered by
    a lever beside it for 1, 2 and 3 ticks (on at 2, off at 3, 4, 5), and one powered by
    an observer's 2-tick pulse (lever behind the observer flipped at 2).
  - *G0 (1-tick generator):* lever held on; a piston P south of D facing north, powered
    by a redstone block two above it (quasi-connectivity, never updated); a repeater east
    of D facing east.
  - *G1 (0-tick generator):* observer → sticky piston → redstone block, spat into D at
    tick 6; P as in G0. Beside D: a sticky piston facing east with a stone (east, 2nd in
    the order), a lamp on top (up), a copper bulb in the floor under D (down).
    *G1b:* a normal piston east instead. *G2:* a repeater east. *G3:* a comparator east.
  - *G5 (order):* D one block up, the redstone block spat in from the west, P **above** D
    facing down (4th in the order), sticky pistons with stones east (2nd), north (5th)
    and south (6th) of D.
- **Observations** (`changes`, `waves`, `trace 6`):

```
spit, lever 1 tick (on 2, off 3)   D: moving 3, redstone_block from 4  (a full push lands at 5)
spit, lever 2 ticks (off 4)        D: moving 3-4, redstone_block from 5
spit, lever 3 ticks (off 5)        D: redstone_block 5, air from 6 (pulled back)
spit, observer (pulse 4-5)         D: moving 4-5, redstone_block from 6, placed in the
                                   block-event step of the piston's retract (trace 6)
G0   D: redstone_block at view 5 only (landed in the block-entity phase, pushed at 6)
     repeater east of D: on 7-8
G1   trace 6: observer off → sticky piston's retract places the redstone block in D
     (lamp lights, bulb toggles on) → the sticky piston east of D extends → P pushes
     the redstone block north (bulb powered=false) → the east piston retracts and its
     stone is placed one cell on: in D for 0 ticks
     waves: lamp 6-9 (4-tick flash), bulb lit from 6, east stone moved at 6
     (base moving_piston 6-7), never a redstone block in D at a tick's end
G1b  normal piston east: head out and back in tick 6, its stone lands at 8
G2   repeater east of D: on 8-9            G3   comparator east of D: never on
G5   east sticky piston (before P): stone moved at 6; north and south (after P): never move
```

- **Result:** as predicted.
- **Conclusion** (in [[timing]], [[components]] Piston):
  - **Spit timing:** a sticky piston's block is in place at the tick its retract
    event runs: a 1-tick lever pulse puts it there 1 tick earlier than a full push (4
    instead of 5), a 2-tick lever pulse at the normal tick, an observer pulse 2 ticks
    after the start. A 3-tick pulse pulls it back (as in [[R-003-short-pulses]]).
  - **Pistons make 0-tick pulses:** a block spat into a cell and pushed out by a BUD
    piston woken by its arrival is there for no tick at all. Repeaters (a full pulse of
    their delay, 2 ticks later), lamps (4-tick flash) and copper bulbs (toggle) react,
    comparators do not: as for the editor-made pulses of R-013. A block that lands
    normally and is pushed out the same way (G0) gives a **1-tick** pulse instead.
  - **Unlike R-013, pistons can react:** a piston next to the cell reacts if its
    neighbor update came before the remover's, in the order west, east, down, up, north,
    south around the cell. A **sticky** piston then moves its block one cell **in 0
    ticks** (pushed and placed in the same phase); a normal piston's head goes out and
    back in the same tick and the block lands 2 ticks later. Pistons updated after the
    remover do not move. Unlike the wire races of [[R-017-wire-order]], this order is
    fixed by direction and does not change when the build is moved.
  Confidence: high (V; G EXP-057: every row matched the 26.3 server tick by tick; S).
- **Side finding:** `set` (like `/setblock`) of an observer makes it fire once (ticks 2–3):
  `/setblock` runs the new block's shape update, and the observer sees its own front. A
  player placing it (`place`) does not. G: in EXP-057 the scenario's observers, all put
  with `/setblock`, fired at tick 2 in the game too; that pulse drives the scenario.
- **Open** ([[backlog]]): a re-armable piston 0-tick (or 1-tick) pulse generator as a
  library module (G0, G1 are one-shot: P stays out and the redstone block is moved
  away); chains of instant (0-tick) piston moves for instant signal transmission.
- **Used by:** [[timing]], [[components]].
