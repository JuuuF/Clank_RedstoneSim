# R-008: what an observer sees

- **Date:** 2026-10-16 · **Simulator:** 864a6da · **Game:** Java 26.3
- **Script:** `experiments/redstone/R-008-observers.cli.txt` · **Status:** verified
- **Question:** Which changes of the watched block fire an observer? Does it see changes
  that live only in block-entity data (a comparator's strength, container contents), or
  updates that do not change the block? How fast is a chain of observers?
- **Hypothesis** ([[observer]], `ObserverBlock.updateShape`): an observer fires when the
  watched block sends it a shape update, which happens only when that block's **state**
  changes (Q-UPD-SHAPE-NOUPD). So: wire power levels, a repeater's delay, a block placed
  or broken, a piston head appearing: yes. A comparator's output strength (stored in its
  block entity; `powered` does not change between 3 and 7), a barrel's items, a neighbor
  update without a state change: no. Each observer in a chain adds 2 ticks.
- **Setup:** a 48×48 world; observers at (0,1,z) facing west (output east), watched cell
  at (−1,1,z), rows 4 blocks apart (the script's header lists them).
- **Procedure:** WIRELVL lever A on at 2 (wire 14), lever B beside the wire on at 10
  (15) and off at 20 (14); COMPSTR and COMPD barrels 3 → 7 at 10; a barrel filled at 10;
  a repeater clicked at 10; a stone placed at 10 and broken at 20; a piston's lever on at
  10 and off at 30; a lamp beside a stone switched at 10; the chain's wire at 2.
- **Observations** (`waves`):

```
@O_WIRELVL    ....ff......ff........ff....   (0→14, 14→15, 15→14)
@O_COMPSTR    ..............ff............   (the wire 3→7 at 12)
@O_COMPD      ............................   (the comparator 3→7: no pulse)
@O_BARREL     ............................
@O_REPDELAY   ............ff..............
@O_PLACE      ............ff........ff....
@O_PISTON     .............ff..................ff   (head appears at 11, gone at 31)
@O_NOCHANGE   ............................
@O_CHAIN1/2/3 ....ff / ......ff / ........ff
```

- **Result:** every hypothesis held.
- **Conclusion** (in [[components]], Observer):
  - An observer fires on **any state change** of the block it watches, including wire
    power levels (15 → 14), a repeater's delay, placing, breaking, and a piston head
    appearing or leaving (2 ticks after the head shows up; the head finishing its move 2
    ticks later falls inside the pulse and adds nothing).
  - It does **not** see block-entity data: a comparator's strength while `powered` stays
    the same, container contents. Watch the wire a comparator drives, or the comparator's
    `powered` change (0 ↔ >0).
  - A neighbor update that does not change the watched block fires nothing.
  - Chains: 2 ticks per observer.
  Confidence: high (V, S; G in EXP-033).
- **Used by:** [[components]], [[circuits]] (both-edge detector, observer clock).
