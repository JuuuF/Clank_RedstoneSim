# Timing reference

How long each component takes, in **game ticks** (20 per second; a redstone tick is 2).
Δ is the delay from an input change at tick T (`at T use …`) to the output change, as
`delays` measures it: Δ = 0 means the output is already changed at tick T. Evidence
labels: [[redstone/README#Scope and trust]].

## Component delays (one input switched on, later off)

| Component | Input on → | Input off → | Notes | Evidence |
|---|---|---|---|---|
| Redstone lamp | lit, Δ 0 | unlit, Δ 4 | the 4-tick off delay stretches every pulse into a lamp by 4 | V [[R-001-response-times]], G EXP-001 |
| Redstone wire | Δ 0, −1 power per wire | Δ 0 | 15 wires carry power 15…1; a lamp after the 15th still lights | V R-001, G EXP-003 |
| Redstone torch (inverter) | off, Δ 2 | on, Δ 2 | its block powered → the torch turns off | V R-001, G EXP-002 |
| Repeater, delay d | on, Δ 2·d | off, Δ 2·d | d = 1…4 gives 2, 4, 6, 8 | V R-001, G EXP-008 |
| Comparator | Δ 2 | Δ 2 | compare mode, full-strength input | V R-001, G EXP-012 |
| Observer | pulse starts Δ 2 after the change it sees | — | the pulse is 2 ticks long; any change of the watched block (on *or* off) fires it | V R-001, G EXP-032 |
| Piston, sticky piston (extend) | `extended=true` Δ 1; front cell `moving_piston` Δ 1; pushed block solid at its new place Δ 3 | — | from a lever; powered by a repeater, torch, comparator or observer it starts in the **same** tick (Δ 0) and the block lands at Δ 2 (R-009) | V R-001, [[R-009-pistons]], G EXP-015 |
| Piston (retract) | — | base `moving_piston` Δ 1, head gone Δ 1, `extended=false` Δ 3 | | V R-001, G EXP-015 |
| Sticky piston (retract) | — | pulled block back in place Δ 3 (`moving_piston` at Δ 1, 2) | | V R-001, G EXP-015 |
| Dropper (and dispenser) | `triggered` Δ 0; the item leaves Δ 4 | `triggered=false` Δ 0 | a rising edge only; empty → nothing happens | V R-001, G EXP-044 |
| Note block | `powered` Δ 0 (plays) | Δ 0 | | V R-001, G EXP-042 |
| Copper bulb | toggles `lit` Δ 0 on a rising edge | `powered=false` Δ 0, `lit` kept | a T flip-flop | V R-001, G EXP-043 |
| Iron trapdoor (doors, gates) | open Δ 0 | closed Δ 0 | | V R-001, G EXP-052 |
| Powered rail | Δ 0 | Δ 0 | | V R-001, G EXP-036 |
| Hopper | `enabled=false` (locked) Δ 0 | unlocked Δ 0 | | V R-001, G EXP-039 |

## 0-tick pulses (R-013)

Power on and off at one moment (two block changes between ticks): a **repeater** turns it
into a full pulse of its delay (2 ticks later), a **lamp** flashes 4 ticks, a **copper
bulb** toggles, a **dropper** fires (4 ticks later), an observer watching the changing
block pulses once. **Comparators, torches, pistons** ignore it; wire shows nothing. V
[[R-013-zero-tick]], G EXP-027.

**Made by pistons** ([[R-018-piston-zero-tick]], G EXP-057): a redstone block spat into a
cell (below) and pushed out again by a piston woken by its arrival (a BUD piston) is there
for 0 ticks, inside one block-event phase. Repeaters, lamps and bulbs react as above and
comparators do not, but **pistons can**: a piston beside the cell whose update came before
the remover's (order around the cell: west, east, down, up, north, south) extends, and a
sticky one moves its block one cell in 0 ticks. A block that lands normally and is pushed
out the same way gives a 1-tick pulse.

**Spit timing** (R-018): a sticky piston that loses power while its block still moves
places the block at its destination at once, at its retract: a 1-tick lever pulse has the
block in place 1 tick earlier than a full push (Δ 2 instead of 3 from the lever), a 2-tick
lever pulse at the normal time, an observer's pulse 2 ticks after the start. V, G EXP-016.

## Instant transmission by pistons (R-023)

A chain of extended sticky pistons, each holding a redstone block against the back of the
next piston, collapses in **0 ticks** when its first piston moves: every piston it
depowers retracts in the same block-event phase. 3 blocks per stage, or up to 17 with a
wire line (≤ 15 blocks, also instant) between the stages; 38 blocks were tested. Only the
edge that removes power is instant; re-arming takes **3 ticks per stage**. Turn the ends
around: an input piston that pushes the first block away (rising edge in), a last stage
that pulls a stone off a wire step (rising edge out). V [[R-023-instant-piston-wire]],
G EXP-058.
Both edges in 0 ticks: two chains on one output step, one removing a cut (on), one removing
the source (off), the second re-arming by itself ([[circuits]] `instant_edges`: IN on ≥ 7,
off ≥ 18 ticks).

## Parallel carries on analog lines (R-024)

Ripple carries cost a delay per bit (4 ticks in `full_adder`). Two wire lines, G and K,
with one step onto glass per bit (a one-way diode, R-019), carry all carries at once: bit
j injects 15 into G when it generates, into K when it kills; at bit i the line whose
nearest injection is closer below is stronger, and one subtracting comparator per bit
(rear G, side K) gives C_i. **Every carry of 4 bits settles 2 ticks after the
injections**, whatever its distance. Three wires a bit: 4 bits and CIN fit the 15-block
wire range; the outputs are analog (2..14). V [[R-024-analog-carry-lines]].

## Durations of manual sources

| Source | On for | Evidence |
|---|---|---|
| Stone button | 20 ticks (pressed at T: on at views T … T+19) | V R-001 |
| Oak (wooden) button | 30 ticks | V R-001 |
| Lever | until flipped again | V R-001 |

## Rules of thumb (from the table)

- **Through a component chain, delays add**: lever → torch → torch is 4 ticks; a
  delay-4 repeater adds 8.
- A lamp shows a signal **4 ticks longer** than it lasts. Do not read short pulses off a
  lamp; probe with wire, a repeater, or the component itself (`waves`).
- Even delays everywhere except pistons and observers (2 + 2). A piston starts moving
  in the block-event phase: **in the same tick** when a component powers it during the
  scheduled ticks (repeater, torch, comparator, observer), **one tick later** when a player
  flips a lever or presses a button (between ticks); the pushed block is solid 2 ticks
  after the start. So in a circuit, piston = +0 to start, +2 to finish (V [[R-009-pistons]]).

## Short pulses and short gaps (R-003)

What comes out when the input pulse (or a gap in a long signal) is short. "Lever" pulses
switch between ticks (player actions); "circuit" pulses switch inside a tick's
scheduled-tick phase (made by observers and repeaters).

| Component | 1-tick pulse | 2-tick pulse (lever) | 2-tick pulse (circuit: observer, repeater) | 3+ ticks | Short gap | Evidence |
|---|---|---|---|---|---|---|
| Repeater, delay D = 2·d | out for D | out for max(2, D) | out for max(2, D) | out for max(n, D) | gaps < D filled; ≥ D pass | V [[R-003-short-pulses]], G EXP-009 |
| Comparator | **lost** | passes, 2 | **lost** | passes, n | 1-tick gap filled, ≥ 2 pass | V R-003 |
| Torch | **ignored** | off for 2 | **ignored** | off for n | 1-tick gap filled, ≥ 2 pass | V R-003 |
| Sticky piston | pushes, **leaves the block** | pushes, leaves the block | pushes, leaves the block | pushes and pulls back | — | V R-003, G EXP-016 |
| Lamp | lit 1 + 4 | 2 + 4 | 2 + 4 | n + 4 | (a gap < 4 never shows) | V R-003 |
| Copper bulb | toggles once | once | once | once | each new rising edge toggles | V R-003 |
| Dropper | fires once | once | once | once | — | V R-003 |

Why: repeaters latch any change and re-check only when their tick runs; torches and
comparators re-check their input when their tick runs 2 ticks later, and a circuit-made
2-tick pulse has usually ended earlier in that same phase (the source's tick runs first:
higher priority or scheduled earlier). Details: R-003. **Exceptions** ([[R-012-same-tick-order]]):
an observer's pulse *does* pass a comparator whose front is a repeater or comparator (its
tick then has priority −1, before the observer's 0), and a 2-tick pulse from a torch
whose switch-back was triggered late (by a player) passes torches and comparators.

**Order inside one tick** (V R-012, S [[tick-scheduling]]): scheduled ticks due in the
same tick run by priority — repeater −3 (front is a diode not facing back), −2 (turning
off), −1 (turning on); comparator −1 (front is a diode not facing back) or 0; torch,
observer, lamp, buttons 0 — then in the order they were scheduled. Then block events
(pistons) in the order queued: two pistons pushing into one cell in the same tick, the
one powered first wins and the other does not move. **Several components fed by one
wire change** get their updates in a coordinate-dependent order (Java hash order): the
same build can race differently when moved ([[R-017-wire-order]]); never rely on it.

**Design rules:**

- To make a torch or comparator see an observer pulse, stretch it first (a repeater with
  delay 2+ makes it 4 ticks).
- A sticky piston needs a pulse of **3 ticks or more** to bring its block back.
- A repeater with delay D is also a *pulse extender to D* and a *gap filler below D*.

## Items (R-011)

| Element | Time | Evidence |
|---|---|---|
| Hopper with N items, unlocked | empty after 1 + 8·(N − 1) ticks; its comparator off 2 later | V [[R-011-hoppers]] |
| Item through a hopper chain | 7 ticks per hopper | V R-011, G EXP-038 |
| Dropper → first hopper | 4 ticks after the dropper's rising edge | V R-011 |
| Hopper unlocked | moves on the next tick | V R-011, G EXP-039 |

## Falling blocks (R-016)

A gravity block (sand, gravel, …) falls 2 ticks after losing its support and lands this
many ticks after the support went: 1 block 8, 2 → 11, 3 → 14, 4 → 16, 8 → 22, 16 → 32,
24 → 40. An observer on the landing cell pulses 2 ticks after landing. V
[[R-016-falling-blocks]], G EXP-054.

## Torch burnout (R-007)

A torch burns out on its **8th turn-off within 60 ticks**: switching it off every 8 ticks
or faster burns it out (a period-4 loop after 30 ticks, a period-8 loop after 59), every 9
ticks or slower never. A burnt-out torch relights 160 ticks later if unpowered, unless its
own turn-off unpowered its block at once (then it waits for a neighbor change). V
[[R-007-torch-burnout]], G EXP-005, 006.

## Loops

A loop (ring) of components holds a moving pattern: a comparator ring of n comparators
has a lap of 2·n ticks. A signal must last at least one lap to change the whole ring
(otherwise a "packet" keeps circulating), and every wire in a ring takes 1 strength per
lap. Used by the [[circuits]] Fade timer, Peak-hold register and Clock.

## Not measured yet

Timings of blocks the knowledge base has
not used in circuits yet (composters, campfires, lecterns' page turns by circuits):
[[backlog]].
