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
| [[#Compact AND]] | OUT = A ∧ B with one comparator | 2×1×4 | 4 / 4 | `and_compact` |
| [[#XOR gate]] | OUT = A ⊕ B, glitch-free | 7×3×6 | 4 / 4 | `xor_gate` |
| [[#Rising-edge detector]] | 4-tick pulse when A turns on | 2×1×3 | 2 | `rising_edge` |
| [[#Falling-edge detector]] | 4-tick pulse when A turns off | 3×1×3 | 4 | `falling_edge` |
| [[#Both-edge detector]] | 2-tick pulse on every change of A | 2×1×1 | 2 | `both_edges` |
| [[#T flip-flop]] | toggles on each rising edge | 2×1×1 | 2 | `t_flipflop` |
| [[#RS latch]] | set / reset memory | 3×1×4 | set 4, reset 2 | `rs_latch` |
| [[#D latch]] | Q follows D, holds while E is on | 2×1×3 | 2 | `d_latch` |
| [[#Clock]] | period 4d+4 with enable, no burnout | 3×1×3 | 2 from enable | `clock` |
| [[#Observer clock]] | free-running, 2 on / 4 off | 2×1×1 | — | `observer_clock` |
| [[#Hopper clock]] | long periods: 16·N − 2 ticks for N items, with stop | 10×2×5 | — | `hopper_clock` |
| [[#4-bit counter]] | counts rising edges (composition) | 14×1×1 | bit k: 2+4k | `counter4` |
| [[#2x2 piston door]] | opens a 2×2 doorway while its input is on | 10×2×3 | open 4, close 4 (solid 6) | `piston_door_2x2` |

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

## Memory

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
  ripple checked tick by tick). Bit k is high for ≥ 20·2^k ticks, far above the torch's
  3-tick minimum; faster input is not tested (H: the limit is the first bit: input edges
  at least 4 ticks apart, R-003's merging does not apply to bulbs).
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
- **Check what else an input powers:** a block powered to drive one component powers
  every component touching it (the first piston door: the torch's input block also
  powered a piston). Keep input blocks away from components they must not drive.
- **Balance path delays** into any gate whose inputs may change in the same tick: an
  input that arrives 2 ticks early makes a 2-tick glitch (a false 1 or a dropout). Add
  delay-1 repeaters to the faster paths ([[R-010-hazards]]).
