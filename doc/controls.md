# Controls

The editor's input design follows the owner's decisions in [[ui-direction]]. Every binding
below is a default and can be changed in the keymap file (see "Rebinding").
Code: `src/redsim/ui/keymap.py` (actions and defaults), `src/redsim/ui/viewport.py` (mouse,
camera, modes), `src/redsim/ui/main_window.py` (menu shortcuts). The **Help → Controls**
panel is generated from the active keymap, so it always shows the real bindings.

## Modes (vim-like)

| Mode | Key | Left click | Right click | Left drag |
|---|---|---|---|---|
| **NORMAL** | Esc | inspect the block | use it (lever, button, repeater, comparator, …) | — |
| **BUILD** | B | break | place the palette block (Ctrl+right click: use) | — |
| **SELECT** | V | select one block (Shift+click: extend the box) | — | draw a box; from a face handle: resize; from inside the box: move it (Ctrl: copy) |

- Middle click picks the block type under the cursor in every mode.
- The badge in the bottom-left corner shows the mode and what the mouse buttons do.
- Choosing a block (palette, hotbar keys 1–9, middle-click pick) switches to BUILD.
- Esc in NORMAL clears the inspector selection and the selection box.
- In BUILD, a white outline shows where a right click will put the block.
- Placed blocks are oriented like a player looking at the target from the camera along the
  cursor ray (`Viewport.player_view`).

## Selections (SELECT mode, Axiom-style)

- **Draw:** click a block, Shift+click another to extend, or drag across blocks.
- **Resize:** each face of the box has a square handle (yellow when under the cursor). Drag
  it to move that face along its axis.
- **Move:** drag from a block inside the box. A translucent ghost and a white box show the
  target; the wheel lifts or lowers it while dragging. Releasing runs
  `/clone <box> <target> replace move`: one undoable edit, and pending scheduled ticks move
  along (game-verified, [[experiments/index]] EXP-023).
- **Copy:** Ctrl+drag from inside the box: `/clone … replace force` (the copy may overlap
  the original). The selection follows the moved or copied blocks.
- **Paste:** Ctrl+C copies the box; Ctrl+V shows the clipboard as a ghost at the cursor;
  left click places it (`/clone` semantics), R rotates it, right click or Esc cancels.
- **Delete:** Del fills the box with air (`/fill`).

## Camera (orbit around a pivot)

The camera orbits a pivot point, drawn as an orange cross and ring on top of everything.

| Input | Effect |
|---|---|
| Middle drag (or Alt+left drag) | orbit around the pivot |
| Shift+middle drag (or Shift+Alt+left drag) | move the pivot horizontally (the world follows the mouse) |
| Ctrl+wheel | move the pivot up or down, one block per notch |
| Wheel | zoom (distance to the pivot) |
| W A S D | move the pivot forward, left, back, right (faster when zoomed out) |
| PgUp / PgDown | move the pivot up or down |
| F | move the pivot to the block under the cursor |

Shift and Ctrl are not camera keys on their own, so they never collide with shortcuts (the
reason the old Shift+T rewind was disliked).

## Simulation and editing

| Keys | Action |
|---|---|
| Space or P | run / pause |
| → or T | step one tick |
| Shift+→ or E | step one event (engine step) |
| ← / Shift+← | tick back / step back |
| Ctrl+Z / Ctrl+Y | undo / redo (rewinds to just before the last edit) |
| Ctrl+C / Ctrl+V | copy the selection box / paste preview at the cursor (click places) |
| Q / Shift+Q | rotate the block under the cursor clockwise / counter-clockwise (`/setblock`, undoable) |
| R | rotate the clipboard 90° |
| Del | clear the selection box (fill with air) |
| 1–9 | hotbar |
| F1 | controls panel |

## Signal sources

The palette's **Signal sources** section (barrel, lectern, cake; hover for how they
differ) places a source at the **Source strength** chosen below the list. In the inspector,
a source shows a **Signal source** row: pick a kind and strength and press *Set* to change
it or swap the block in place (one `/setblock` edit each). Lecterns also get *◀ Page* /
*Page ▶*, which turn the page like a player (the comparator value changes and the lectern
sends a 2-tick pulse into the block below). Details: [[mechanics/analog-sources]].

## Changing placed blocks

- **Q / Shift+Q** turns the block under the cursor (repeaters, comparators, pistons facing
  sideways, levers, buttons, torches, wire connections). Up/down facings do not turn.
- **Inspector:** left-click a block in NORMAL mode, choose any property (facing, delay,
  mode, …) and press *Apply (/setblock)*. This covers everything Q cannot.
- Both are `/setblock` edits ([[decisions]] ADR-013): the new state is set directly, then
  neighbors update. A wall torch turned away from its wall stays until a neighbor update
  pops it, as in the game.

## Rebinding

**Settings → Edit keymap file…** writes all actions with their defaults to
`~/.config/redsim/keymap.json` (or `$XDG_CONFIG_HOME/redsim/keymap.json`; the environment
variable `REDSIM_KEYMAP` overrides the path) and opens it. Change the lists, delete the
entries you keep, then **Settings → Reload keymap**. Example:

```json
{"version": 1, "bindings": {"camera.orbit": ["Right Drag"], "sim.run": ["Space"]}}
```

- Keys use Qt key sequence text (`Ctrl+Z`, `Shift+Right`, `Space`, `PgUp`).
- Mouse bindings are `[Ctrl+|Shift+|Alt+|Meta+]<Left|Right|Middle> <Click|Drag>` or
  `[modifiers+]Wheel`.
- `[]` unbinds an action.
- Mouse actions starting with `normal.`, `build.` or `select.` apply only in that mode and
  take precedence over mode-independent ones (`camera.*`, `pick`).
- Unknown actions, invalid mouse bindings and conflicts (one binding on two actions in the
  same context) are reported in the status bar; the file never breaks the editor (an
  unreadable file falls back to the defaults).

## Related

[[ui-direction]] · [[architecture]] · [[tour]] · [[decisions]] ADR-018
