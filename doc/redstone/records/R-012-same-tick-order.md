# R-012: order inside a tick: which 2-tick pulses pass, and piston races

- **Date:** 2026-10-16 · **Simulator:** 864a6da · **Game:** Java 26.3
- **Script:** `experiments/redstone/R-012-same-tick-order.cli.txt` · **Status:** verified
- **Question:** R-003 found that torches and comparators lose 2-tick pulses made by
  observers and repeaters, but see 2-tick lever pulses. What exactly decides it (Q5)?
  And when two pistons push into one cell in the same tick, which wins?
- **Hypothesis** ([[tick-scheduling]]): scheduled ticks due in one tick run **by
  priority** (repeater −3 when its front is a diode not facing back, −2 turning off, −1
  turning on; comparator −1 when its front is a diode not facing back, else 0; torch,
  observer and the rest 0), **then in the order they were scheduled**. A receiver (torch,
  comparator) re-reads its input when its tick runs 2 ticks after the pulse started; the
  pulse source's switch-back is also due then. The pulse passes iff the receiver's tick
  runs first. Block events (pistons) run in the order they were queued.
- **Setup:** a 48×48 world, rows 4 blocks apart (the script's header lists them). Row a
  stacks a second torch's block on top of the first torch (a torch strongly powers the
  block above it). Rows i and j: pistons at x=11 (facing east, a stone in front) and 15
  (facing west, wool in front), both pushing into the cell x=13.
- **Procedure:** levers at tick 2 (a and e: off again at 4, d: at 3); rows i, j: both
  levers in the same tick, west first (i) or east first (j).
- **Observations** (`waves`, `changes`):

```
a  torch out 4..5 (its lever: on 2, off 4)  → torch above: on 6..7         passes
e  torch out 4..5                           → comparator (front lamp): off 6..7   passes
b  observer 4..5 → comparator, front repeater:          on 6..7 (repeater 8..9)  passes
f  observer      → comparator, front comparator:        on 6..7                  passes
c  observer      → comparator, front lamp:              nothing                  lost
g  observer      → comparator, front wire:              nothing                  lost
h  observer      → comparator, front repeater facing back into it: nothing       lost
d  repeater 4..5 → comparator, front repeater:          nothing                  lost
i  stone (west lever first) takes the cell at 5; the east piston never extends
j  wool (east lever first) takes the cell at 5; the west piston never extends
```

- **Result:** as predicted. Why each case went that way (all due in the same tick, 2
  ticks after the pulse started):
  - a, e: the source torch's switch-back was scheduled by the lever at tick 4, *after*
    the receiver had scheduled its tick (during the torch's own tick) → receiver first.
  - b, f: the comparator feeds a diode, so its tick has priority −1 and runs before the
    observer's switch-off (priority 0).
  - c, g, h: comparator priority 0, same as the observer, and the observer scheduled its
    switch-off before it updated the comparator → observer first.
  - d: a repeater turning off has priority −2 (−3 into a diode): always before a
    comparator or torch.
- **Conclusion** (in [[timing]], [[components]]):
  - **Rule:** a circuit-made 2-tick pulse reaches a torch or comparator only if the
    receiver's tick runs before the source's switch-back: compare priorities first, then
    who scheduled first. In practice: **repeater-made: never; observer-made: only into a
    comparator that feeds a repeater or comparator** (not a lamp, wire, block, or a
    repeater pointing back); **torch-made: yes** when the torch's own switch-back was
    triggered later than it switched (as by a player).
  - A component's *front* can change what it sees: a comparator in front of a diode
    reacts one priority step earlier.
  - Design advice stays: do not rely on 2-tick pulses into torches or comparators;
    stretch them to 3+ ticks (a repeater of delay 2+), or check the case with `trace`.
  - **Pistons racing for one cell:** the piston powered first wins; the other does not
    move at all (its push is blocked by the moving block). Same tick, order = the order
    the pistons were powered (here: the order of the two lever flips).
  Confidence: high for these cases (V, S; G in EXP-010, EXP-028, EXP-047).
- **Used by:** [[timing]] (short pulses), [[components]], [[circuits]].
