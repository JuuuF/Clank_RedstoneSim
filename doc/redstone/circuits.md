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
- **Ports** are given as offsets from the module's lowest corner (the scripts build every
  module with that corner at `0 1 0`, so the offsets are the script's coordinates minus
  `0 1 0`). Every module's signal flows **east** (+x) unless said otherwise.
- **Rotating:** `rotate N` turns the module N quarter turns clockwise seen from above
  (flow east → south → west → north). A port at offset (dx, dy, dz) of a module that is
  D blocks deep along z moves to (D − 1 − dz, dy, dx) for one turn. (V: `not_gate`
  imported with `rotate 1` worked with its torch on the south face.)
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

## Index

| Module | Function | Size (x×y×z) | Latency | Script |
|---|---|---|---|---|
| [[#NOT gate]] | OUT = ¬A | 2×1×1 | 2 / 2 | `not_gate` |
| [[#OR gate]] | OUT = A ∨ B, isolated | 2×1×3 | 2 / 2 | `or_gate` |
| [[#NOR gate]] | OUT = ¬(A ∨ B) | 2×1×3 | 2 / 2 | `nor_gate` |
| [[#AND gate]] | OUT = A ∧ B (also NAND) | 4×2×3 | 4 / 4 | `and_gate` |
| [[#NAND gate]] | OUT = ¬(A ∧ B) | 2×2×3 | 2 / 2 | `nand_gate` |
| [[#Compact AND]] | OUT = A ∧ B with one comparator | 2×1×4 | A 2, B 4 | `and_compact` |

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

One subtracting comparator: rear = A, side = ¬B (a torch on B's block powers a wire at
the comparator's side). `and_compact.cli.txt`. **Verified, with a hazard.**

| Port | Offset | Kind |
|---|---|---|
| A | 0 0 0 | wire into the comparator's rear; drive it from the west |
| B | 1 0 3 | input block (a torch on its north face) |
| OUT | 1 0 0 | comparator facing east, subtract mode, output 15 |

- **Behavior:** OUT = A − ¬B = A ∧ B (with full-strength A).
- **Latency:** from A 2 ticks each way; from B 4 ticks each way (torch + comparator).
- **Hazard (failure case):** if A turns on and B turns off in the same tick, OUT gives a
  **2-tick glitch** (ticks +2, +3) before settling to 0: the A path is 2 ticks faster.
  Use the torch [[#AND gate]] where inputs can change together, or delay A by a delay-1
  repeater to balance the paths (H, not tested).
- **Constraints:** A's strength passes through: A at strength N gives OUT N (R-005).
- **Tested:** truth table; A on 2, B on 10 → on 14; B off 20 → off 24; B on 30 → on 34;
  A off 40 → off 42; the glitch above.

## Composition rules

To be filled as primitives are combined: how far apart modules must be, which outputs
may drive which inputs, timing budgets. Known so far:

- A torch output does **not** power a block beside it (R-002), so it cannot drive the
  next module's input *block* directly. Connect it through a repeater or wire, or put
  the next input block *above* the torch (a torch strongly powers the block above).
- A repeater output can point straight into the next module's input block (strong
  power) or wire.
