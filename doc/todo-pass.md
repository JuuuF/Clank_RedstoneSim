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
2. [ ] **O3 several selections:** copy, move, rotate and flip every box at once.
3. [ ] **O2 diagnostics:** a clickable cause chain per block ("why did this change?") from
   the trace; a signal-strength heat view in the viewport.
4. [ ] **O4 sign text:** text drawn on the sign's face; entering text for signs placed in
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
