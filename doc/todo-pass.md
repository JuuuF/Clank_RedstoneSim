# Working through the open list (from 2026-10-14)

Owner request (2026-10-14): "go through the TODO list of the project and start
implementing it". The list is [[feedback-status]] ("Still open"). Branch
`feature/todo-pass`; each verified item is fast-forwarded to `main` and pushed.

Whoever picks this up reads this page, continues with the first unchecked item and adds a
line to the log. Items that need the owner (O5, O10, O11) or were deferred on purpose
(O8, ADR-016) are not part of this pass.

## Order

1. [x] **O12 loose ends:** the Select World screen's stray character in the search box,
   its dirt-and-stone look, thumbnails for simulation worlds without one; colored groups
   for every category's timeline lines (not only Powered).
2. [x] **O3 several selections:** copy, move, rotate and flip every box at once.
3. [x] **O2 diagnostics:** a clickable cause chain per block ("why did this change?") from
   the trace; a signal-strength heat view in the viewport.
4. [x] **O4 sign text:** text drawn on the sign's face; entering text for signs placed in
   the editor.
5. [ ] **O1 worlds:** unloading far chunks; re-attaching the stream when a document saved
   from a world is reopened; an on-disk chunk cache; an index of the save's builds with
   "go to"; pending ticks in the written copy.
6. [ ] **O9 schematics:** import/export of Sponge `.schem` and vanilla structure `.nbt`.
7. [ ] **O6/O7 mechanics:** composter (block and source kind), hopper and chest as source
   kinds, daylight sensor; verified in game like the other blocks.

## Log

- 2026-10-14: plan written.
- O12 done: the "stray r" was the text cursor drawn over the placeholder's "T" (the
  placeholder now starts with a space); the Select World screen uses the game's look
  (`ui/game_gui.py`: dirt background and darker list, the `widget/button` and
  `widget/tab` nine-slice sprites, the text-field colors, pixel-font labels; app theme
  without the jar); a world without a thumbnail gets one 1.5 s after it is opened; every
  timeline category has its own colored groups (`Document.lines_of(row)`, saved as
  `extra["row_line_groups"]`; Powered stays in `extra["line_groups"]`).
- O3 done: a new editor action `transform_regions` (engine `_transform_regions`: captures
  every cell of the boxes once, clears them unless copying, places them mirrored within
  the bounding box, turned around its middle and shifted, pending ticks along) moves,
  copies, turns and flips several selections as one undo step; the single-box turn now
  uses the same code. Ctrl+C with several boxes copies one sparse prefab
  (`Prefab.capture_many`). Dragging shows every box's ghost and target. Note: turning a
  non-square group of boxes can land on cells between them (as a single turned box lands
  on its neighbors).
- O2 done: `sim/causes.py` builds a block's chain of causes from the trace (parents within
  a step; scheduled ticks and block events continue at the record that scheduled or
  queued them; neighbor updates from a block changed earlier in the step continue at
  that change). For that, `Level.set_block` now makes its `set_block` record the cause
  of the updates it sends, and sequence power's `note` is the cause of its update (trace
  structure only; engine unchanged, 31.1/13.1 ticks/s as before). Diagnostics has a
  "Why?" sub-tab for the selected block (click: show the block, double click: go to the
  tick). Signal heat view: `editor/heat.py`, View menu / Alt+H, vectorized boxes cached
  per step.
- O4 done: standing and wall signs of all 12 woods are simulated blocks now
  (`world/blocks/sign.py`: survival rules, placement like a player's, `forceSolidOn`,
  `SignBlockEntity` with front/back text that keeps a world's formatting unless edited),
  game-verified (EXP-048: popping, blocking pistons, staying on pushed blocks). Text is
  typed in the inspector (`sign_text` action, one undo step, replayed and saved) and
  drawn on the boards in perspective (`ui/sign_text.py`), not through blocks, only on
  sides facing the camera. Older documents' `extra["signs"]` text moves into the signs;
  hanging signs stay foreign (their text from worlds is still drawn).
