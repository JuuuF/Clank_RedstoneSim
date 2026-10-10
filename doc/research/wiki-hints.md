# Wiki hints

The owner supplied stripped Minecraft Wiki pages in `data/wiki/` (2026-10-10). They are
**hints only** ([[decisions]] ADR-011). Each claim used here is checked against the 26.3
source or the real game before the simulator relies on it.

| Page (file) | Useful for |
|---|---|
| Redstone components (`Redstone components – Minecraft Wiki.html`) | Per-component overview: torch, repeater, comparator, dust, piston, observer and more |
| Tutorial: Quasi-connectivity | Immediate vs. update-based QC activation, BUD uses, workaround examples |
| Tutorial: Instant repeaters | BUD-powered sticky-piston "instant repeater" (bug MC-8328), 0-tick piston use |
| Tutorial: Redstone | General introduction (low technical value) |

Text extraction for reading (scratch only, not committed): parse the HTML with Python's
`html.parser` in isolated mode (`python3 -I`).

## Claims checked so far

| Wiki claim | Verdict | Evidence |
|---|---|---|
| A torch powers the block above it and not the block it is attached to | confirmed | `RedstoneTorchBlock.getDirectSignal`/`getSignal`; unit test `test_torch_strongly_powers_block_above_but_not_its_support` |
| Torch delay 2 game ticks | confirmed | `RedstoneTorchBlock.neighborChanged` (`scheduleTick(…, 2)`); EXP-002 |
| Burnout example: dust on a block with a torch on its side, block above the torch | confirmed (the loop burns out) | EXP-005 |
| "After burning out, a torch re-lights when it receives a redstone update, or randomly after a short time" | **partly wrong for 26.3**: there is no randomness, only a 160-tick scheduled check, and in the example loop that check is dropped, so the torch stays out until an update | `RedstoneTorchBlock.tick`, `LevelChunkTicks.schedule`; EXP-005, EXP-006 |
| QC: components that update two blocks away (comparator, dust, repeater, torch) activate a QC piston immediately; others only on the next update | consistent with source (update ranges of each component); to be tested with pistons | `getNeighborSignal`; update patterns in [[mechanics/redstone-wire]], [[mechanics/repeater]], [[mechanics/redstone-torch]] |
| "A piston that has a conductive block two spaces above itself receiving a signal from a repeater does not extend immediately" | consistent with source; planned game scenario | [[mechanics/pistons]] |
| Sticky piston with a pulse shorter than 1.5 ticks leaves the block behind | consistent with event-2 logic; planned game scenario | `PistonBaseBlock.checkIfExtend`/`triggerEvent` |

## Test ideas taken from the pages

- QC: immediate activation by dust/torch/repeater/comparator next to the space above a
  piston; update-based activation by a lever two blocks away (M5).
- Instant repeater (BUD-powered sticky pistons) as an advanced M5 regression scenario.
- Upward-only signal on glass/glowstone, which the source predicted and EXP-007 confirmed.
