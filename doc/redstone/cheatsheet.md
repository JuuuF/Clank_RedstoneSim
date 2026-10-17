# Redstone cheat sheet

The rules a designer needs most often, one line each, with the record that proves them.
All times in **game ticks** (20 per second). Details: [[timing]], [[signals]],
[[components]], [[circuits]]. Evidence: [[redstone/README#Experiment records]].

## Delays

| Thing | Delay |
|---|---|
| wire, lamp on, note block, copper bulb, doors, rails, hopper lock | 0 |
| lamp off | 4 ([[R-001-response-times]]) |
| torch, comparator | 2 |
| repeater | 2 per delay step (2, 4, 6, 8) |
| observer | pulse 2 ticks long, starting 2 after the change |
| piston | starts at once if powered by a component, +1 if by a player; block solid 2 after it starts ([[R-009-pistons]]) |
| dropper/dispenser | fires 4 after the rising edge |
| buttons | stone 20 on, oak 30 on |
| hopper | 1 item / 8 ticks; 7 ticks per hop through a chain ([[R-011-hoppers]]) |
| falling sand | 2 + fall time: 1 block 8 total, 4 blocks 16, 16 blocks 32 ([[R-016-falling-blocks]]) |

## Power

- Strong power (lever/button on the block, torch under it, repeater/comparator/observer
  into it) also reaches **wire** beside the block; weak power (from wire) does not
  ([[R-002-what-powers-a-block]]).
- A lever on the floor *beside* a block does not power it; power never chains block to
  block; a redstone block powers no block.
- Wire powers only what its shape points into, and the block under it; a lone placed
  wire is a cross ([[R-004-wire-geometry]]).
- Wire loses 1 per block; repeaters give 15; comparators keep strength
  ([[R-005-signal-strength]]).
- Power steps down only from wire on conductors; glass, slabs, hoppers, observers pass
  it up only ([[R-019-wire-supports-and-dropper-qc]]).

## Pulses

- Repeaters stretch pulses and fill gaps shorter than their delay.
- Torches and comparators lose 1-tick pulses **and the 2-tick pulses of observers and
  repeaters**: stretch to 3+ ticks first ([[R-003-short-pulses]], exceptions
  [[R-012-same-tick-order]]).
- Sticky pistons need 3+ ticks of power to pull their block back; shorter pulses leave
  it ("spit"), in place at once when the power goes ([[R-018-piston-zero-tick]]).
- A 0-tick pulse lights no comparator; repeaters, lamps, bulbs and droppers react
  ([[R-013-zero-tick]]). It moves no piston when a player makes it; made by pistons
  inside a tick, it moves pistons updated before it ends (order W, E, down, up, N, S):
  a sticky one moves its block in 0 ticks ([[R-018-piston-zero-tick]]).
- Copper bulbs and droppers react once per pulse, any length.
- **Instant wire:** extended sticky pistons, each holding a redstone block against the
  next one's back, all retract in one tick: power removal crosses any distance in 0 ticks
  (3 blocks a stage, 17 with wire between); re-arming is 3 ticks a stage
  ([[R-023-instant-piston-wire]]).

## Components

- A torch burns out on its 8th turn-off within 60 ticks (period ≤ 8); use the comparator
  clock instead ([[R-007-torch-burnout]]).
- Only repeaters and comparators lock a repeater; a locked repeater drops waiting
  changes ([[R-006-repeater-locking]]).
- Observers see block **state** changes only (not comparator strength, not container
  contents); a pushed observer pulses after landing ([[R-008-observers]],
  [[R-015-moving-observers]]).
- Pistons: 12 blocks max; block entities and obsidian stop them; slime grabs the floor;
  quasi-connectivity needs an update.
- Comparator side inputs: wire, redstone blocks, diodes pointing in; not torches, levers,
  powered blocks.

## Design

- Balance path delays into a gate whose inputs may change together; otherwise 2-tick
  glitches ([[R-010-hazards]]).
- Never rely on which component one wire change reaches first: it depends on where the
  build stands ([[R-017-wire-order]]).
- Rings: changing a loop's contents takes a full lap (2 ticks per comparator).
- Keep wires one block away from other circuits' strongly powered blocks; tap signals
  through repeaters before they join a shared wire ([[circuits]] composition rules).
- `place` is a player: a copper bulb placed next to power lights; pasted modules keep
  their states and need no updates; settle after building ([[cli]] pitfalls).
- Paste library modules in any rotation ([[R-022-rotated-modules]]).
- Many signals to many lines: a **crossbar** (signals on the floor, lines on the top layer,
  a tap = repeater, stone, wire on the stone stepping up into the line); bring a module's
  outputs out to rows by **nested corners** (the outermost turns first) ([[circuits]]
  4x1 RAM, Lookup table).
- A paste includes its air: paste the module whose cells must win last.

## Which module

See the "Which module for what" table at the top of [[circuits]]; the full method for a
new requirement is [[workflow]].
