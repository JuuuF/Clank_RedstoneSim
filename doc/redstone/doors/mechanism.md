# Mechanism and controller: a door's contract

The 5x5 guide's process puts the **piston layout** first and the **wiring** last
([[guide-5x5]] 1.1). The door lab can test that split on real doors
(`python -m tools.doorlab.mechanism WORLD …`, 2026-10-18):

1. From the replay, the **mechanism** is every piston that moves door blocks or other
   pistons (roles "door" and "stack", [[representation]]) plus the door blocks and the
   plain blocks around them; the **controller** is everything else: wire, repeaters,
   comparators, observers, torches, the lever, droppers and hoppers used as timers, and
   the pistons that only move controller parts (power switches, sliders, helpers).
2. The **contract** is read from the mechanism pistons' block events: an extension at
   tick e and the piston's next retract at tick r is a pulse "on between e−1 and e, for
   r−e ticks" (`pulse POS at e−1 for r−e`, the timing R-026 measured: the piston starts
   at e and retracts at r; a 1-tick pulse on a pushing sticky piston is a spit). A piston
   that is extended and powered in the build and first retracts at r gets a pulse from
   tick 1 for r−2 ticks (it stays out until the pulse ends).
3. The controller is removed and the contract put on the timeline as editor pulses. If
   the stripped door moves its doorway exactly like the original, the contract is
   complete: **any controller that gives these pulses runs this mechanism.**

## Results

| World | Mechanism pistons | Pulses | Same-tick "retract, then extend" | Stripped door |
|---|---|---|---|---|
| `3x3-piston-door-mumbo-jumbo` | 11 | 14 | none | **identical** |
| `4x4-piston-door-sydney600mc` | 24 | 48 | none | **identical** |
| `4x4-piston-door-kwipla` | 24 | 54 | ticks 20, 50, 56 | **identical** |
| `3x3-spiral-vault-door-lutal` | 19 | 38 | 8 ticks | **identical** |
| `3x3-piston-door-zhus`, `…-monchicarp` | 11 | 19 | 12, 29 | differs from 29 |
| `3x3-piston-door-rubik` | 11 | 22 | 7, 32 | differs from 9 |
| `3x3-piston-door-sacredredstone` | 11 | 37 | 5 ticks | differs from 13 |
| `3x3-spiral-piston-door-purplers` | 11 | 24 | 13 ticks | differs from 10 |
| `3x4-piston-door-pal1` | 16 | 32 | 7 ticks | differs from 10 |
| `3x3-flush-enchanting-table-door-purplers` | 27 | 98 | 6 ticks | **identical** (since the carried blocks stay, below; was: differs from 3) |
| `5x5-vault-door-nile` | 29 | 48 | 22, 24, 29 | differs from 8 |
| `3x3-seamless-glass-door-nile` | 33 | 61 | none | differs from 40 (was 10) |
| `5x5-vault-lamp-door-purplers` | 46 | 52 | none | differs from 23 |
| `4x4-sliding-piston-door-purplers` | 12 | 12 | none | differs from 5 |
| `1-wide-hidden-staircase-purplers` | 13 | 18 | none | **identical** (was: differs from 13) |
| `5x5-glass-piston-door-ashevoy` | 131 | 252 | 11 ticks | differs from 68 (was 16) |
| `7x7-piston-door-legden`, `8x8-…` | 129, 152 | 390, 348 | 36, 24 ticks | differ from 2 (the builds stop, EXP-068) |

### Mumbo Jumbo's contract

The whole controller of [[analyses/3x3-piston-door-mumbo-jumbo]] (31 blocks: wire,
repeaters, torches, comparator, dropper, hopper, the power-switch and helper pistons)
reduces to these 14 pulses; the stripped door (11 pistons, 9 door blocks) moves its
doorway tick for tick like the original:

| Start (piston extends) | Piston | Pulse | Effect |
|---|---|---|---|
| 2 | P1 (5 3 −2, up) | 1 | spit the center block C up one |
| 5 | the 6 side singles, the top (5 9 −2) and the floor slider (5 4 0) | 12 | close the edges; slide B under C |
| 9 | P1 | 5 | push B and C up (closed at 11); at 14 pull B down |
| 21 | P2 (5 2 −2, up) | 7 | lift P1 one cell; at 28 lower it |
| 24 | P1 raised (5 4 −2) | 1 | extend under C, pull C down one at 25 |
| 31 | P1 | 6 | extend, pull C into the floor at 37 |
| 31 | P2 | to the end | its push fails on the extended P1 (harmless) |

The lever is pulled at 1 and 13; everything else is the controller's timing. This table
is the specification a redesigned controller has to meet.

## Why a contract can need more than pulse times

In 11 doors the original orders, **inside one tick**, a retract of one mechanism piston
**before** an extension of another (column 4). Editor pulses cannot do that, nor can any
input between ticks: a pulse that starts acts at the end of the tick before (its piston
queues its event then), a pulse that ends acts at the start of the tick, so in one tick
every start is queued before every end ([[../timing]], order inside a tick). Only parts
that switch in the scheduled-tick phase (repeaters, observers, torches, comparators) can
put a retract first. Zhus's door needs it at tick 29: piston 2 3 −6 must pull its block
out of the center column before piston 2 2 −4 extends into the column; given the other
order, 2 2 −4 pushes the block up instead and the doorway runs differently from then on. So **a door's
contract is a pulse schedule plus a same-tick order**, and part of a controller's
design is choosing components whose tick phase gives that order.

**D4, first half (2026-10-19): the mechanism carries blocks.** `strip` now keeps every
block a mechanism piston moves, whatever its role (`mechanism.carried`: the tokens moved
by door and stack pistons, from the replay). That made the staircase and the
enchanting-table door identical (their "door" pistons carry pistons and power parts) and
moved the seamless door's divergence from tick 10 to tick 40, ashevoy's from 16 to 68. The table above is the
re-run; the rows that did not change still differ for the reasons below.

Some doors with such ticks still come out identical (Kwipla, Lutal): there the two
pistons do not interact. The doors that differ without one fail for reasons of the
simple split: in the sliding 4x4 and Nile's vault 5x5 the redstone blocks that ride in the
slime assemblies are kept now, and the doors still differ from ticks 5 and 8: their
first strokes depend on the order of extensions inside a tick (Purplers' sliding door
pushes two front skins with plain pistons earlier in the same tick's queue so that the
cores count 11 blocks, [[analyses/4x4-sliding-piston-door-purplers]]), which editor
pulses, queued in position order, do not reproduce: the contract needs an
extend-before-extend order too; an editor pulse on a piston also
quasi-powers a piston directly below it (it powers the position the lower piston's
quasi-connectivity asks from), which stacked mechanisms like Rubik's notice; the
staircase's "door" pistons depend on pistons the split calls helpers. Backlog D4 has the
refinements (move slime-carried parts to the mechanism, drive stacked pistons from the
side).
