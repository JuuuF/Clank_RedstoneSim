# R-024: analog carry lines

- **Date:** 2026-10-17 · **Simulator:** e326ced · **Game:** Java 26.3
- **Script:** `experiments/redstone/R-024-analog-carry-lines.cli.txt` · **Status:** verified (simulator)
- **Question** (backlog Q15): can the carries of an adder be computed in parallel, instead
  of rippling through one comparator (or more) per bit?
- **Hypothesis** (wire rules of R-004/R-019, comparator subtraction of R-005):
  - A carry into bit i is 1 exactly when the nearest bit below i that does not propagate
    (A = B) generates (A = B = 1); CIN counts as bit −1.
  - Give each kind of event its own wire line: bit j injects 15 into the **G line** when it
    generates and into the **K line** when it kills (A = B = 0). Wire loses 1 per block, so
    at bit i the line whose nearest injection is closer is the stronger one, and one
    subtracting comparator (rear G, side K) per bit tells which.
  - Wire spreads both ways; a wire stepping up onto glass passes power up only (R-019), so
    one step onto glass per bit keeps each injection out of the bits below it. A bit of
    line is three wires: lower wire on stone, wire on glass one higher, wire on stone, then
    down to the next lower wire. Three wires a bit fit four bits and CIN into 15 blocks.
  - The two lines need not be read at exactly matching distances: events lie at least one
    bit (3 wires) apart, so an offset of up to 2 between the G and K reads cannot change
    which line wins.
- **Setup** (48×48 world, floor y=0):
  - G line z=0: lower wires 3j 3 0 on stone, glass 3j+1 3 0 with a wire on it, stone
    3j+2 3 0 with a wire on it (j = 0..3), last lower wire 12 3 0; the CIN start is a wire
    on stone −1 3 0. K line z=2: the same, shifted +1 in x (CIN start 0 4 2).
  - Injections: a repeater facing into the wire on glass (G: 3j+1 4 −1 facing south; K:
    3j+2 4 3 facing north), with a lever on the block behind it (G0..G3, K0..K3; CG and CK
    for CIN at the line starts).
  - Reads: comparator 3j+1 2 0 (subtract, facing east) under the glass; its rear is the
    stone under the G line's lower wire (the wire on top powers it), its side a single wire
    3j+1 2 1 that steps up onto the K line's lower wire 3j+1 3 2. Labels @C0..@C4.
- **Procedure:** a truth table over all 162 input patterns (CIN generates or kills; each
  bit propagates, generates or kills), outputs read 10 ticks after the levers; targets for
  the timing and the weakest on-value.
- **Observations:**
  - All 162 patterns give the right C0..C4 (target `carry`).
  - With every bit propagating and CIN on (lever at 1, repeater on at 3), **all five carries
    switch on in the same tick, 5**: C0 at strength 14, C4 at 2 (target `parallel`). The
    carry costs one comparator delay (2 ticks) whatever the number of bits.
  - Comparator outputs are analog: an on-carry is at least 3 when a kill lies one bit
    farther than the generate (target `margin`), and as low as 2 for the farthest bit.
- **Conclusion:** two wire lines with one glass step per bit and one comparator per bit
  compute every carry of 4 bits in parallel in 2 ticks after the injections. The limit is
  the wire range: CIN to the last read is 13 wires (4 bits); more bits need a second block
  whose CIN is the first block's restored carry (+2 ticks for a repeater). The outputs are
  weak (2..14): use them only as comparator rears or repeater inputs. Community
  "carry-cancel adders" are said to use a similar idea (not checked here).
- **Used by:** [[circuits]] fast adder (in progress), [[timing]].
