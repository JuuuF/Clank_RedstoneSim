# R-010: glitches from unequal path delays, and balancing them away

- **Date:** 2026-10-16 · **Simulator:** 864a6da · **Game:** Java 26.3
- **Script:** `experiments/redstone/R-010-hazards.cli.txt` · **Status:** verified
- **Question:** When two inputs of a gate change in the same tick, can the output show a
  wrong value for a moment? Does giving every input path the same delay prevent it?
- **Hypothesis:** a comparator schedules its tick only when its output *would* change at
  the moment of an update ([[comparator]], `checkTickOnNeighbor`). If one input's change
  arrives 2 ticks before the other's, the comparator acts on the half-changed inputs: a
  glitch 2 ticks long. With equal path delays both changes arrive in the same tick (both
  through repeaters, which switch before the comparator's tick, R-003), and the
  comparator sees only the final inputs.
- **Setup:** a 48×48 world:
  - Compact AND (comparator, subtract; rear A, side = wire from a torch on B's block):
    unbalanced (A by wire: 2 ticks; B through the torch: 4) at x=−10, z=−20; balanced (A
    through a delay-1 repeater: 4) at x=0.
  - XOR (two subtracting comparators facing each other into one stone; each rear one
    input, each side the other input through a delay-1 repeater): unbalanced (rears by
    wire) at x=−10, z=−8; balanced (rears through delay-1 repeaters) at x=4. Layouts as in
    `examples/circuits/xor_gate.cli.txt`.
- **Procedure:** AND: B on at 2; at 10 A on and B off together. XOR: A on at 2; at 12 A
  off and B on together; at 22 swapped back. XOR: both on at 2, both off at 12.
- **Observations** (`waves` of the outputs):

```
AND unbalanced  ............ff................   (glitch at 12..13)
AND balanced    ..............................
XOR unbalanced  ....cccccccccc..cccccccc..cccc   (drops out at 14..15 and 24..25)
XOR balanced    ......cccccccccccccccccccccccc   (on from 6, continuous)
XOR both inputs together, either version: no output at all (correct)
```

  Mechanism (unbalanced XOR, A off and B on at 12): C2 (= B − A) sees its rear B rise at
  12 while its side A is still 15 (the side repeater turns off only at 14): its output
  would stay 0, so it schedules nothing; at 14 the side drops, C2 schedules, and switches
  at 16. C1 (= A − B) loses its rear at 12 and switches off at 14. Between 14 and 16
  neither is on.
- **Result:** as predicted.
- **Conclusion** ([[circuits]] composition rules):
  - **Unequal path delays into one gate make glitches** when inputs change together:
    2 ticks long here, either a false 1 (AND) or a dropout (XOR).
  - **Balancing removes them:** give every path into the deciding component the same
    delay (add delay-1 repeaters to the faster paths). Cost: latency rises to the slowest
    path (both gates: 4 ticks on every edge).
  - Inputs changing in the *same direction* together (both on, both off) did not glitch
    even unbalanced, for these gates.
  - The library's [[circuits]] Compact AND and XOR gate are the balanced versions.
  Confidence: high for these gates (V); the mechanism is general (S) but other
  components' timing (torch vs comparator ticks, priorities) must be checked per design.
- **Used by:** [[circuits]] (Compact AND, XOR gate, composition rules).
