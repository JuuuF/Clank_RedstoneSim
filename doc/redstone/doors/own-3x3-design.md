# An own 3x3 door without slime: design study (2026-10-20, 02:35–02:52)

The owner asked for an own 3x3 piston door, clean, small and fast, no exposed redstone,
no slime, in a 20-minute window after the mission ([[mission]] §13). A validated build
did not fit the window; this page keeps the design reasoning so the next agent starts
from it instead of from zero. The project's existing door is `door_3x3`
([[demonstration]], 10 pistons, 32 ticks to open, a lockout).

## The goal in numbers

The dataset's compact 3x3s ([[metrics]]): Zhus 11 pistons, 51 blocks, 14 ticks; Mumbo
Jumbo 12 pistons, 87 blocks, open 10. An own door should beat 10 pistons and stay under
~60 blocks with no redstone visible from the doorway side.

## Edge columns: 6 sticky pistons, two deep in the wall

Row y = 1..3, piston at x = ±3 facing the doorway, its block at x = ±2 when open
(the wall face), head at x = ±2 and block at x = ±1 when closed. Powered = closed, so a
lever on the back of the wall powers all six through conductors; no timing needed.

## The center column is the whole problem (as in every slimeless door)

- Top cell (y = 3): one sticky piston at (0, 5) facing down; block at y = 4 when open.
- Bottom cell (y = 1): one sticky piston at (0, −1) facing up; its block is the floor
  (y = 0) when open and the head is the floor when closed. Both faces are walkable.
- Middle cell (y = 2): no single piston reaches it from any side (one cell of travel
  from a wall that must stay solid). The corpus answers this with floor storage: the
  middle block goes down and the bottom block moves aside in the floor
  ([[patterns]] "Floor storage", `door_3x3`'s M east, Mumbo Jumbo's), 4–5 pistons.

### Idea tried: a gravity block as the middle cell (simulator-checked, see below)

Make the middle cell sand pushed up from the floor by a vertical double extender
(A sticky at y = −3, B sticky at y = −2, block at y = −1, sand at y = 0 when open;
closed: head y = 0, block y = 1, sand y = 2). The top cell comes from above as before.
That is 9 pistons and the sand needs no piston of its own: on opening it falls back
into the floor hole.

Why it fails: the double extender's retraction. B pulls the block from y = 1 to y = 0,
then A pulls B from y = −1 to y = −2, and the block stays at y = 0 (a pulled piston
does not carry its held block). The sand lands at y = 1, in the doorway, and no later
pulse of B helps: B extending pushes the block and the sand up again, retracting pulls
only the block. A sand-from-above variant fails the other way: the sand has no resting
place out of the doorway when open (y = 4 is only solid when the top block is there).
Two sands accumulate by one cell per cycle. The simulator does simulate falling blocks
(`sim/entities.py`), so the variant with a lateral exit for the stranded block could
still be tested: pull the block at y = 0 sideways into the floor with a seventh floor
piston, and the sand falls to y = 0 on its own. That is the same count as floor
storage (the corpus's choice) and buys nothing.

### The check (`experiments/doors/own3x3/extender.cli.txt`, 02:39)

The column alone, levers on A (tick 2 on, 40 off) and B (8 on, 30 off); cells named by
y, the floor is y 5, the doorway's bottom and middle cells y 6 and y 7:

| Tick | y 5 (floor) | y 6 (bottom) | y 7 (middle) | Event |
|---|---|---|---|---|
| 5 | stone | sand | air | A extended: B, stone and sand up one |
| 11 | B's head | stone | sand | B extended: **closed** |
| 33 | stone | air | air | B retracted: stone pulled down, sand still at y 7 for a moment |
| 39 | stone | **sand** | air | the sand fell (6 ticks after the stone landed) |
| 43 | stone | sand | air | A retracted: B back, the stone stays on the floor |

Open state: the sand sits in the bottom cell. The idea is dead unless a seventh floor
piston takes the stone aside before the sand falls, which is floor storage again.

## What to build next (the recommendation)

Floor storage, done in the corpus's smallest form:

1. Edge columns as above (6 pistons).
2. Top cell from above (1 piston).
3. Middle and bottom cells: the middle block is pushed down by the top piston when the
   bottom block has been moved aside in the floor by a sticky piston lying in the floor
   (1 piston), and a sticky piston below the doorway (1 piston) catches / returns the
   stack. Expected total 9–10 pistons; the open sequence is the known contract of
   `door_3x3` rows "B", "W", "A" ([[demonstration]] "The contract"), which that page
   says can be driven 26 ticks faster by a smaller controller.
4. Controller: one lever, a repeater chain for the three ordered events, all behind the
   wall (no exposed redstone). Keep `door_3x3`'s lockout principle only if the safe gap
   measured by `python -m tools.doorlab.inputs --explain` is longer than a player's
   double flip.
5. Validate with the lab: `annotate.py`-style sections and markers, then
   `mechanism`, `inputs --explain`, `ablation`, and a game run (`run_world`, EXP-0xx).
