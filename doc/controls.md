# Controls

The editor's input design follows the owner's decisions in [[ui-direction]]. Every binding
below is a default and can be changed in the keymap file (see "Rebinding").
Code: `src/redsim/ui/keymap.py` (actions and defaults), `src/redsim/ui/viewport.py` (mouse,
camera, modes), `src/redsim/ui/main_window.py` (menu shortcuts). The **Hotkeys** panel
(F1; right side, next to the Inspector) is generated from the active keymap, so it always
shows the real bindings: grouped by what you are doing (getting around, modes, each mode's
clicks, simulation, view, editing), searchable, with the current mode's section
highlighted. Sections are defined in `keymap.HOTKEY_GROUPS`.

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
- In BUILD, a translucent preview shows the block exactly as a right click would place it
  (orientation from the cursor ray, wire connections, source setup) inside a white outline;
  the outline turns red where the block cannot be placed.
- Placed blocks are oriented like a player looking at the target from the camera along the
  cursor ray (`Viewport.player_view`).

## Selections (SELECT mode, Axiom-style)

- **Draw:** click a block, Shift+click another to extend, or drag across blocks.
- **Resize:** each face of the box has a pin handle (a stem with a cube knob, yellow when
  under the cursor). Drag it to move that face along its axis. The selection and its
  handles are drawn through blocks (hidden parts dimmed) and handles always win over
  blocks under the mouse, so a face below the ground can be grabbed too.
- **What the other outlines are:** colored single-block outlines are *sections* (Sections
  panel; e.g. blue inputs, green outputs, orange processing), white boxes are *groups*
  (Contraptions → Groups). Both are annotations; hide them under View.
- **Move:** drag from a block inside the box. A translucent ghost and a white box show the
  target; the wheel lifts or lowers it while dragging. Releasing runs
  `/clone <box> <target> replace move`: one undoable edit, and pending scheduled ticks move
  along (game-verified, [[experiments/index]] EXP-023).
- **Copy:** Ctrl+drag from inside the box: `/clone … replace force` (the copy may overlap
  the original). The selection follows the moved or copied blocks.
- **Paste (Trackmania-style):** Ctrl+C copies the box; Ctrl+V shows the clipboard as a
  ghost centered under the cursor on the camera's working layer (the pivot's height, shown
  in the badge). Ctrl+wheel moves the layer up or down, so a paste can go into the air or
  inside blocks; a grid marks the layer and yellow lines drop to the ground. Left click
  places it, R rotates it, right click or Esc cancels.
- **No block updates:** pasting, moving, copying and stacking are editor operations and
  cause no block updates (`/clone … strict`), so budded components stay budded
  ([[decisions]] ADR-019). Pending scheduled ticks inside a moved selection come along.
- **Rotate:** R turns the selection 90° clockwise (seen from above), Shift+R
  counter-clockwise, in place: blocks inside turn too (repeaters, comparators, wire
  connections, levers, …). R then Shift+R, or R four times, returns exactly to the start.
  While pasting, R and Shift+R turn the paste preview instead.
- **Flip:** H mirrors the selection left/right as seen from the camera, Shift+H front/back
  (facings and wire sides mirror too).
- **Stack:** Shift+drag a face handle outwards: copies appear along that axis (ghosts), one
  more for each selection length dragged; release to place them. The selection then
  covers all copies, so a row can be stacked again into a grid.
- The **Selection toolbar** (top) has rotate, flip, copy, paste and delete buttons.
- Rotate, flip and stack cause no block updates either, and each is one undo step.
- **Delete:** Del fills the box with air (`/fill`); this does update neighbors.

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
| R / Shift+R | rotate the selection (or the paste preview) 90° clockwise / counter-clockwise |
| H / Shift+H | flip the selection left/right / front/back (as seen from the camera) |
| Del | clear the selection box (fill with air) |
| 1–9 | hotbar |
| F1 | controls panel |

## View toggles

| Keys | Toggle |
|---|---|
| F3 | **Info overlay:** signal values on the blocks: dust power (red), signal-source strength as a comparator reads it (purple), comparator output (dark); zeros are grey. Nearest 300 within 48 blocks. |
| Alt+Z | **X-ray** (as in Blender): building blocks become see-through, circuit parts (dust, torches, diodes, lamps, pistons, redstone blocks, barrels, …) stay opaque. |

Active toggles show as a tag above the mode badge. View → Show sections / Show groups
hides the annotation outlines.

## Signal sources

The palette's **Signal sources** section (barrel, lectern, cake; hover for how they
differ) places a source at the **Source strength** chosen below the list. In the inspector,
a source shows a **Signal source** row: kind buttons swap the block in place, the strength
stepper changes the value (one `/setblock` edit each, applied at once). Lecterns also get *◀ Page* /
*Page ▶*, which turn the page like a player (the comparator value changes and the lectern
sends a 2-tick pulse into the block below). Details: [[mechanics/analog-sources]].

## Changing placed blocks

- **Q / Shift+Q** turns the block under the cursor (repeaters, comparators, pistons facing
  sideways, levers, buttons, torches, wire connections). Up/down facings do not turn.
- **Inspector:** left-click a block in NORMAL mode. Every property has a direct control
  that applies at once: facing as arrow buttons (↑N →E ↓S ←W, up/down), booleans as
  toggle buttons, numbers as ◀ value ▶ steppers, other choices as buttons. Signal sources
  get kind buttons (barrel/lectern/cake: swap in place) and a strength stepper. Each click
  is one undo step.
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
