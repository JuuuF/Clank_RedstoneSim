# Circuit library

Validated circuit building blocks, each with a contract: what it takes, what it gives,
latency, state, reset, the input sequences it was tested with and how it fails. Every
entry has a script `examples/circuits/NAME.cli.txt` that builds it in a fresh world and
checks its contract (`tests/cli/test_research.py` runs them all), the world it builds
(`NAME.redsim.json`, to open in the editor) and the module alone as a structure file
(`NAME.nbt`). Evidence labels: [[redstone/README#Scope and trust]].

## Using a module

- **Paste it:** `import examples/circuits/NAME.nbt at X Y Z [rotate N]` puts the module
  with its lowest corner at X Y Z (paths are relative to the directory you run
  `redsim-cli` in; run it from the repository root). Then `settle`. Rebuild the files
  after changing a script: `PYTHONPATH=src python -m tools.make_circuits`.
- **Ports** are given as offsets from the module's lowest corner. Most scripts build the
  module with that corner at `0 1 0` (offset = script coordinate minus `0 1 0`); where a
  script uses another corner (`xor_gate`, `monostable`) its section says so. Every
  module's signal flows **east** (+x) unless said otherwise.
- **Rotating:** `rotate N` turns the module N quarter turns clockwise seen from above
  (flow east → south → west → north). A port at offset (dx, dy, dz) of a module that is
  D blocks deep along z moves to (D − 1 − dz, dy, dx) for one turn (code in
  [[R-022-rotated-modules]]); inputs "from the west" come from the north, east, south
  after 1, 2, 3 turns. V: the clock in all four rotations, the XOR gate turned 1 and 3,
  the piston door turned 1, the NOT gate turned 1 all kept their contracts.
- **Driving inputs:** an input port is either a **block** (power it: attach a lever or
  button, or point a repeater, comparator, observer or wire into it; [[signals]]) or a
  **wire/repeater** (drive it from the side the contract names). A wire input only works
  when the driver makes it point the right way: a wire arriving from the side turns it
  into a line that no longer points into the module.
- **Latency** is in game ticks from the input change to the output change, measured with
  levers (player actions). Circuit-made pulses shorter than 3 ticks are lost by torches
  and comparators ([[timing]] short pulses), so a module whose input path starts with a
  torch or comparator needs input pulses of **3+ ticks** from other circuits (2+ from a
  player).

## Which module for what

| Need | Use |
|---|---|
| a button that toggles something (lever-like) | [[#T flip-flop]] ([[#Toggle door]] shows it wired) |
| on for a fixed time after a press | [[#Monostable]] (any length), a stone/oak button (20/30 ticks) |
| on while things keep happening, off a while after the last one | [[#Fade timer]] (retriggerable); a door that way: [[#Timed door]] |
| a short pulse from a long signal | [[#Rising-edge detector]] / [[#Falling-edge detector]] / [[#Both-edge detector]] |
| remember set/reset | [[#RS latch]]; sample-and-hold: [[#D latch]]; a sequence of bits: [[#Shift register]]; bits by address: [[#4x1 RAM]] |
| a repeating signal | [[#Clock]] (2–20 ticks period, enable), [[#Hopper clock]] (long), [[#Observer clock]] (6, free) |
| actions in order | [[#Sequencer]] |
| combine signals | gates; glitch-free when inputs change together: [[#XOR gate]], [[#Compact AND]], [[#AND gate]] |
| count events | [[#4-bit counter]] |
| react to a container's fill level | [[#Threshold detector]] |
| remember a strength (0–15) | [[#Peak-hold register]] |
| add two strengths | [[#Analog adder]] (subtract: one comparator, R-005) |
| pick one of two strengths by a select signal | [[#Analog multiplexer]]; one of four by a 2-bit address: [[#4:1 analog selector]] |
| one output per strength 0–15 (a counter or fill display, a selector) | [[#Signal-strength decoder]] |
| turn 4 bits into a strength 0–15 | [[#4-bit DAC]] |
| one output per 4-bit number (addresses, displays) | [[#Binary decoder]] |
| a 4-bit number on a 7-segment display | the segment lines: [[#Lookup table]] (`seg7`); with a lamp digit: [[#7-segment display]] |
| a strength as 4 bits; any function of 4 bits | [[#Lookup table]] (`adc4`, the generator) |
| add binary numbers | [[#Full adder]] (one bit), [[#4-bit adder]] (copies chained) |
| two signal paths must cross | [[#Crossing]] |
| a signal far away with no delay (40+ blocks in 0 ticks) | [[#Instant wire]] (rising edge); both edges: [[#Instant wire, both edges]] |
| move a structure by itself | [[#Flying machine]] |
| push a block two cells and pull it back | [[#Double piston extender]] |
| sort items out of a hopper line | [[#Item sorter]] |
| a door: 2x2 / 3x3 flush | [[#2x2 piston door]], [[#3x3 flush door]] (input-safe) |
| a sequence that must not be interrupted by a fast-changing input | [[#Lockout]] in front of it (each level held at least D + 6 ticks) |

## Index

| Module | Function | Size (x×y×z) | Latency | Script |
|---|---|---|---|---|
| **Gates** | | | | |
| [[#NOT gate]] | OUT = ¬A | 2×1×1 | 2 / 2 | `not_gate` |
| [[#OR gate]] | OUT = A ∨ B, isolated | 2×1×3 | 2 / 2 | `or_gate` |
| [[#NOR gate]] | OUT = ¬(A ∨ B) | 2×1×3 | 2 / 2 | `nor_gate` |
| [[#AND gate]] | OUT = A ∧ B (also NAND) | 4×2×3 | 4 / 4 | `and_gate` |
| [[#NAND gate]] | OUT = ¬(A ∧ B) | 2×2×3 | 2 / 2 | `nand_gate` |
| [[#Compact AND]] | OUT = A ∧ B with one comparator | 2×1×4 | 4 / 4 | `and_compact` |
| [[#XOR gate]] | OUT = A ⊕ B, glitch-free | 7×3×6 | 4 / 4 | `xor_gate` |
| **Analog** | | | | |
| [[#Threshold detector]] | on while an analog signal (a container's fill) ≥ k | 3×1×3 | 4 | `threshold` |
| [[#Peak-hold register]] | analog memory: keeps the largest strength written | 3×1×4 | 2–8 | `peak_hold` |
| [[#Analog adder]] | min(15, A + B) of two strengths | 4×1×4 | 6–8 | `analog_adder` |
| [[#Analog multiplexer]] | OUT = SEL ? B : A, strength kept | 6×1×5 | 4 data, 6 select | `analog_mux` |
| [[#4-bit DAC]] | OUT = 8·B3 + 4·B2 + 2·B1 + B0 as a strength | 6×1×11 | 12, balanced | `dac4` |
| [[#4:1 analog selector]] | OUT = X[2·S1 + S0], strength kept (composition) | 9×3×21 | 8 data, 12 address | `analog_mux4` |
| [[#Signal-strength decoder]] | 1 of 16 outputs on: the one numbered S | 17×1×9 | 10 | `decoder16` |
| **Wiring** | | | | |
| [[#Crossing]] | two wires cross without touching | 3×3×7 | 0 | `crossing` |
| [[#Sequencer]] | taps follow the input 8, 16, 24, 32 ticks later | 9×1×1 | 8 per tap | `sequencer` |
| [[#Instant wire]] | OUT rises with IN 39 blocks away; any length | 40×2×4 | 0 on, 12 off | `instant_wire` |
| [[#Instant wire, both edges]] | OUT follows IN in 0 ticks on both edges, 23 blocks away | 25×2×12 | 0 | `instant_edges` |
| **Pulse shapers** | | | | |
| [[#Rising-edge detector]] | 4-tick pulse when A turns on | 2×1×3 | 2 | `rising_edge` |
| [[#Falling-edge detector]] | 4-tick pulse when A turns off | 3×1×3 | 4 | `falling_edge` |
| [[#Fade timer]] | on until 54 ticks after the last input (retriggerable) | 4×1×4 | 12 | `fade_timer` |
| [[#Both-edge detector]] | 2-tick pulse on every change of A | 2×1×1 | 2 | `both_edges` |
| [[#Lockout]] | follows A but holds each level ≥ 30 ticks (any input timing) | 8×1×7 | 6 | `lockout` |
| **Memory** | | | | |
| [[#T flip-flop]] | toggles on each rising edge | 2×1×1 | 2 | `t_flipflop` |
| [[#RS latch]] | set / reset memory | 3×1×4 | set 4, reset 2 | `rs_latch` |
| [[#D latch]] | Q follows D, holds while E is on | 2×1×3 | 2 | `d_latch` |
| [[#Shift register]] | 4 bits, shifts on each clock edge | 17×1×3 | 8 | `shift_register` |
| [[#4x1 RAM]] | 4 one-bit words: write D at address A1 A0, read the addressed word | 16×3×43 | 32 read, 14–32 write | `ram4` |
| **Clocks** | | | | |
| [[#Clock]] | period 4d+4 with enable, no burnout | 3×1×3 | 2 from enable | `clock` |
| [[#Observer clock]] | free-running, 2 on / 4 off | 2×1×1 | — | `observer_clock` |
| [[#Hopper clock]] | long periods: 16·N − 2 ticks for N items, with stop | 10×2×5 | — | `hopper_clock` |
| **Arithmetic** | | | | |
| [[#Full adder]] | S = A ⊕ B ⊕ C, COUT = majority; copies chain | 17×5×13 | S 6–8, COUT 4–8 | `full_adder` |
| [[#4-bit adder]] | S3..S0 + COUT = A + B + CIN (composition) | 68×5×13 | 24 worst case | `adder4` |
| [[#Binary decoder]] | output N on while the 4 bits read N (composition) | 23×1×11 | 22 | `bin_decoder16` |
| [[#Lookup table]] | 16-word table: hex 7-segment decoder; ADC (strength → bits) | 44×3×43, 30×3×43 | 46, 28 | `seg7`, `adc4` |
| [[#7-segment display]] | 4 levers → a hex digit of lamps (composition) | 45×10×63 | 54 | `seg7_display` |
| **Contraptions and compositions** | | | | |
| [[#4-bit counter]] | counts rising edges (composition) | 14×1×1 | bit k: 2+4k | `counter4` |
| [[#Monostable]] | one edge → output on for exactly D ticks (64) | 5×1×8 | 4 | `monostable` |
| [[#2x2 piston door]] | opens a 2×2 doorway while its input is on | 10×2×3 | open 4, close 4 (solid 6) | `piston_door_2x2` |
| [[#3x3 flush door]] | opens a 3×3 doorway while its input is on; input-safe | 17×8×12 | open 32 (sides 8), close 17 | `door_3x3` |
| [[#Toggle door]] | a button toggles the 2x2 door | 10×2×6 | open 6, closed 8 | `toggle_door` |
| [[#Combination lock]] | 4 levers = 1 0 1 1 open the 2x2 door | 14×2×9 | OPEN 4, door 10 | `combination_lock` |
| [[#Flying machine]] | moves itself 1 block / 10 ticks, either way, until blocked | 5×2×1 | — | `flying_machine` |
| [[#Double piston extender]] | pushes a block 2 out and brings it back | 11×2×10 | out 10, home 24 | `double_piston_extender` |
| [[#Item sorter]] | takes one item type out of a hopper line | 7×3×4 | — | `item_sorter` |
| [[#Timed door]] | two buttons; closes ~5 s after the last press | 12×2×10 | open 18, close 102 | `timed_door` |

## Gates

### NOT gate

A torch on the input block. `examples/circuits/not_gate.cli.txt`. Status: **verified** (V).

| Port | Offset | Kind |
|---|---|---|
| A | 0 0 0 | input block (stone): power it |
| OUT | 1 0 0 | wall torch on A's east face |

- **Behavior:** OUT on (15 to adjacent components and wire, strongly powers the block
  above it at 1 1 0) while A is unpowered.
- **Latency:** 2 ticks off, 2 ticks on.
- **Pulses:** ignores a 1-tick input pulse; a 2-tick lever pulse turns it off for 2.
  Circuit-made 2-tick pulses are ignored (R-003).
- **State:** none. **Reset:** none needed.
- **Constraints:** A must not be powered by anything else; the torch does not power A.
  Torch burnout: more than 8 changes in 60 ticks burn the torch out (R-007, [[backlog]]).
- **Tested:** truth table; on 2 → off 4, off 20 → on 22; a 1-tick pulse ignored; a 2-tick
  pulse passes as 2 ticks.

### OR gate

Two wires into one block, a repeater reading the block. `or_gate.cli.txt`. **Verified.**

| Port | Offset | Kind |
|---|---|---|
| A | 0 0 0 | wire; drive it from the **north** (lever, torch, repeater/comparator pointing south, wire from the north) |
| B | 0 0 2 | wire; drive it from the **south** |
| OUT | 1 0 1 | repeater facing east, output 15 |

- **Behavior:** OUT = A ∨ B. The block between the wires (0 0 1) is weakly powered; the
  repeater isolates the inputs from each other's drivers on the output side.
- **Latency:** 2 on, 2 off (the repeater).
- **Pulses:** any input pulse comes out at least 2 ticks long (repeater, R-003).
- **Constraints:** the two input wires do not connect (the block is between them), but
  each input wire also powers whatever else it points into; keep the block's other sides
  free of components. A and B are **not** isolated from each other's *sources* if those
  sources also touch the other wire.
- **Tested:** truth table; A on 2, B on 10, A off 20, B off 30 → OUT on 4..31.

### NOR gate

As the OR gate, with a torch instead of the repeater. `nor_gate.cli.txt`. **Verified.**

| Port | Offset | Kind |
|---|---|---|
| A | 0 0 0 | wire, driven from the north |
| B | 0 0 2 | wire, driven from the south |
| OUT | 1 0 1 | wall torch facing east |

- **Behavior:** OUT = ¬(A ∨ B). **Latency:** 2 off, 2 on. **Pulses:** as the NOT gate.
- **Tested:** truth table; A on 2, B on 10, A off 20, B off 30 → OUT off 4..31.

### AND gate

The classic three-torch AND: torches on both input blocks feed a wire that powers the
output torch's block. `and_gate.cli.txt`. **Verified.**

| Port | Offset | Kind |
|---|---|---|
| A | 0 0 0 | input block |
| B | 0 0 2 | input block |
| NAND | 1 1 1 | wire on top (power 14): on unless both inputs are on |
| OUT | 3 1 1 | wall torch on the block 2 1 1, facing east (y = 2 in the script) |

- **Behavior:** OUT = A ∧ B; NAND = ¬(A ∧ B) as a by-product.
- **Latency:** 4 on, 4 off (two torches); NAND 2.
- **Hazards:** none seen when the inputs swap in the same tick (A off, B on at once): both
  paths are equally long.
- **Tested:** truth table (OUT and NAND); A on 2, B on 10 → OUT on 14; A off 20 → OUT off
  24; A on and B off together at 30 → no glitch.

### NAND gate

The AND gate without its output torch. `nand_gate.cli.txt`. **Verified.**

| Port | Offset | Kind |
|---|---|---|
| A | 0 0 0 | input block |
| B | 0 0 2 | input block |
| OUT | 1 1 1 | wire (power 14) pointing east into 2 1 1: put the next block or component there |

- **Latency:** 2 off, 2 on. Output is wire, so a block it points into is only weakly
  powered (drives components, not wire; [[signals]]).
- **Tested:** truth table; a repeater at 2 1 1 (on a stone) follows 2 ticks later.

### Compact AND

One subtracting comparator: rear = A (through a delay-1 repeater), side = ¬B (a torch
on B's block powers a wire at the comparator's side). `and_compact.cli.txt`. **Verified.**

| Port | Offset | Kind |
|---|---|---|
| A | 0 0 0 | repeater facing east into the comparator's rear; drive it from the west |
| B | 1 0 3 | input block (a torch on its north face) |
| OUT | 1 0 0 | comparator facing east, subtract mode, output 15 |

- **Behavior:** OUT = A − ¬B = A ∧ B.
- **Latency:** 4 ticks each way from either input.
- **No glitches:** the repeater on A makes both paths 4 ticks long. Without it (A by
  wire, 2 ticks) OUT gave a 2-tick false 1 when A rose as B fell ([[R-010-hazards]]).
- **Tested:** truth table; A on 2, B on 10 → on 14; B off 20 → off 24; B on 30 → on 34;
  A off 40 → off 44; one input rising as the other falls, both ways: no glitch.

### XOR gate

Two subtracting comparators facing each other into one stone: C1 = A − B, C2 = B − A.
A enters at the west end, B at the east end; each loops around one side (A south, B
north) to the other comparator's side, so the inputs never cross; the output climbs out
over B's loop on a stone stair. `xor_gate.cli.txt`. **Verified.**

| Port | Offset | Kind |
|---|---|---|
| A | 0 0 3 | wire; drive it from the west (script: 0 1 0) |
| B | 6 0 3 | wire; drive it from the east (script: 6 1 0) |
| OUT | 3 2 0 | wire at the top (power 12) pointing north into 3 2 −1 (script: 3 3 −3) |

(Offsets from the module's lowest corner, which is at 0 1 −3 in the script.)

- **Behavior:** OUT = A ⊕ B, power 12.
- **Latency:** 4 ticks on every edge of either input.
- **No glitches:** all four paths (rears and sides) go through one delay-1 repeater. The
  first version, with the rears by wire, dropped OUT for 2 ticks whenever A and B swapped
  in one tick ([[R-010-hazards]]).
- **XNOR:** put a [[#NOT gate]] after OUT (or a torch on the stone the comparators point
  into: off while either comparator is on).
- **Tested:** truth table; A on 2 → on 6, B on 10 → off 14, A off 20 → on 24, B off 30 →
  off 34; both on and off together; swapped twice: OUT continuous.

## Analog

### Threshold detector

A comparator in compare mode with a constant k at its side passes the analog input only
when it is ≥ k; a repeater turns that into a clean 15. `threshold.cli.txt`. **Verified.**

| Port | Offset | Kind |
|---|---|---|
| X | 0 0 0 | the analog input: a container or analog block here, or wire / a powered block carrying a strength |
| K | 1 0 2 | a barrel of reading k (`source … barrel k`), read by a comparator pointing into the side |
| OUT | 2 0 0 | repeater facing east: 15 while X ≥ k |

- **Behavior:** OUT on while X ≥ k (built with k = 6: X = 3, 5 off; 6, 7, 15 on; 4 off).
  **Latency 4** (comparator 2 + repeater 2) after X changes.
- **Uses:** "chest at least this full" (k from the [[signals]] fill table), analog
  combination locks, level sensors. For "X ≥ k" with k = 1 a plain comparator does it.
- Rules behind it: [[R-005-signal-strength]] (compare mode: rear ≥ side passes).

### Peak-hold register

Analog memory: four comparators and four stones in a ring (no wire, so nothing fades)
hold a strength 0–15 forever. The write comparator feeds the ring's last stone, which
takes the larger of the ring and the write value; a clear zeroes the subtracting
comparator through its side. `peak_hold.cli.txt`. **Verified.**

| Port | Offset | Kind |
|---|---|---|
| W | 0 0 0 | write: comparator facing south; it writes what it reads behind it |
| CLR | 1 0 0 | clear: repeater facing south; drive it from the north for **8+ ticks** |
| VAL | 2 0 1 | a ring stone holding the value (strong): wire beside it, or a comparator facing away |

- **Behavior:** keeps the **largest** value written (tested: 1 → 7 → 9, then a 4 does
  not lower it); the stored value appears within one lap (up to 8 ticks).
- **Clear:** zeroes the ring for as long as CLR is on; afterwards the ring holds the
  *current* write value (tested: 9, write input lowered to 4, clear 10 ticks → 4, and a
  later 2 does not lower it).
- **Failure case (V):** a clear shorter than one lap (8 ticks) wipes only part of the
  ring; the old value keeps circulating and the output alternates (9, 4, 9, 4 every 4
  ticks). The same lap rule as the [[#Fade timer]]: anything that should change a ring's
  whole contents must last at least one lap.

### Analog adder

Three subtracting comparators: C1 = 15 − A (a redstone block behind it, A at its side),
C2 = C1 − B, C3 = 15 − C2 = A + B (another redstone block behind C3, C2 at its side).
`analog_adder.cli.txt`. **Verified.**

| Port | Offset | Kind |
|---|---|---|
| A, B | 1 0 0, 2 0 0 | analog inputs (containers or analog blocks; each read by a comparator pointing into C1's / C2's side) |
| SUM | 3 0 2 | comparator C3 facing north: strength min(15, A + B) |

(Offsets from the lowest corner, 0 1 −2 in the script.)

- **Behavior:** tested 3+4 = 7, 7+8 = 15, 9+9 → 15 (saturates), 1+0 = 1, 6+6 = 12,
  0+5 = 5, 2+11 = 13.
- **Latency:** 6 ticks from B, 8 from A (2 per comparator).
- **Constraints:** strengths travel comparator to comparator only: wire would lose 1 per
  block. Keep wire and redstone blocks away from the input comparators' sides (they would
  be side inputs, R-005); that is why C3 points into a stone.

### Analog multiplexer

Two subtracting comparators gate the inputs: CA = A − 15·SEL, CB = B − 15·¬SEL. Both point
into one stone; a comparator reading the stone gives the larger, which is the selected
input. A repeater (SEL) and a torch (¬SEL), both 2 ticks, switch the two gates in the
same tick. `analog_mux.cli.txt`. **Verified.**

| Port | Offset | Kind |
|---|---|---|
| SEL | 0 0 1 | wire; drive it from the **west** (on = select B) |
| A | 4 0 0 | input A: an analog block (container …) read by CA, or a block powered with the strength |
| B | 4 0 4 | input B, the same |
| OUT | 5 0 2 | comparator facing east: strength A while SEL is off, B while SEL is on |

- **Behavior:** tested A = 5, B = 11: OUT 5, then 11 after SEL; changes of the unselected
  input do nothing; the selected one passes with its strength (3, 9, 14); A = 15 is
  blocked completely while B = 0 is selected; 0 and 15 pass.
- **Latency:** 4 ticks from the selected input (2 comparators), 6 from SEL.
- **No glitch:** switching SEL goes straight from one value to the other (tested every 10
  ticks, OUT never 0 in between).
- **SEL pulses must last 3+ ticks** (V, failure cases in the targets): a 1-tick pulse is
  lost (the torch ignores it, and CA misses the repeater's 2-tick pulse, R-003); a 2-tick
  lever pulse switches only CB, so OUT is max(A, B) for 2 ticks instead of B.
- **Constraints:** if A or B is a solid block carrying a strength below 15, nothing
  behind it (4 0 −1, 4 0 5) may be a container: the comparator would read that instead
  (R-005). 5 0 1 and 5 0 3 must stay air: they are side inputs of CA, CB and OUT.
- **Composition (V):** OUT may point straight into another module's input block (a
  comparator keeps the strength): [[#4:1 analog selector]] is three copies, two of them
  turned so their OUT points into the third's A and B stones.

### 4:1 analog selector

Picks one of four strengths by a 2-bit address: three [[#Analog multiplexer]] copies
pasted so that the first stage's outputs point straight into the second stage's inputs.
`analog_mux4.cli.txt` (imports `analog_mux.nbt`; run from the repository root).
**Verified.**

| Port | Offset | Kind |
|---|---|---|
| S0 | 0 2 10 | wire on the top layer (script −2 3 2); drive it from the west, strength 8 or more |
| S1 | 0 0 9 | wire (script −2 1 1); drive it from the west |
| X0, X1 | 8 0 6, 4 0 6 | inputs (script 6 1 −2, 2 1 −2): analog blocks (barrels in the paste) or blocks powered with the strength; X0 fed from the east, X1 from the west |
| X2, X3 | 4 0 14, 8 0 14 | the same (script 2 1 6, 6 1 6); X2 from the west, X3 from the east |
| OUT | 7 0 10 | comparator facing east (script 5 1 2): the strength of X[2·S1 + S0] |

(Offsets from the module's lowest corner, −2 1 −8 in the script.)

- **Layout:** mux2 as pasted picks between its A stone (S1 off) and B stone. mux0 (pasted
  `rotate 1`, north of mux2) picks X0 / X1 by S0, and its OUT comparator points south
  straight into mux2's A stone; mux1 (`rotate 3`, south) picks X2 / X3 and points north
  into mux2's B stone. No routing between the stages: a comparator keeps the strength,
  and the stone it points into is what the next gate reads. mux2's A and B must be stones
  (the paste brings barrels: a comparator reads a container's contents, not the power).
- **Address wiring:** S0 has to reach the far edges of both first-stage muxes (a mux's
  SEL is opposite its OUT). It runs on the top layer (y=3 on supports at y=2): east along
  z=2, then north and south along x=4 straight over the three muxes, with a repeater on
  each branch, and steps down onto the SEL wires. A wire on the bottom layer would have
  walled in mux2's SEL and the X1, X2 inputs; on the top layer every port is reached
  from outside under the supports.
- **Behavior:** X = 3, 7, 11, 14: every address gives its input (target `select`); a
  change of the selected input passes, the other three do nothing (`data`).
- **Latency:** selected input → OUT 8 ticks (two muxes); S0 → OUT 12 (a repeater, then two
  muxes); S1 → OUT 12 (its delay-3 repeater, then one mux).
- **Balanced address:** both address bits may change in the same tick: OUT goes straight
  from the old input to the new one (00 → 11, 11 → 00, 01 → 10 tested, target
  `together`). **Failure case found while building** (target `unbalanced`): with S1's
  repeater at delay 1, S1 takes 8 ticks and S0 12, and 00 → 11 shows X2 for 4 ticks
  before X3 (mux2 switches before the first stage does). Address pulses must last 3+
  ticks, as for [[#Analog multiplexer]].
- **Uses:** reading one of four analog memories ([[#Peak-hold register]] outputs as the X
  inputs), a 2-bit-addressed signal-strength bus. Larger: 8:1 is two of these into one
  more mux, with S2 delayed to match.

### Signal-strength decoder

A thermometer code from a wire line, then one subtracting comparator per value. The input
strength S feeds a wire line whose cell c carries S − c; a repeater tap on each cell gives
T(c) = 15 while S ≥ c + 1. Output m is a subtracting comparator with T(m − 1) behind it
and T(m) at its side: on only while S = m (output 0 is a torch: ¬T(0)). `decoder16.cli.txt`.
**Verified.**

| Port | Offset | Kind |
|---|---|---|
| IN | 0 0 4 | the analog input: a barrel in the build; any container, or a block powered with the strength (a comparator reads it) |
| O0 | 2 0 0 | repeater facing north: 15 while S = 0 |
| Om, even m ≥ 2 | m+1 0 0 | facing north (a comparator or a repeater): 15 while S = m |
| Om, odd m | m+1 0 8 | facing south: 15 while S = m |

- **Behavior:** tested with every value 0 → 15 in steps (exactly one output on, the one
  numbered S, checked every tick) and with jumps 0 → 13 → 2 → 15 → 0 → 8 → 7 → 9 → 1 (no
  other output ever flashes).
- **Latency:** 10 ticks from the input barrel to every output (8 from the wire line); all
  outputs switch in the same tick, so no two are ever on together.
- **Layout rules that make it work** (each one found necessary while designing it):
  - Every cell needs two taps (it is the rear of one output and the side of the next), so
    taps sit on both sides of the line: odd outputs south, even north.
  - A wire feeding a comparator's side feeds **every** comparator beside it (wire
    connects to comparators on any side, and they read it; V: the script's `sharedside`
    control). Comparators in one row would share their side wires, so on each side they
    alternate between a near and a far row; repeaters make up the far row's extra
    distance, keeping all paths 8 ticks.
  - A powered solid block beside a comparator is not a side input (R-005), so the O0
    stone may touch O2's comparator.
- **State:** none. **Constraints:** the input changes only through the comparator 1 0 4
  (a container or a block); the wire line must keep its cells (no wire next to it).
- **Uses:** counter or fill-level displays, selecting one of 16 actions by a strength
  (with [[#Analog multiplexer]] for the reverse), item-count logic with
  [[#Threshold detector]].

### 4-bit DAC

Binary to signal strength: OUT = N = 8·B3 + 4·B2 + 2·B1 + B0. `dac4.cli.txt`, generated by
`tools/circuitgen/dac4.py`. **Verified.**

| Port | Offset | Kind |
|---|---|---|
| B3 | 0 0 3 | the bit's repeater at the west edge (script −1 1 −2); drive it from the west |
| B2, B1, B0 | 0 0 7, 0 0 1, 0 0 9 | wires at the west edge (script −1 1 2, −1 1 −4, −1 1 4); drive them from the west |
| OUT | 5 0 5 | a stone powered with N (script 4 1 0): read it from the east (a comparator, or another module's input block) |

(Offsets from the module's lowest corner, −1 1 −5 in the script.)

- **How it works** (all comparators subtract): a chain of four comparators starts from a
  full barrel (15) and subtracts the weight of every bit that is **off**:
  15 − (15 − N) = N, with no inverter. Each weight comes from a gate comparator that reads
  a barrel holding the weight and has its bit as side input (15): w − 15·B. The gates of
  bits 1 and 0 sit two cells further out and feed the chain through three wire cells,
  which lose 2, so their barrels hold w + 2; that frees the west side for every input
  and keeps the east side clear for the reader.
- **Behavior:** all 16 values (target `values`, counting); every bit flipping at once,
  N → 15 − N (16 targets). All 240 changes between two values were checked once: OUT goes
  straight from the old value to the new one 12 ticks after the change, nothing in
  between (`python -m tools.circuitgen.dac4 --all FILE` writes that script, 3 s).
- **Latency:** **12 ticks** from every bit: the input repeaters (delays 1, 2, 3, 4) balance
  the chain, where a bit's gate enters later the earlier its delay. **Failure case**
  (target `unbalanced`): with all four at delay 1, bit 0 arrives in 6 ticks and bit 3 in
  12, and 0 → 9 shows 1 for 6 ticks before 9.
- **Exact strengths:** a comparator chain keeps strengths exactly (rear to rear, no
  wire); a weight carried by wire must count the wire's loss (1 per cell after the first).
- **Uses:** a binary counter's value as a strength (to [[#Signal-strength decoder]],
  [[#Threshold detector]], comparator arithmetic), [[#Binary decoder]].

## Wiring

### Crossing

Two signals cross: A runs west→east on the floor; B climbs a stair of stones, runs over a
stone set right on top of A's wire, and comes down again. `crossing.cli.txt`.
**Verified.**

| Port | Offset | Kind |
|---|---|---|
| A_IN, A_OUT | 0 0 3, 2 0 3 | A's ends (wire) |
| B_IN, B_OUT | 1 0 0, 1 0 6 | B's ends (wire), B passes over A at y = 3 (offset 2) |

- **Behavior:** A and B never affect each other (all four combinations checked). No
  delay; B loses 6 strength on the bridge (in 15 → out 9), A 2 (15 → 13).
- **Why it works:** B's wire on the stone above A powers that stone only weakly, and wire
  ignores weakly powered blocks; the stone also stops A's wire from stepping up; wire
  never powers the block above it (R-002, R-004).

### Sequencer

A tapped delay line: repeaters (delay 4) alternate with tap blocks. `sequencer.cli.txt`.
**Verified.**

| Port | Offset | Kind |
|---|---|---|
| IN | 0 0 0 | wire; drive it from the west |
| S1…S4 | 2, 4, 6, 8 (x) | tap blocks, strongly powered; put the driven components beside them |

- **Behavior:** tap k follows IN with a delay of **8·k ticks** (on and off). A short
  input becomes an 8-tick pulse at the first repeater and walks down the taps.
- **Tuning:** each repeater's delay sets its stage (2/4/6/8 ticks).
- **Use:** piston sequences (one tap per piston), staggered lamps.

### Instant wire

A rising edge carried 39 blocks (any length) in **0 ticks**: a chain of sticky pistons
that collapses in one block-event phase ([[R-023-instant-piston-wire]], G EXP-058).
`instant_wire.cli.txt`, generated by `tools/circuitgen/instant_wire.py STAGES` (2 here;
each stage adds 17 blocks and 3 ticks of re-arming). **Verified.**

| Port | Offset | Kind |
|---|---|---|
| IN | 0 1 3 | a stone behind the head piston (script 0 2 2): power it (a lever on it, a repeater or wire into it) |
| OUT | 37 0 3 | wire at the south edge, strength 12 (script 37 1 2) |

(Offsets from the module's lowest corner, 0 1 −1 in the script. Paste it on a floor.)

- **How it works:** armed, every stage's sticky piston is extended and its redstone block
  powers the next piston through a 14-wire line. IN makes the head piston push the first
  redstone block away; the first stage loses power and retracts, which removes its block
  from the wire, and so on: each retract is queued into the block-event phase being run.
  The tail piston pulls its stone off the step from the wire on its support down to the
  output wire, and the step connects at once (a solid block over the lower wire cut it).
- **Latency:** OUT rises in the tick the head piston moves: **0 ticks** after a component
  that powers IN (a repeater turning on at 12 lights OUT at 12, target `same_tick`), one
  tick after a lever (target `instant`), as for any piston.
- **Falling edge is slow:** OUT goes off **12 ticks** after IN (3 per stage, the head and
  the tail included: 3·(STAGES + 2)), when the tail's stone is back over the step (target
  `rearm`). The module is armed again only then.
- **Failure cases** (targets): IN on again before it has re-armed (10 ticks after going
  off) finds the tail's stone still moving; the tail spits it onto the step, and OUT goes
  **off while IN is on** (`too_soon`). A 2-tick pulse on IN makes the head spit its
  redstone block forward: the chain stays down, OUT stays on, until IN has been on and
  off again (`short_pulse`). So: IN pulses of 3+ ticks, gaps of 12+.
- **Both edges at once:** two such chains whose collapses are combined at the output (one
  removes a cut, the other a source) work if the falling-edge chain re-arms by itself:
  [[#Instant wire, both edges]].
- **Uses:** start a far contraption without delay (a door, a piston line, a flying
  machine's start), or line up events at several distances in one tick.

### Instant wire, both edges

OUT follows IN in **0 ticks on both edges**, 23 blocks away (backlog Q17): two instant
piston chains ([[R-023-instant-piston-wire]]) whose collapses act on one output step.
`instant_edges.cli.txt`. **Verified**, also in the game (EXP-060: every watched block matched for
180 ticks, both edges one tick after the input).

| Port | Offset | Kind |
|---|---|---|
| IN | 0 1 2..11 | the input wire bus (script 1 2 2..11): power any part of it |
| OUT | 22 0 9..11 | output wire (script 23 1 9..11) |

- **How it works:** the output step (wire 24 2 9 down to OUT) carries power only while the
  source B (a redstone block, 25 2 9) feeds it and no cut A (a stone, 23 2 9) sits over it.
  Only removals are instant (a piston pulling or pushing a block away), so each edge
  removes one of the two:
  - **Chain R** (an [[#Instant wire]] with one stage): IN's rising edge makes its head push
    the first redstone block away. The chain collapses, and its tail pulls A off the step:
    OUT turns **on**.
  - **Chain F** (two stages): its head H_F is a sticky piston powered by IN or by D. IN's
    falling edge makes it pull its block back; the chain collapses, and its tail pulls B
    away: OUT turns **off**.
  - **Re-arming in order:** R re-arms when IN falls and has A back over the step 9 ticks
    later. D (the bus, 4 ticks of repeaters, a torch: NOT IN, then a repeater into H_F)
    powers H_F again 8 ticks after the fall, so F re-arms by itself and B is back 18
    ticks after the fall. A comes back before B, so OUT never glitches on.
  - Why D: an F whose head only followed IN (like R) would re-arm only after IN rose, and
    B would be missing at the rise. That is why the old note said two chains could not
    be combined.
- **Latency:** **0 ticks** after a component powering the bus on both edges (target
  `same_tick`: a repeater turning on at 12 and off at 42 moves OUT at 12 and 42); 1 tick
  after a lever, as for any piston input (`lever`).
- **Limits:** IN on at least **7 ticks**, off at least **18**: then every edge is exact
  (tested: pulses and gaps of 1–30 ticks, 40 random sequences within the limits).
  Outside them:
  - on for 3–6: the fall waits until D is off, 8 ticks after the rise (`late_fall`);
  - off for 9–17: the rise waits until F has re-armed, 19 after the fall (`late_rise`);
  - **failure cases:** off for 8 or less, R has not re-armed and OUT stays off while IN
    is on (`lost_rise`); on for 1–2, R's head spits its block forward and OUT stays on
    until IN goes on and off again (`spit`).
- **Longer distances:** more stages in both chains. Each stage adds 3 ticks to the
  re-arming, so D must grow with F's stage count: B must come back after A.

## Pulse shapers

### Rising-edge detector

A subtracting comparator: rear = A, side = A delayed by a repeater. While the delayed copy
has not arrived, the comparator outputs A. `rising_edge.cli.txt`. **Verified.**

| Port | Offset | Kind |
|---|---|---|
| A | 0 0 0 | wire; drive it from the west |
| OUT | 1 0 0 | comparator facing east, subtract |
| DELAY | 1 0 1 | repeater facing north into the comparator's side; delay d ≥ 2 |

- **Behavior:** when A turns on, OUT gives a pulse of **2·d ticks** (4 at the built
  delay 2) starting **2 ticks** later, with A's strength. Nothing when A turns off.
- **Tuning:** click DELAY: d = 2, 3, 4 → 4, 6, 8 ticks. d = 1 gives **no pulse** (the side
  repeater switches in the same tick as the comparator, before it). V for d = 1…4.
- **Short inputs:** A on for n ticks gives min(n, 2·d); n = 1 is lost (comparator,
  R-003).
- **Failure case:** A turning on again less than 2·d ticks after it turned off gives no
  new pulse (the side repeater fills the gap).
- **Output** is a circuit-made pulse of 2·d ≥ 4 ticks: torches and comparators see it.

### Falling-edge detector

Rear = A delayed by D (repeater, D = 3), side = A through a delay-1 repeater.
`falling_edge.cli.txt`. **Verified.**

| Port | Offset | Kind |
|---|---|---|
| A | 0 0 0 | wire; drive it from the west |
| REAR | 1 0 0 | repeater facing east, delay D |
| OUT | 2 0 0 | comparator facing east, subtract |
| SIDE | 2 0 1 | repeater facing north, delay 1 |

- **Behavior:** when A turns off, OUT gives a pulse of **2·D − 2 ticks** (4 at D = 3)
  starting **4 ticks** later. Nothing when A turns on. D = 1, 2 give no pulse; D = 4 gives
  6 ticks.
- **Failure case:** A on for fewer than 2·D ticks: the rear repeater stretches it, and OUT
  gives a 6-tick pulse 8 ticks after the rise instead (tested: a 2-tick input).
- Why the side goes through a repeater: a wire side input loses strength with distance,
  and the comparator would leak rear − side (3) while A is on (seen in the first build).

### Both-edge detector

An observer watching the input wire. `both_edges.cli.txt`. **Verified.**

| Port | Offset | Kind |
|---|---|---|
| A | 0 0 0 | wire; drive it from the west |
| OUT | 1 0 0 | observer watching A, output east |

- **Behavior:** a 2-tick pulse starting 2 ticks after every change of A (on and off; also
  a change of A's power level).
- **Merging:** changes less than 4 ticks apart give one pulse; 4 ticks apart give two.
- **Output** is a circuit-made 2-tick pulse: repeaters, pistons, lamps, bulbs see it,
  **torches and comparators do not** (R-003); stretch it with a repeater of delay ≥ 2.

### Fade timer

A retriggerable timer: a ring of three comparators (they keep the strength) closed by
three wires (two of which take 1 each) holds a value that drops by 2 per 6-tick lap.
The input fills the ring with 15; the output is on while anything is left.
`fade_timer.cli.txt`. **Verified.**

| Port | Offset | Kind |
|---|---|---|
| IN | 0 0 1 | repeater facing east, delay 4; drive it from the west |
| OUT | 3 0 0 | repeater facing north reading the ring's first stone |

- **Behavior:** OUT on **12 ticks** after the input rises; off **54 ticks after the input
  falls**. Inputs shorter than 8 ticks count as 8 (the input repeater stretches them), so
  a short trigger at T gives OUT on T+12 … T+61.
- **Retriggerable:** any new input while it runs refills the ring and restarts the time
  (tested: a 2-tick input at 40 kept OUT on without a break until 101).
- **Tuning (I, not tested):** each extra comparator+stone pair in the ring adds 2 ticks
  per lap (7 laps); one decaying wire instead of two would make it last 15 laps.
- **Failure case found (V):** an input shorter than one lap (6 ticks) fills only part
  of the ring: a packet of strength circulates and OUT flickers (4 on, 2 off). That is
  why the input repeater has delay 4 (8-tick minimum); with delay 2 it flickered.
- **Analog note:** comparators in a ring keep a strength forever; any wire in the ring
  makes it fade ([[R-005-signal-strength]]). A ring without wire is the
  [[#Peak-hold register]].

## Memory

### Lockout

A repeater that locks itself after each change of its output: the output follows A, but
every level lasts at least D + 6 ticks, whatever A does. For anything that runs a
sequence and must not be interrupted (a door, an extender): put it in front of the input.
`lockout.cli.txt`. **Verified.**

| Port | Offset | Kind |
|---|---|---|
| A | 0 0 4 | input wire; drive it from the west (script 0 1 4) |
| OUT | 7 0 4 | output repeater facing east (script 7 1 4) |

- **Behavior:** OUT follows A **6 ticks** late; each on level and each off level lasts at
  least **30 ticks** (D = 24). A shorter pulse comes out 30 long, a gap of 4–29 ticks comes
  out 30 long, and gaps under 4 ticks are filled. A change of A while the output is held
  waits and is applied when the hold ends (A is read again then). Tested: the five
  targets, and 60 random flip sequences per setting (`scripts/rtest.py` in
  `experiments/wip/door3x3/`): the output ends equal to A, and no level is shorter.
- **How:** lockout repeater X (delay 2) from A to the output wire. Two subtracting
  comparators point into X's sides:
  - OFFL: side = the output wire, rear = the wire D late. It is on for D + 2 ticks after
    the output turns off.
  - ONL: rear = the wire, side = the wire D late through a repeater. It is on for D + 2
    after the output turns on.

  A lock engages 2 ticks after X changes (wire inputs), and X cannot change again sooner
  than 4 ticks after its last change. A new request therefore always meets the lock
  (with X at delay 1, or a repeater in a lock's input, short requests slip through).
- **Tuning:** click the three repeaters of each lock: D = 6..24 ticks, held D + 6
  (tested: D = 6 → 12, D = 24 → 30). **Keep both D within 6 ticks of each other:** each
  lock compares the output with its own delayed copy, so it only works if the level
  before it lasted at least its D. With D = 14 (on) and 24 (off), random flips gave levels
  of 4 and 5 ticks.
- **Strengths:** OFFL's rear wire (12) must be weaker than its side wire (14), or the
  comparator leaks 1 and locks X for good; ONL's side is a repeater (15) against a weak
  rear wire (6).
- **Used by:** [[#3x3 flush door]] (with D = 24 and 22 between its input torch and its
  trunk).

### T flip-flop

A copper bulb toggles on every rising edge of its power; a comparator reads it.
`t_flipflop.cli.txt`. **Verified.**

| Port | Offset | Kind |
|---|---|---|
| T | 0 0 0 | copper bulb: power it (lever, wire, repeater, powered block) |
| Q | 1 0 0 | comparator facing east reading the bulb: 15 while lit |

- **Behavior:** each rising edge of T toggles Q; falling edges do nothing.
- **Latency:** bulb 0, Q 2 ticks.
- **Pulses:** any pulse toggles it once, even 1 tick long and circuit-made (R-003).
- **State:** the bulb's `lit`; built unlit. Reset: none (toggle it).
- **Pitfall:** a bulb **placed** next to something that already powers it lights at once
  (placement is a rising edge). Pasting the module (`import`, strict) keeps it unlit; to
  place one next to power unlit, use `set POS copper_bulb[lit=false,powered=true]`
  (V: the first counter build started at 14 because of this).

### RS latch

Two torches, each on a block the other's wire powers. `rs_latch.cli.txt`. **Verified.**

| Port | Offset | Kind |
|---|---|---|
| R | 0 0 0 | reset input block (power it from the west or north) |
| Q | 1 0 0 | wall torch facing east: Q (powers 1 0 −1 and the block above) |
| S | 2 0 3 | set input block (power it from the east or south) |
| NQ | 1 0 3 | wall torch facing west: ¬Q (powers 1 0 4) |

- **Behavior:** power S → Q on (NQ off after 2, Q on after 4); power R → Q off after 2
  (NQ on after 4). It holds when both inputs are off. Built reset (Q off).
- **Pulses:** a 2-tick lever pulse switches it; a 1-tick pulse does not (torch).
  Circuit-made pulses need 3+ ticks.
- **Failure case:** S and R both on turn **both** torches off; when they are released
  the result depends on the order (avoid it).

### D latch

A repeater locked by a second repeater at its side. `d_latch.cli.txt`. **Verified.**

| Port | Offset | Kind |
|---|---|---|
| D | 0 0 0 | data: wire, drive it from the west |
| Q | 1 0 0 | repeater facing east (delay 1) |
| LOCK | 1 0 1 | repeater facing north into Q's side |
| E | 1 0 2 | enable: wire, drive it from the south; **on = hold** |

- **Behavior:** E off: Q follows D after 2 ticks. E on: Q is locked 2 ticks later and
  holds. E off again: Q follows D 4 ticks after E fell.
- **Setup time:** D must change **at least 1 tick before** E rises to be captured
  (tested: D at E−1 is captured; D in the same tick as E is not).
- **Locking:** only repeaters and comparators pointing into a repeater's side lock it
  (R-004: wire beside it does not).

### Shift register

Four repeater latches in a row share one lock bus; each clock edge opens all of them for
exactly 4 ticks. `shift_register.cli.txt` (pastes `rising_edge.nbt` for the clock).
**Verified.**

| Port | Offset | Kind |
|---|---|---|
| CLK | 0 0 0 | clock input wire (rising edges count); drive it from the west |
| D | 9 0 2 | data input wire; drive it from the west |
| Q0…Q3 | 10, 12, 14, 16 (x), 0 2 | the latches (repeaters facing east): Q0 newest |

(Offsets from the lowest corner, 0 1 −2 in the script.)

- **Behavior:** each rising clock edge shifts D into Q0 and Qk into Qk+1, **8 ticks**
  after the edge (tested: 1, 0, 1, 1 shifted in → Q0..Q3 = 1, 1, 0, 1). Data changes
  between edges do not get in.
- **Why exactly one step:** the unlock window is 4 ticks. A latch switches 2 ticks
  after unlocking; its right neighbor would switch 2 ticks after that, but by then the
  lock is back: the lock repeaters turn on before the latches' ticks in the same tick
  (priority −3, [[R-012-same-tick-order]]) and a locked repeater drops a waiting change
  ([[R-006-repeater-locking]]). Measured on a test bench: windows of **2 ticks shift
  nothing, 3–4 ticks one stage, 5 ticks two stages** (race-through).
- **Timing:** D must be stable during the window (6–8 ticks after the clock edge); clock
  edges at least 20 ticks apart tested.

### 4x1 RAM

Four 1-bit words with a 2-bit address, a write input and one output. `ram4.cli.txt`,
generated by `tools/circuitgen/ram4.py`. **Verified.**

| Port | Offset | Kind |
|---|---|---|
| A1, A0 | 0 0 0, 4 0 0 | address: wires at the north edge (script 0 1 −6, 4 1 −6); drive them from the north |
| W | 8 0 0 | write: wire (script 8 1 −6); on for 2+ ticks writes D into word A |
| D | 10 0 0 | data: wire (script 10 1 −6) |
| OUT | 15 2 41 | repeater facing south (script 15 3 35): the addressed word |

(Offsets from the module's lowest corner, 0 1 −6 in the script. It rests on a floor.)

- **How it works:** the inputs become six **literal columns** on the floor, A1, ¬A1, A0,
  ¬A0, ¬W and D, all 2 ticks late (a repeater or a torch), so a bit and its complement
  change together. Each column runs south through 12 crossings: a repeater, a stone, then
  under a line on the top layer (y=3). Where a line needs a literal, a wire on the
  crossing's stone steps up into the line: a **tap**, one way only (the line cannot power
  the column back: the stone under the tap is only weakly powered by it). Per word m
  three lines: READ_m = "A ≠ m" (two taps), D_m, and LOCK_m = "¬W or A ≠ m" (three taps).
  LOCK_m holds the word's latch (a repeater locked from its side, as in [[#D latch]]);
  READ_m blocks the word's read comparator (latch − 15·READ), and the four read
  comparators feed one OUT bus through stones.
- **Behavior** (targets): write 1, 0, 1, 1 and read them back (`store`); overwrite a 1
  with a 0 while another word keeps its 1 (`overwrite`).
- **Read:** OUT shows the addressed word **32 ticks** after the address changes. Every
  word's read path is balanced to 32 (its three read repeaters get delays 4/4/2, 3/2/2,
  2/2/1, 1/1/1 against the column and bus differences), so switching between two words
  that both hold 1 never dips (`switch`).
- **Write:** W on for **2 ticks or more** (1 tick does nothing: the ¬W torch ignores it,
  `short`). D is sampled **2 ticks after W falls** (`sample`: a change then still counts,
  one a tick later does not). The address must not change while W is on; a change 1 tick
  before W falls is still safe, 2 ticks before writes the new word too (**failure case**
  `address_late`). The stored bit appears 14 (word 0) to 32 (word 3) ticks after W.
- **Larger:** more words need more lines (3 per word) and more address literals; the
  crossing rows add 2 ticks each to every column. Wider words: one D column and one
  latch/read gate per bit and word, the same READ and LOCK lines.

## Clocks

### Clock

A subtracting comparator whose output loops back through a repeater into its side.
`clock.cli.txt`. **Verified.**

| Port | Offset | Kind |
|---|---|---|
| EN | 0 0 0 | enable: wire into the comparator's rear; drive it from the west |
| OUT | 1 0 0 | comparator facing east, subtract |
| DELAY | 1 0 1 | loop repeater facing north; delay d |

- **Behavior:** while EN is on: OUT on 2d+2 ticks, off 2d+2 (period **4d+4**: 8, 12, 16,
  20), starting 2 ticks after EN. Stops (output 0) 2 ticks after EN goes off.
- **No burnout:** no torch. The same loop with a torch instead (torch clock) has the same
  period but burns out at d = 1 (8 turn-offs within 60 ticks; it relights 160 ticks
  later and burns out again; seen in the clock experiment, R-007 in [[backlog]]).
- **Tested:** d = 1 (period 8, on at 4..7, 12..15, …; off from 32 when EN falls at 30);
  d = 4 (period 20).

### Observer clock

Two observers watching each other. `observer_clock.cli.txt`. **Verified.**

| Port | Offset | Kind |
|---|---|---|
| OUT | 0 0 0 | observer facing east (watches the other), output west |
| OUT2 | 1 0 0 | observer facing west, output east |

- **Behavior:** each output is on 2 ticks, off 4 (period **6**), OUT2 2 ticks after OUT.
  Free-running: no enable.
- **Starting:** built in a world, it starts by itself; **pasted from the .nbt it does
  not** (structure files carry no scheduled ticks): break and place one observer again
  to start it (tested).
- **Output** is a circuit-made 2-tick pulse (torches and comparators ignore it).

### Hopper clock

Two hoppers pass N items back and forth; a copper bulb remembers the direction.
`hopper_clock.cli.txt`. **Verified.** Built for this library from [[R-011-hoppers]]
(hopper timing) and [[#T flip-flop]] (bulb).

| Port | Offset | Kind |
|---|---|---|
| H1, H2 | 4 0 3, 5 0 3 | hoppers facing each other; H1 holds the N items at the start |
| OUT | 6 0 2 | repeater facing east: the clock output |
| STOP | 4 1 4 | wire (y = 2 in the script): power it to freeze the clock |

- **Behavior:** OUT on for **8·N ticks**, off for **8·N − 2** (period **16·N − 2**; N = 5:
  78 ticks, 40 on / 38 off). Measured for N = 2, 3, 5, 10; N = 1 gives 8 on / 7 off.
  Runs by itself; a pasted copy starts by itself too (hoppers tick without updates).
- **How:** comparators read both hoppers; torches on the blocks they power are lit while
  their hopper is **empty**; both torches feed one wire into the copper bulb, which
  toggles each time a hopper runs empty (the torch turning off again does nothing to a
  bulb, and both hoppers are never empty at once). The bulb's comparator locks H2 (H1
  drains into H2) through a stone; a torch on that stone locks H1 while the bulb is off
  (H2 drains back). The torches and the bulb make the hysteresis that a plain "lock the
  full one" rule lacks.
- **Tuning:** `container 4 1 3 0 stone N` (script coordinates) sets N (1–64 per slot; more
  slots for more).
- **STOP:** both hoppers locked; the state holds. Released, the next item moves on the
  next tick; since the 8-tick cooldown keeps running while stopped, a phase is extended
  by the stop time minus the cooldown already elapsed (stopped 20..60: phase end 43 → 77).
- **Constraints:** nothing else may power the hoppers or the stone 5 0 2; the output
  repeater's south side faces C2 harmlessly (a comparator pointing east does not lock it).

## Arithmetic

### Full adder

One bit of binary addition, built to be pasted side by side. `full_adder.cli.txt` (its
layout is generated by `tools/circuitgen/full_adder_layout.py`). **Verified.**

| Port | Offset | Kind |
|---|---|---|
| A | 10 2 0 | wire; drive it from the **north** (script 7 3 −5) |
| B | 14 2 0 | wire; drive it from the north (script 11 3 −5) |
| CIN | 0 2 5 | wire; drive it from the **west** (script −3 3 0); any strength from 1 (it feeds two repeaters) |
| COUT | 16 3 5 | wire at the east edge, strength 3, on the stone 16 2 5 (script 13 4 0); it steps down onto the next copy's CIN wire |
| S | 4 0 12 | wire on the bottom layer at the south edge, pointing south (script 1 1 7) |

(Offsets from the module's lowest corner, −3 1 −5 in the script. The bottom layer holds
wires: paste it on a solid floor.)

- **Logic** (all comparators subtract; H = A ⊕ B): an XOR (two comparators into one stone,
  all four inputs through delay-1 repeaters, as in [[#XOR gate]]); a carry stone YC fed by
  G1 = A − H and G2 = C − ¬H (COUT = H ? C : A, the [[#Analog multiplexer]] idea); a sum
  stone YS fed by G3 = C − H and G4 = ¬C − ¬H (S = H ⊕ C). The two comparators of each
  column share one side wire (H, or ¬H) between them.
- **Behavior:** truth table (8 rows) and, in [[#4-bit adder]], all 512 additions.
- **Carry path:** the CIN repeater, the C stone, G2, YC, then **wire only**: YC is strongly
  powered at 15, so the wire on top of it climbs to the top layer (y=5) and runs straight
  east over the core, the A port and the XOR to the east edge: 15 wires, strength 2 at
  the next copy's CIN, which only feeds repeaters (its CIN repeater, and the repeater that
  starts the C route round the south to G3).
- **Latency:** A or B → S 8 ticks, → COUT 8; CIN → S 6, → COUT 4 (one repeater and one
  comparator: 4 ticks per bit, half the first version's 8, which had two more repeaters
  on its route over the top). Single input changes never glitch (all 24
  checked); when several inputs change together an output can glitch for 2–4 ticks before
  settling (the CIN paths are faster than the A/B paths), as in any ripple adder. The
  top-layer wire weakly powers the stones under it, harmless here: nothing below them
  reads a block from above.
- **Design rules found while building it** (each one broke an earlier version):
  - An XOR's output is enclosed by its own input wiring in the plane: it must leave
    vertically (here: a wire under the H stone, then the bottom layer).
  - A subtracting comparator blocks only if its side is at least its rear: side inputs
    need full strength (repeaters, torches, or wire right next to a 15 source); a long
    side wire (14, 13, …) lets a weak "1" through. Rears may be weak.
  - Weak inputs into the XOR made H weak, and H died out on its way to the core: feed
    comparators that drive long wires through repeaters.
  - H and ¬H must reach the gates in the same tick (¬H's torch fed from the H line, not
    from after H's repeater), and A must reach G1 with H (A through a delay-3 repeater):
    otherwise a 2-tick dropout and a 4-tick false carry (targets `hazards`).
  - Levels as lanes: logic on y=3, supports on y=2, a free bottom layer y=1 under them
    (H, S) and a top layer y=5 (COUT) to cross the A and B wires; a wire may pass under a
    support block, and a block may sit over a wire.

### 4-bit adder

Four [[#Full adder]] copies pasted 17 blocks apart; each COUT wire steps down onto the
next CIN wire, so the carry needs no extra wiring and no repeater between the copies. `adder4.cli.txt` (imports `full_adder.nbt`; run
from the repository root). **Verified.**

| Port | Position in the script | Kind |
|---|---|---|
| A0..A3, B0..B3 | 7+17i 3 −6, 11+17i 3 −6 | levers on the copies' A and B wires (bit 0 west) |
| CIN | −4 3 0 | lever on bit 0's CIN |
| S0..S3 | 1+17i 1 7 | sum wires (lamps south of them) |
| COUT | 65 3 0 | repeater after bit 3's COUT (it reads the stone under bit 3's last wire) |

- **Behavior:** all 512 combinations of A, B and CIN give A + B + CIN (checked once with
  every row, about a minute; the script keeps 48, including every longest carry chain
  A + (15 − A) + CIN). To rerun: the script's `add` target with all 512 rows from
  `tools/circuitgen/adder4.py`'s `row(a, b, c)`.
- **Latency:** the carry ripples **4 ticks per bit**: 1111 + 0000 with CIN on at 10 → S0
  off at 16, S1 20, S2 24, S3 28, COUT on at 28 (the repeater; bit 3's COUT wire at 26;
  target `ripple`). Read the outputs **24 ticks** after the inputs change (the truth
  table's settle; all 512 additions also pass at 22, while at 20 64 rows still show an
  unsettled S3); before that they may change more than once.
- **Composition:** pasting (`import`) keeps every state; the carry wires join when the
  first carry changes (wire takes power from adjacent wire whatever its shape).
- **Faster still:** 2 ticks per bit needs the next bit's G2 to read YC directly (no
  repeater to restore the strength, so no 17-block wire between them): a bit-sliced
  layout with the bits 2 blocks apart along the carry, or a carry skip ([[backlog]] Q15).

## Compositions

### 4-bit counter

Four [[#T flip-flop]]s chained through three [[#NOT gate]]s, pasted from the library's
`.nbt` files: bit k's comparator powers a NOT gate's input block, whose torch powers bit
k+1's bulb, so bit k+1 toggles when bit k falls. `counter4.cli.txt`. **Verified.**

| Port | Offset | Kind |
|---|---|---|
| IN | 0 0 0 | the first bulb: any rising edge next to it counts |
| Q0…Q3 | 1, 5, 9, 13 (x) | comparators: bit k = 15 while set |

- **Behavior:** counts rising edges modulo 16, from 0.
- **Latency:** bit k settles **2 + 4k** ticks after the edge (ripple: 4 ticks per bit:
  comparator 2 + torch 2). Read all four bits at least 14 ticks after an edge.
- **Rate:** tested with one edge every 20 ticks (16 edges, every count checked; the 7 → 8
  ripple checked tick by tick), with lever edges **every 2 ticks** (11 edges → 1011),
  and driven by an [[#Observer clock]] (2-tick pulses every 6 ticks: bit k has period
  12·2^k). The 2-tick case works although bit 0's comparator then makes 2-tick pulses
  into bit 1's torch: its switch-off was scheduled after the torch's tick (the player's
  edge comes after the tick's scheduled ticks), the [[R-012-same-tick-order]] exception.
  Faster than one edge per 2 ticks is not possible with levers; read the count at least
  14 ticks after the last edge.
- **Integration findings:** the pasted modules keep their states, so later bulbs sit
  unlit and unpowered next to lit torches and only react when those torches change: the
  counter starts at 0 with no reset step. The NOT gate's input block takes the comparator
  output directly (a comparator strongly powers the block it points into).

### 2x2 piston door

Four sticky pistons, two per side, hold the door stones; a wall torch per side inverts the
input. `piston_door_2x2.cli.txt`. **Verified.**

| Port | Offset | Kind |
|---|---|---|
| DOOR | 4..5 0..1 0 | the four door cells (seen from the south) |
| IN | 4 0 2 | the input wire bus (0..9 0 2): power any part of it to open |

- **Behavior:** input on → all four cells clear **4 ticks** later (pistons retract in the
  tick the torches go out: same-tick start, [[R-009-pistons]]); input off → the stones
  start moving back after **4 ticks** and are solid after **6**.
- **Pulses:** the door stays open as long as the input; a stone button opens it for 20
  ticks (cells clear 6..25). **Failure case:** an input pulse of 2 ticks or less does
  nothing (the repeaters turn it into a circuit-made 2-tick pulse, which the torches
  ignore, R-003); 3 ticks open it briefly.
- **Design notes:** each torch hangs on its own input block, which touches no piston; the
  torch powers the lower piston directly and the upper one through the stone above the
  torch (a torch strongly powers the block above it). **Pitfall found:** the first build
  stood the torch on a block next to the lower piston; the input powering that block also
  powered the piston, so the lower half never opened (V).
- **Floor:** the door stones rest on the floor and are not slime: nothing else moves.

### 3x3 flush door

Nine door blocks, flush with the wall when closed and with the wall and floor when open.
Eight move one cell (sides into the wall, top up into the frame, bottom middle down);
the center moves two cells down, which plain sticky pistons cannot do directly
(backlog Q18): it goes down in two steps through a gap that a third piston makes. A
lockout makes it **input-safe**: no input timing leaves it stuck. `door_3x3.cli.txt`,
generated by `experiments/wip/door3x3/scripts/make_lib.py` (the stages that led to it,
failures included, are worlds in that folder). **Verified.**

| Port | Offset | Kind |
|---|---|---|
| DOOR | 7..9 3..5 2 | the nine door cells (smooth stone), seen from the south (script 7..9 4..6 2, labels @D00..@D22) |
| IN | 8 1 11 | input block: power it to open (script 8 2 11; test lever @L on top) |

- **Behavior:** input on → the six side cells and the top clear **8 ticks** later, all
  nine **32 ticks** later; input off → all nine solid **17 ticks** later (sides after 10).
  The center leaves last because it passes through the bottom-middle cell on its way down.
- **Any input timing works:** a request that comes while a sequence runs waits and is
  carried out after it. Tested: every open request and every close gap of 1–30 ticks, 45
  close / re-open / re-close patterns, 120 random flip sequences
  (`experiments/wip/door3x3/scripts/suite*.py`), a lever flipped every 3 ticks, and a stone
  button (it opens fully 37..42 and closes by 52).
- **Center column:** C (center) and M (bottom middle) rest in the floor when open (C 8 3 2,
  M 9 3 2). Under C: sticky piston B (8 2 2) standing on sticky piston A (8 1 2); W
  (10 3 2) pushes M west. Close: B gets a 2-tick pulse and **spits** C up one; W pushes M
  under C; B pushes both up and holds them. Open: B pulls M down; W pulls M aside; A lifts
  B into the floor; B extends into the gap and pulls C down one; A lowers B; B extends
  again and pulls C into the floor.
- **Sides and top:** three sticky pistons per side in the wall plane and one above the
  frame. Each side is powered by a wire staircase in the wall plane: the lowest piston
  through the block behind it, the middle one by a wire pointing into it, the top one
  through the block above it. A glass step keeps a support block from cutting a wire step,
  and the left staircase continues over the frame into the top piston.
- **Lockout:** the input block's torch feeds repeater @X (delay 2, 4 ticks), which feeds the
  trunk. @X is **locked** ([[R-006-repeater-locking]]) after each change of its own output
  by one of two subtracting comparators pointing into its sides:
  - @OFFL: rear = the trunk 24 ticks late, side = the trunk; locked for 26 ticks after
    @X turns off, while the open runs;
  - @ONL: rear = the trunk, side = the trunk 22 ticks late; locked for 24 ticks after @X
    turns on (the close itself needs 17).

  Each lock engages 2 ticks after @X's output changes (wire inputs, no repeater), and
  @X cannot change again sooner than 4 ticks after its last change, so a new request
  always meets the lock and is read when the lock ends. **Found on the way:**
  - With @X at delay 1 and repeaters in the locks' inputs, requests of 2–4 ticks slipped
    through.
  - **Both lock delays must be within 6 ticks of each other.** Each lock compares the
    output with a delayed copy of itself, so it only works if the level before it lasted
    at least its delay. With 8 for the close lock and 24 for the open lock, a re-open 12–14
    ticks after a close followed by a re-close 12 ticks later stuck the door (now target
    `reopen`).
  - @OFFL's rear wire must be weaker than its side wire (13 against 14), or the comparator
    leaks 1 and locks @X for good.
  - If @X were locked on the trunk's raw input instead of its own output, its own
    legitimate change would be dropped too.
- **Controller** (behind the wall): the trunk feeds short repeater branches.
  - The spit is an observer behind B watching a wire spur. A repeater keeps a 2-tick pulse
    (a comparator edge detector would give 4 or more, which pulls C back instead of
    spitting it). It also fires on the falling edge, while B still holds.
  - B's hold is the floor block 7 3 2, through quasi-connectivity. B extends exactly
    when M lands under C (the landing updates B, [[R-025-piston-door-timing]]).
  - W's driver is **locked** by a delayed copy of the trunk. W stays out after its input
    turns off, until B has pulled M down. This gives W its asymmetric timing (on before
    B's hold, off after it) without a second delay line.
  - A gets an 8-tick pulse from a subtracting comparator (rear 18, side 10 ticks after
    the trunk), on falling edges only.
  - An observer in front watches A. Its pulse reaches the floor block 7 3 2 through
    wire: when A extends, that powers B in its raised position; when A retracts, it is
    there as B lands at home, and B extends by quasi-connectivity (the final pull).
- **Failure case:** 16 lever flips within 48 ticks burn out the input torch (8 turn-offs
  in 60 ticks, [[R-007-torch-burnout]]). The door then opens and stays open until the
  torch relights, about 160 ticks later (target `burnout`).
- **Without the lockout** (`door.py module`, WIP 06) the door is 4 ticks faster (clear
  28, solid 13), but it needs its input on at least 25 ticks and off at least 7. A stone
  button sticks it with the center cell empty, and so do open requests of 2, 9–13 and
  18–24 ticks (WIP 05b).
- **Pitfalls found:** an observer placed before the wire it watches sees the wire being
  built and fires during `settle` (here it spat C into the doorway of the fresh build):
  place it last. W may only be powered after B's head has left the floor cell (in the same
  tick its push fails on the moving head and nothing updates it again). W may only retract
  after M has landed (a sticky piston does not pull a block that moves another way).
- **Build:** the script builds the door open with the test lever on, flips the lever off
  and rebases at tick 40, so the world and the `.nbt` hold the closed door.
- **Speed so far:** the first controller (WIP 04) took 37 ticks to open and 16 to close.
  The hold through quasi-connectivity, the observer behind B and wire instead of repeaters
  for the observer's pulses brought it to 28 and 13; the lockout adds 4 on each edge.

### Monostable

A rising edge turns the output on for exactly D ticks, whatever the input does
meanwhile: a [[#Rising-edge detector]] makes a 4-tick pulse that toggles a copper bulb
on at once and, through a delay line, off again D ticks later. `monostable.cli.txt`
(pasted from `rising_edge.nbt` plus a bulb and repeaters). **Verified.**

| Port | Offset | Kind |
|---|---|---|
| A | 0 0 5 | input wire; drive it from the west (script: 0 1 0) |
| Q | 4 0 5 | comparator reading the bulb (script: 4 1 0) |

- **Behavior:** Q on **4 ticks** after A rises, for **D = 64 ticks** (eight delay-4
  repeaters, 8 ticks each). A held input still gives exactly D (only the edge counts).
- **Tuning:** D = the delay line's total (each repeater 2·delay ticks); keep D > 8 so the
  echo does not overlap the 4-tick start pulse (stretched to 8 by the line's repeaters).
- **Failure case (not retriggerable):** a second edge while it runs toggles the bulb off
  early, and the two echoes toggle it on and off again later (tested: edges at 2 and 28
  → Q on 6..31, off 32..69, on 70..95). Block re-triggers upstream if needed.
- **Why a bulb:** it toggles on rising edges of its power only, so the start pulse and
  its echo (both through the same bulb) give one clean on-off.

### Combination lock

Four levers compared to a key (1 0 1 1); right → `OPEN` lights and the [[#2x2 piston
door]] (pasted from its `.nbt`) opens. `combination_lock.cli.txt`. **Verified.**

| Port | Offset | Kind |
|---|---|---|
| K0…K3 | 0, 2, 4, 6 (x), 0 0 0 | levers on the north faces of the key stones |
| OPEN | 10 0 2 | wall torch: lit only while all four levers match the key |
| DOOR | 6..7 0..1 6 | the door cells |

- **How:** a "wrong" bus of wire runs beside the key stones (y = 2). A key-1 lever's
  stone carries a torch next to the bus (lit = lever off = wrong); a key-0 lever's stone
  carries a wire that joins the bus (lever on = stone strongly powered = wrong). OPEN is
  a torch on the stone the bus points into: a NOR of the wrong terms. Change the key by
  swapping torch and wire on a stone.
- **Behavior:** all 16 lever combinations checked: OPEN only for 1 0 1 1. OPEN lights 4
  ticks after the last right lever (a key-1 lever: its torch 2 + OPEN 2; a key-0 lever
  turned off: 2); the door opens 10 ticks after it (route repeater 2, door 4 + 2… cells
  clear at +10); a wrong lever closes it (moving at +8, solid at +10).
- **Integration findings (V, both in the first build):**
  1. Torches placed **in** the bus line split it: power does not pass through a torch, so
     a wrong key-0 lever west of a torch never reached OPEN. Put torches *beside* a bus.
  2. The route from OPEN to the door ran past the door's input block. When the door
     opened, that block was strongly powered, the passing wire took its power (R-002)
     and fed the bus: the door **latched open**. Keep wires one block away from blocks
     other circuits power strongly.
  3. Fed from its far end, the door's 10-wire bus lost too much strength to reach the
     other side: one door half did not open. A repeater right before the bus fixed it.

### Toggle door

A button toggles the [[#2x2 piston door]]: a [[#T flip-flop]] (copper bulb with the
button on its face) whose comparator points into the middle of the door's input bus.
`toggle_door.cli.txt`. **Verified** (worked as composed, first try).

| Port | Offset | Kind |
|---|---|---|
| B | 4 0 5 | stone button on the bulb's south face (any rising edge at the bulb works) |
| DOOR | 4..5 0..1 0 | the door cells |

- **Behavior:** each press toggles: open (cells clear) **6 ticks** after an opening
  press; closing starts 6 ticks after a closing press, solid after **8**.
- **Why the middle of the bus:** fed at x=4 the 10-wire bus keeps ≥ 10 at both ends
  (see the [[#Combination lock]]'s third finding).

### Flying machine

Two groups that move each other: a honey group (observer, sticky piston facing east,
two honey blocks) and a slime group (two slime blocks, sticky piston facing west,
observer), with a one-block gap between them. Honey and slime do not stick to each
other. `flying_machine.cli.txt` (built in a world without floor). **Verified.**

| Port | Offset | Kind |
|---|---|---|
| OB, P1 | 0 0 0, 1 0 0 | honey group's observer (watches west) and sticky piston (faces east) |
| P2, OA | 3 1 0, 4 1 0 | slime group's sticky piston (faces west) and observer (watches east) |
| start east / west | 5 1 0 / −1 0 0 | change the block OA / OB watches (set a block and remove it) |

(Offsets from the lowest corner, 0 10 0 in the script.)

- **Behavior:** once started it moves **1 block every 10 ticks** (2 blocks per second)
  in the direction of the observer that was triggered: started at OA's side it flies
  east, at OB's side west. Each group's observer fires 2 ticks after its group lands
  ([[R-015-moving-observers]]) and fires its own piston: one piston extends into the gap
  and pulls the other group over, the other pushes the other group away and leaves it.
- **Stops** when a push fails: tested with obsidian in the path (the slime ends against
  it, the honey group closes up, nothing fires again). More than 12 blocks, block
  entities or immovable blocks in the way do the same ([[R-009-pistons]]).
- **Build it in the air:** slime grabs any pushable block it touches, including the
  ground (R-009).
- **Pitfalls found:** built with `set`, observers carry start-up ticks: one version fired
  both pistons together and did not move; another moved an observer while it was
  powered, which killed its pulse. Building it closed (no gap) and running `settle`
  leaves it at rest with the gaps open; the pasted `.nbt` is in that rest state.

### Double piston extender

Two sticky pistons in a row (A behind B) push a block two cells and bring it back, run
by three timed control signals from one lever. `double_piston_extender.cli.txt`
(lowest corner −4 1 0 in the script). **Verified** (it worked as designed on the first
build; the input limit below was found afterwards).

| Port | Script position | Kind |
|---|---|---|
| IN | the wire bus 1 1 9 (z = 9, x −4…6) | any power on the bus; the test lever is at 1 1 10 |
| A, B | 0 2 0, 1 2 0 | sticky pistons facing east (B is moved by A) |
| X | 2 2 0 → 4 2 0 | the moved block (home, two out) |

- **Sequence (lever at r, off at f):** A extends at r+4 (B and X move one out, X at 3
  by r+6); B's out-position block is powered at r+8 and B pushes X to 4 by **r+10**.
  Back: B retracts at f+8 (X back to 3 by f+10); A retracts at f+12 and pulls B home
  (X stays at 3: a retracted piston's face does not pull when it is moved); a pulse at
  B's home block (f+18) makes B extend into the gap and pull X home by **f+24**.
- **How the timing is made:** B's power block sits under B's *out* position, so B is
  only powered once A has moved it there (and the pull pulse sits under B's *home*).
  A's power is the input OR a 10-tick delayed copy (a block fed by two repeaters), so A
  holds until B is back. The pull pulse is a [[#Falling-edge detector]] fed 12 ticks
  late. Rules behind it: same-tick piston start ([[R-009-pistons]]), extended pistons
  cannot be pushed, pulling across a gap ([[R-015-moving-observers]]).
- **Input:** hold it at least **8 ticks** (a lever, a button: 20). **Failure case:**
  with a 4-tick input the direct path into A's block ends before the delayed copy
  starts, A's power has a gap, A pulls B back mid-way and X never gets two out (it
  still ends at home). General lesson: an OR of a signal and its delayed copy has a gap
  when the signal is shorter than the delay.

### Item sorter

A filter hopper under a hopper line takes only one item type; a comparator lock lets a
bottom hopper drain every extra item into a chest (here a barrel).
`item_sorter.cli.txt`. **Verified** (designed from [[R-011-hoppers]] and
[[R-005-signal-strength]]).

| Part | Script position | Role |
|---|---|---|
| LINE0 … LAST | −3 3 0 … 2 3 0 | the hopper line (facing east); put items into LINE0 |
| F | 0 2 0 | filter hopper, facing north into air (it never pushes): 18 stone + 4 swords (stack 1) |
| G | 0 1 0 | bottom hopper facing the output; locked at rest |
| CF, L | 1 2 0, 2 2 0 | comparator reading F (12; 13 with one extra stone); subtracting comparator with 13 behind it: the lock = 13 − reading |
| OUT, END | −1 1 0, 3 3 0 | sorted items; everything else |

- **Behavior:** tested with 40 stone and 30 dirt at full line rate (one item per 8
  ticks): all stone left the line into OUT (one topped the filter up), all dirt reached
  END, nothing escaped (a control case without F jams the line, so the check is real).
- **Why the parts are where they are:** F must **pull** (from the line above) and
  **never push**, so it faces into air; a hopper locked to keep its stack would not pull
  either. G **pulls** from F only while unlocked. A locked hopper does not push either,
  so G keeps one item in it between unlock windows. The filter count 18 sits just below
  the reading's next step (with four stack-1 swords: 18 → 12, 19 → 13; [[signals]]
  container formula), so one extra stone flips the lock.
- **Start-up:** while the lock is being built G pulls one stone; F settles at 17 and the
  first sorted stone brings it to 18.
- **Simulator note:** items in containers only (no item entities, [[differences]]);
  there are no renamed items, so the filler is a stack-1 item instead of the usual
  renamed ones, which changes the counts (classic sorters use 41 + four renamed items).

### Timed door

The worked requirement of [[workflow]]: either of two buttons opens the [[#2x2 piston
door]]; it closes about 5 s after the last press. A [[#Fade timer]] (retriggerable)
plus a 24-tick off-delay drive the door bus. `timed_door.cli.txt` (lowest corner −2 1 0
in the script). **Verified.**

| Port | Script position | Kind |
|---|---|---|
| B1, B2 | −2 1 10, −2 1 4 | floor buttons beside the input wire (x = −1) |
| DOOR | 4..5 1..2 0 | the door cells |

- **Behavior:** a press opens the door after **18 ticks**; closing starts **102 ticks
  after the last press** (solid at 104). A press while open (either button) restarts the
  time (tested: presses at 2 and 60 → open until 161). Reopens normally after closing.
- **Bugs found while building it** (see [[workflow]]): a tap on a wire that joined the
  door bus let the bus feed itself back (door never closed); a two-timer cascade closed
  after 134 ticks. Both are composition rules now.

### Binary decoder

Four bits in, one of 16 outputs on: [[#4-bit DAC]] turns the bits into the strength N on
its OUT stone, and [[#Signal-strength decoder]] is pasted so that this stone is its input.
`bin_decoder16.cli.txt` (imports `decoder16.nbt` and `dac4.nbt`; run from the repository
root). **Verified.**

| Port | Script position | Kind |
|---|---|---|
| B0..B3 | west of −1 1 4, −1 1 −4, −1 1 2, −1 1 −2 | dac4's inputs (levers @L0..@L3 at x = −2) |
| O0 | 6 1 −4 | repeater facing north: on while N = 0 |
| Om, even m ≥ 2 | m+5 1 −4 | facing north |
| Om, odd m | m+5 1 4 | facing south |

- **Composition:** decoder16 pasted with its corner at 4 1 −4 (its input on dac4's OUT
  stone), then dac4 at −1 1 −5: the second paste replaces the decoder's input barrel with
  the stone (a paste includes its air, so the module whose cells must win goes last).
- **Behavior:** the 16-row truth table (target `decode`) and a jump sequence. All 240
  changes between two inputs were checked once: the old output alone until 21 ticks after
  the change, the new one alone from 22; no other output ever flashes (both parts switch
  everything in one tick).
- **Latency:** **22 ticks** (12 + 10).
- **Uses:** addressing (one of 16 memory cells or actions), lighting one lamp per value,
  the first half of a lookup table or 7-segment display (each segment an OR of outputs,
  [[backlog]]).

### Lookup table

Any table of 16 words: [[#Signal-strength decoder]] gives one line per value, the lines
turn into 16 rows on the floor, and each row taps the output lines of its word's 1 bits.
Two tables from `tools/circuitgen/rom16.py`: **`seg7`**, a hex 7-segment decoder (four
bits through [[#Binary decoder]], segments a..g out), and **`adc4`**, an ADC (a strength
in decoder16's input, its value as four bits out). **Verified.**

| Port | Script position | Kind |
|---|---|---|
| seg7 B0..B3 | −1 1 4, −1 1 −4, −1 1 2, −1 1 −2 | dac4's inputs (levers @L0..@L3 at x = −2) |
| seg7 a..g | 24+3k 3 21, k = 0..6 | repeaters facing south: segment k lit |
| adc4 IN | 4 1 0 | decoder16's input: a container or a block powered with the strength |
| adc4 B0..B3 | 24+3k 3 21, k = 0..3 | repeaters facing south: bit k |

(Boxes: seg7 −1 1 −21 .. 42 3 21, adc4 4 1 −21 .. 33 3 21; both pasteable.)

- **Rows by nested corners:** decoder16's outputs leave it to the north (even values) and
  south (odd); each runs out to its own row z (±6 … ±20, 2 apart), turns east and runs
  to the table. The output **farthest east turns first**, so no row crosses another
  output's path. Each path has exactly two repeaters (one leaving the decoder, one after
  the corner), so all 16 rows are equally late. O0 sits beside O2: a stone on its output
  cell powers the wire west of it (O2's first cell is a repeater, which ignores it).
- **OR plane:** each output line runs along z on the top layer (y=3) over the rows; a row
  crossing it passes a repeater and a stone, and a wire on the stone (where the word has
  that bit) steps up into the line: the crossbar tap of [[#4x1 RAM]]. Each line has
  repeaters at z = −7, 7 and 21 (between rows), placed so that the farthest tap of every
  segment still reaches the next repeater: **found while building**: with repeaters at
  −9 and 5, the tap at z = 6 (digit F's) arrived at the end with 0.
- **Behavior:** seg7: the 16-row truth table (`digits`); adc4: all 16 strengths in a mixed
  order (`values`).
- **Latency:** seg7 settled **46 ticks** after the bits change (measured: the truth table
  passes at 47, fails at 44), adc4 **28** after the strength; from 30 (seg7) or 18 (adc4)
  the outputs may **flicker** until then, as a row's taps reach the lines at 2 ticks per
  crossing and through 1–3 line repeaters. Read them after the settle time, or latch them.
- **Other tables:** edit the table in the generator (16 words, up to as many output lines
  as fit; each line adds 3 blocks in x and 2 ticks).

### 7-segment display

Four levers and a lamp digit that shows their value in hex (0–9, A, b, C, d, E, F): the
[[#Lookup table]] `seg7` drives seven lines into the back of a 4×7 digit of lamps.
`seg7_display.cli.txt`, generated by `tools/circuitgen/display7.py` (composition: no
`.nbt`). **Verified.**

| Port | Script position | Kind |
|---|---|---|
| L0..L3 | −2 1 4, −2 1 −4, −2 1 2, −2 1 −2 | levers on the four bits (as in `seg7`) |
| digit | lamps x 32..35, y 2..8, z 41 | seen from the south; labels @Sa..@Sg and @Ta..@Tg (the two lamps of each segment) |

- **Behavior:** all 16 values light exactly their segments, both lamps of each
  (targets `digits1`, `digits2`); settled **54 ticks** after the levers change (`seg7`'s 46,
  two repeaters on the way, the digit's repeaters, and the lamps' 4-tick off delay).
  Before that the segments may flicker, as `seg7`'s lines do.
- **The digit:** 4 wide and 7 high, two lamps per segment, dark corners so no two segments
  touch.
  - a, g and d have a repeater behind each lamp, fed by a wire one block further back.
  - b, c, e and f have a wire behind the upper lamp, standing on a block behind the
    lower one: the wire lights the upper lamp and powers the block, which lights the lower.
  - The seven feeds leave the back at distinct positions (x 32, 33, 35; heights 2, 4, 5,
    7, 8), with stones where a diagonal wire step would join two segments.
  - Tested alone first: `experiments/wip/display7/01`.
- **Routing without crossings:**
  - The decoder's output columns are in the order f e a g d b c (west to east), not a..g.
    Then every line can run to the digit's x without passing another line's x.
  - Each line climbs or drops to its feed height at its own column (3 apart), gets a
    repeater, then shifts sideways in its own row: a and d first, then e and b, then f
    and c. That is the order in which no shift passes a line still standing at its
    column.
  - A second repeater sits in the cable into the digit.
  - A stone above every wire, except above a wire's up-step, keeps wires of different
    segments from joining diagonally.
  - It worked on the first build.
- **Other tables:** `display7.py` takes the table from `rom16.py`; a different column order
  needs only `PERM` (and the shift rows: shift the lines that end innermost first).
- **Not done:** latching the segments after the settle time to hide the flicker (backlog
  Q20).

## Composition rules

To be filled as primitives are combined: how far apart modules must be, which outputs
may drive which inputs, timing budgets. Known so far:

- A torch output does **not** power a block beside it (R-002), so it cannot drive the
  next module's input *block* directly. Connect it through a repeater or wire, or put
  the next input block *above* the torch (a torch strongly powers the block above).
- A repeater or comparator output can point straight into the next module's input block
  (strong power) or wire. V `counter4` (comparator → NOT gate block).
- A torch output powers a component next to it directly (a bulb, a lamp, a repeater's
  back). V `counter4` (torch → copper bulb).
- Pasting with `import` is a strict paste: no updates, states kept exactly. A module whose
  state disagrees with its new neighbors (a bulb unpowered beside a lit torch) stays that
  way until something nearby changes. That can be what you want (`counter4`) or a hidden
  initial glitch: check the first ticks after pasting.
- Free-running modules (the [[#Observer clock]]) do not start after a paste: no scheduled
  ticks are pasted.
- **Wires beside strongly powered blocks pick up their power** (R-002): a wire routed past
  another circuit's input block can feed that circuit back into itself (the combination
  lock's door latched open). Keep one block of space.
- **Do not put components in a wire line** you want to stay one net: torches, repeaters
  and comparators split it (the combination lock's bus).
- **Mind wire length:** 15 wires from a 15 source; put a repeater right before long buses.
- **One repeater per stage on a chained path, at the receiving end:** a block a comparator
  powers at 15 drives a wire 15 blocks, and a repeater reads the weak end; route the link
  straight on its own top layer so it fits, and let the next module's input repeater
  restore it. Fan-out inside the module then starts after that repeater, or with its own
  (V `full_adder`: the carry went from 8 ticks per bit to 4).
- **Tap a signal before it joins a shared wire**, through a repeater: a tap on a wire
  that also feeds a bus receives the bus's power too (the timed door's first build
  latched itself on).
- **Check what else an input powers:** a block powered to drive one component powers
  every component touching it (the first piston door: the torch's input block also
  powered a piston). Keep input blocks away from components they must not drive.
- **An OR of a signal and its delayed copy has a gap** when the signal is shorter than
  the delay (the double piston extender with a 4-tick input). Stretch the input first
  or state a minimum input length.
- **Rings hold moving patterns:** anything that should change a ring's (loop's) whole
  contents must last at least one lap (fade timer, peak-hold register).
- **Never rely on the order in which one wire change reaches several components**
  (pistons racing, ties between equal-priority ticks): it depends on the position of the
  build ([[R-017-wire-order]]). Give the paths different delays instead.
- **A wire beside a comparator is its side input, and a wire between two comparators is
  a side input of both** (V `decoder16` control). Feed comparators in a row through
  repeaters pointing into their sides, or stagger them so no wire touches two.
- **Subtract only blocks with a full-strength side:** feed comparator sides from
  repeaters, torches or wire right beside a 15 source; rears may be weak ([[#Full adder]]).
- **Cross by level:** give long signals their own layer (a wire passes under a support
  block, a block sits over a wire) instead of crossing in the plane; an XOR's output must
  leave vertically ([[#Full adder]]).
- **Fan many signals across many lines with taps** (a crossbar): signals as columns on
  the floor, lines on the top layer (y=3) crossing over them; at a crossing the column
  passes a repeater and a stone, and a wire on that stone steps up into the line where a
  connection is wanted. One way only, any number of taps per line ([[#4x1 RAM]]). Every
  crossing row adds 2 ticks to the columns: balance what must arrive together.
- **A paste includes its air:** where two modules' boxes overlap, the one pasted last
  wins every cell, air included. Paste the module whose cells must survive last (the
  binary decoder pastes dac4 after decoder16, so its stone replaces the input barrel).
- **Turn modules so an output points into the next input:** a pasted module may be
  rotated (R-022), and a comparator output pointing straight into the next module's input
  stone needs no routing and keeps an analog strength ([[#4:1 analog selector]]).
- **A control signal shared by modules on opposite sides goes on its own top layer**, or
  it walls in whatever lies between them ([[#4:1 analog selector]]'s S0).
- **Balance path delays** into any gate whose inputs may change in the same tick: an
  input that arrives 2 ticks early makes a 2-tick glitch (a false 1 or a dropout). Add
  delay-1 repeaters to the faster paths ([[R-010-hazards]]). The same holds for select
  and address lines of different depth: delay the shallower one so all arrive together
  ([[#4:1 analog selector]]: S1 waits 6 ticks for S0).
