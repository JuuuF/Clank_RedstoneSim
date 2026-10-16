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
| Piston, sticky piston (extend) | `extended=true` Δ 1; front cell `moving_piston` Δ 1; pushed block solid at its new place Δ 3 | — | the block event runs in the next tick, then the move takes 2 ticks | V R-001, G EXP-015 |
| Piston (retract) | — | base `moving_piston` Δ 1, head gone Δ 1, `extended=false` Δ 3 | | V R-001, G EXP-015 |
| Sticky piston (retract) | — | pulled block back in place Δ 3 (`moving_piston` at Δ 1, 2) | | V R-001, G EXP-015 |
| Dropper (and dispenser) | `triggered` Δ 0; the item leaves Δ 4 | `triggered=false` Δ 0 | a rising edge only; empty → nothing happens | V R-001, G EXP-044 |
| Note block | `powered` Δ 0 (plays) | Δ 0 | | V R-001, G EXP-042 |
| Copper bulb | toggles `lit` Δ 0 on a rising edge | `powered=false` Δ 0, `lit` kept | a T flip-flop | V R-001, G EXP-043 |
| Iron trapdoor (doors, gates) | open Δ 0 | closed Δ 0 | | V R-001, G EXP-052 |
| Powered rail | Δ 0 | Δ 0 | | V R-001, G EXP-036 |
| Hopper | `enabled=false` (locked) Δ 0 | unlocked Δ 0 | | V R-001, G EXP-039 |

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
- Even delays everywhere except pistons (1 to start moving, 3 to finish) and observers
  (2 + 2). Odd timings come from pistons, from player actions (between ticks) and from
  0-tick tricks.

## To be measured

Short pulses (how each component treats a pulse shorter than its delay), inputs through
blocks and wire, and update-order races inside a tick are open: [[backlog]].
