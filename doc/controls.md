# Controls

The editor's input design follows the owner's decisions in [[ui-direction]]. Every binding
below is a default and can be changed in the keymap file (see "Rebinding").
Code: `src/redsim/ui/keymap.py` (actions and defaults), `src/redsim/ui/viewport.py` (mouse,
camera, modes), `src/redsim/ui/main_window.py` (menu shortcuts). The **Hotkeys** panel
(F1; right side, next to the Inspector) is generated from the active keymap, so it always
shows the real bindings: grouped by what you are doing (getting around, modes, each mode's
clicks, simulation, view, editing), searchable, with the current mode's section
highlighted. Sections are defined in `keymap.HOTKEY_GROUPS`.

## Window layout

- **Top:** menus, then the tool bar: modes (Normal, Build, Select) and the selection tools
  (rotate, flip, copy, paste, delete, lock).
- **Middle:** the 3D view. On the right, one **Properties** panel with tabs: Inspector,
  Circuit (sections, groups and prefabs), Diagnostics, Hotkeys.
- **Timeline** (like Blender's): transport buttons (start, previous edit, tick back, play
  backwards, run, tick forward, next edit, end), speed and warp, and a ruler counting ticks
  from **tick 0, the build** ([[decisions]] ADR-022), with the recorded range and the blue
  playhead. Click or drag on the ruler to scrub, wheel to zoom, middle-drag to pan.
  - **Keyframes:** edits made after tick 0 are diamonds in four color-coded rows: *Placed*
    (green), *Removed* (red), *Changed* (blue: inspector edits, selection tools), *Used*
    (yellow: levers, buttons, pages, projectiles). One diamond per tick and row; a number
    shows how many edits it holds, hovering lists them. Click to select (Shift/Ctrl+click
    adds), drag a band in empty space to select several, **drag** selected diamonds to move
    them in time, **M** merges the selection into its earliest tick, **Del** deletes it.
    The right-click menu also merges a whole row ("merge all placed edits": everything you
    placed while the simulation ran), moves the selection into the build (tick 0), and
    sets tick 0 at the current tick. Each of these re-runs the history and is one
    undo step; edits that cannot be applied at their new time are dropped (with a note).
  - **Monitor tracks** (logic-analyzer style): Inspector → Monitor adds the selected
    block; its value per tick (wire power, lit/powered, comparator output, …) is drawn in a
    row; hovering a row shows the value at that tick. Right-click a row's label to
    remove it. Monitored blocks are saved; their
    recorded values are rebuilt as the simulation runs.
- **Inventory** (Trackmania's hierarchy, Minecraft's hotbar), shown in BUILD mode only,
  over the bottom of the 3D view like the game's hotbar (nothing resizes). Every folder
  level is a row drawn with the game's own hotbar (9 slots, game-style previews, the number
  key in a small cap, folders marked with an up chevron, the chosen block in the game's
  selection frame, its name in gold above, fading after two seconds like the game's). The
  root row stays lowest; opening a folder slides its row in above, so the stack grows
  upwards (click a slot of a lower row to jump there; the red bar marks the row the number
  keys act on). Number keys (from any mode: they switch to BUILD) open a folder or pick the
  block with that number; **^** (the key left of 1; `` ` `` on US layouts) goes back to
  the parent folder. Folders: Redstone, Movement, Signal sources, Items, Rails, Building,
  Special. **RECENT**, right next to the hotbar, shows the last nine blocks you placed
  (kept between sessions; **Alt+1–9** or a click picks one). **Search** (Ctrl+Space, /, or
  pressing Shift twice like Rider) opens a quick search: type a few letters (fuzzy), Enter
  builds with the block. Signal sources show the strength box.
- **Hint bar** (like Blender's): the essential keys for what you are doing right now (mode,
  selection, gizmo under the cursor, Shift held, pasting), the block under the cursor and
  status messages.

## Modes (vim-like)

| Mode | Key | Left click | Right click | Left drag |
|---|---|---|---|---|
| **NORMAL** | Esc | inspect the block | use it (lever, button, repeater, comparator, …) | — |
| **BUILD** | B | place the block on the build layer | remove the block under the cursor (Ctrl: use it) | a straight line on the build layer |
| **SELECT** | V | select one block (Shift+click: extend the box) | — | draw a box; from a face handle: resize; from inside the box: move it (Ctrl: copy) |

- Middle click picks the block type under the cursor in every mode.
- The badge in the bottom-left corner shows the mode and what it works on; the hint bar below lists the keys.
- Choosing a block (inventory, number keys, middle-click pick) switches to BUILD.
- Esc in NORMAL clears the inspector selection and the selection box.
- In BUILD, **right click** removes the block under the cursor; **Del** only ever clears the
  selection box. **Q** / Shift+Q turn the block under the cursor; blocks facing up or down
  (pistons, observers, hoppers) step through all their facings.
- **Build layer (Trackmania-style):** blocks go on the horizontal layer at the camera
  pivot's height, in the cell under the cursor (a grid around the target cell marks the
  layer and fades out with the distance, yellow lines drop
  to the ground, the badge shows `layer y=…`). **Shift+wheel** moves the layer (and
  the pivot) up or down one block per notch; the **wheel** zooms. Blocks are
  oriented as if placed on top of the block below, facing along the cursor ray.
- **Variants of the block to place** (round 8): in BUILD, the selection's transform keys act
  on the block about to be placed: **R** / Shift+R turn it, **H** mirrors it, **Shift+H**
  turns it upside down (a slab on the top half, a piston or observer facing down, a lever
  on the ceiling). The ghost shows it and the badge names it ("turned 90°, upside down");
  choosing another block starts plain again. With a paste preview, R and H act on the paste.
- **Line placement:** drag with the left button: the line runs on the build layer from the
  first cell along the axis (x or z) you moved most along, up to 64 blocks, with a preview
  of every block. On release all are placed as one edit batch and one undo step; cells that are
  taken or lack support are skipped.
- In BUILD, a translucent preview shows the block exactly as a left click would place it
  (orientation from the cursor ray, wire connections, source setup) inside a white outline;
  the outline turns red where the block cannot be placed. The preview is 1 % smaller than
  a block, so it never z-fights with the block below.
- **Tick 0 is the build:** at tick 0 (a new world, or after jumping to the start) edits
  change the build itself and are not replayed. Edits at later ticks are recorded on the
  timeline; all edits made at one tick appear together when the history replays.
- Placed blocks are oriented like a player looking at the target from the camera along the
  cursor ray (`Viewport.player_view`).

## Selections (SELECT mode, Axiom-style)

- **Draw:** click a block, Shift+click another to extend, or drag across blocks. Dragging
  anywhere inside the box (blocks or air) moves it instead.
- **Gizmos (Blender-like):** each face has a slim resize arrow, colored by axis (X red,
  Y green, Z blue; yellow under the cursor): drag it to move that face. Holding **Shift**
  turns the arrows into white chevrons: drag one outwards to stack copies. A ring around
  the selection carries two arrowheads on the side facing you: click to rotate clockwise
  or counter-clockwise. Two double-headed arrows across the top face flip the selection on
  X or Z. Gizmos are drawn through blocks and win over blocks under the mouse, so a face
  below the ground can be grabbed too. The selection also has a very faint body, so it is
  clear which blocks are inside.
- **Lock (Enter, like GIMP):** a locked selection (orange) cannot be replaced or extended by
  clicks; moving, rotating, flipping and stacking still work. Enter or Esc unlocks.
- **What the other outlines are:** colored single-block outlines are *sections* (Sections
  panel; e.g. blue inputs, green outputs, orange processing), white boxes are *groups*
  (Circuit → Groups). Both are annotations; hide them under View.
- **Move:** drag from a block inside the box. A translucent ghost and a white box show the
  target; the wheel lifts or lowers it while dragging. Releasing runs
  `/clone <box> <target> replace move`: one undoable edit, and pending scheduled ticks move
  along (game-verified, [[experiments/index]] EXP-023).
- **Copy:** Ctrl+drag from inside the box: `/clone … replace force` (the copy may overlap
  the original). The selection follows the moved or copied blocks.
- **Paste (Trackmania-style):** Ctrl+C copies the box; Ctrl+V shows the clipboard as a
  ghost centered under the cursor on the camera's working layer (the pivot's height, shown
  in the badge). Shift+wheel moves the layer up or down (the wheel zooms while pasting), so
  a paste can go into the air or inside blocks; a grid marks the layer and yellow lines drop to the ground. Left click
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
Zooming, wheel layer steps and focusing (F) glide smoothly instead of jumping; the build
and paste layer follow the new height at once.

| Input | Effect |
|---|---|
| Middle drag (or Alt+left drag) | orbit around the pivot |
| Shift+middle drag (or Shift+Alt+left drag) | move the pivot horizontally (the world follows the mouse) |
| Wheel | zoom (distance to the pivot), in every mode |
| Shift+wheel | move the camera (pivot) up or down, one block per notch (in BUILD and while pasting: the layer) |
| W A S D | move the pivot forward, left, back, right (faster when zoomed out) |
| PgUp / PgDown | move the pivot up or down |
| F | move the pivot to the block under the cursor |

Shift and Ctrl are not camera keys on their own, so they never collide with shortcuts (the
reason the old Shift+T rewind was disliked).

## Simulation and editing

| Keys | Action |
|---|---|
| Space or P | run / pause |
| Ctrl+Shift+Space | play backwards / pause (stops at tick 0) |
| Ctrl+0 | **Set tick 0 here** (also a button by the transport controls): the current state becomes the build; later edits move along |
| → or T / ← | step one tick forward / back |
| Ctrl+→ or E / Ctrl+← | step one event (engine step) forward / back |
| Shift+← / Shift+→ | jump to tick 0 / the end of the recorded history (Blender) |
| ↑ / ↓ | jump to the next / previous edit (like Blender's keyframe jumps) |
| Ctrl+Z / Ctrl+Y | undo / redo: the last edit (or line, or keyframe operation) is removed from the history and the simulation re-run; the view returns to where it was made |
| Edit → Undo History | the latest 25 steps, newest first; choosing one undoes it and everything after it in one re-run (redo brings them back one by one) |
| Ctrl+Space, /, Shift Shift | quick block search |
| Ctrl+C / Ctrl+V | copy the selection box / paste preview at the cursor (click places) |
| Q / Shift+Q | rotate the block under the cursor clockwise / counter-clockwise (`/setblock`, undoable) |
| R / Shift+R | rotate the selection (or the paste preview) 90° clockwise / counter-clockwise |
| H / Shift+H | flip the selection left/right / front/back (as seen from the camera) |
| Settings → Keymap… | edit every binding in the program: filter, **Record key** (press the key with its modifiers), reset one or all; conflicts are marked; Save writes only your changes to the keymap file |
| Del | clear the selection box (fill with air); single blocks: right click in BUILD |
| 1–9 / ^ | inventory: open folder or pick block / back to the parent folder |
| Alt+1–9 | pick one of the recently placed blocks (the RECENT strip next to the hotbar) |
| F1 | controls panel |

## View toggles

| Keys | Toggle |
|---|---|
| F3 | **Debug screen** (like Minecraft's): left, the engine and world (rates, game time, phase, engine step and next step, pending scheduled ticks and block events, counts, camera, mode, selection); right, the block under the cursor (id, every property, block entity, comparator reading, the strong and weak power it receives from each side, best neighbor signal, its scheduled ticks, conductor/solid/push reaction). Signal values are labeled on the blocks too: dust power (red), signal-source strength (purple), comparator output (dark); zeros grey. |
| View → Game textures | Blocks drawn with the game's own models and textures (read from the supplied client jar; saved preference). Off, or without the jar: simple colored models. |
| View → Scenery | A grass superflat around the floor (the game's grass texture, fading into the horizon) and the game's clouds; saved preference. Off: the floor alone in the sky. |
| Alt+Z | **X-ray**, cycling like Minecraft's F5: off → building blocks see-through (circuit parts such as dust, torches, diodes, lamps, pistons, redstone blocks and barrels stay opaque) → everything see-through (defaults: building blocks 30 %, circuit blocks 50 % opaque). Both transparency levels are in **Settings → Preferences** (saved in `~/.config/redsim/preferences.json`). |

Active toggles show as a tag above the mode badge. View → Show sections / Show groups
hides the annotation outlines.

## Signal sources

The inventory's **Signal sources** folder (barrel, lectern, cake; hover for how they
differ) places a source at the **Source strength** shown next to the tiles. In the inspector,
a source shows a **Signal source** row: kind buttons swap the block in place, the strength
stepper changes the value (one `/setblock` edit each, applied at once). Lecterns also get *◀ Page* /
*Page ▶*, which turn the page like a player (the comparator value changes and the lectern
sends a 2-tick pulse into the block below). Details: [[mechanics/analog-sources]].

**Target blocks** (inventory: Redstone) show a **Hit strength** stepper (1-15; 15 is a hit
at the face center) and **🏹 Arrow** / **❄ Snowball** buttons in the inspector. The hit
lands during the next tick's entity phase and powers the target for 20 ticks (arrow) or 8
(any other projectile); a hit while it is still powered changes nothing. Details:
[[mechanics/target-block]].

**Containers** (barrels and hoppers; hoppers are in the inventory's **Items** folder) show
a **Contents** row in the inspector: pick a slot, an item and a count and press **Set**, or
**Empty all slots**. Each is one `/setblock` with the block-entity data, so comparators
update and a hopper keeps its transfer cooldown. Details: [[mechanics/hopper]].

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

**Settings → Edit keymap file…** creates `~/.config/redsim/keymap.json` (or
`$XDG_CONFIG_HOME/redsim/keymap.json`; the environment variable `REDSIM_KEYMAP` overrides
the path) with empty `bindings` and every default under `defaults` for reference, and opens
it. Copy the actions you want to change into `bindings`, then **Settings → Reload
keymap**. Only `bindings` is read, so defaults you never touched can change in later
versions. Example:

```json
{"version": 2, "bindings": {"camera.orbit": ["Right Drag"], "sim.run": ["Space"]}}
```

- Files written by older versions listed every default. An entry equal to an earlier
  default (for example `"sim.step_back": ["Shift+Left"]`) is treated as unchanged and
  follows the current default (`keymap.LEGACY_DEFAULTS`).
- A key you bind is taken away from an action that only has it by default (a warning says
  so); two of your own bindings on one key are reported as a conflict.

- Keys use Qt key sequence text (`Ctrl+Z`, `Shift+Right`, `Space`, `PgUp`).
- Mouse bindings are `[Ctrl+|Shift+|Alt+|Meta+]<Left|Right|Middle> <Click|Drag>` or
  `[modifiers+]Wheel`.
- `[]` unbinds an action.
- Mouse actions starting with `normal.`, `build.` or `select.` apply only in that mode and
  take precedence over mode-independent ones (`camera.*`, `pick`).
- Unknown actions, invalid mouse bindings and conflicts (one binding on two actions in the
  same context) are reported in the status bar; the file never breaks the editor (an
  unreadable file falls back to the defaults).

## macOS and trackpads

Every binding works on a Mac as written: Qt reads **Ctrl as ⌘ Command**, Alt as ⌥ Option
and Meta as ⌃ Control, and the hint bar, the Hotkeys panel and tooltips show Apple's
symbols (⇧⌘Z). Nothing was changed for other systems; macOS only gets extra bindings for
what Mac keyboards and trackpads lack or the system already uses:

| Action | Everywhere | Added on macOS | Why |
|---|---|---|---|
| Search blocks | Ctrl+Space, / | ⌘F | ⌘Space opens Spotlight |
| Delete the selection | Del | ⌫ (delete) | the Mac "delete" key is Backspace; fn+delete is Del |
| Pick the block type | middle click | ⌥ + right click (two-finger click) | trackpads have no middle button |
| Info overlay | F3 | ⌘I | F-keys need fn |
| All hotkeys | F1 | ⌘/ | F-keys need fn |

Orbit and pan already have middle-button-free bindings: **⌥ + drag** orbits, **⇧⌥ + drag**
pans. PgUp/PgDown (camera up/down) are fn+↑/fn↓ on a MacBook. Right click is a two-finger
click (or ⌃-click).

**Trackpad gestures:** pinching zooms, rotating two fingers turns the view, a smart-zoom
double tap (two fingers) moves the pivot to the block under the cursor. With **Settings →
Preferences → Trackpad: two-finger scrolling navigates** (on by default on macOS only),
two-finger scrolling works like Blender on a Mac: scroll orbits, **⇧** pans, **⌘** zooms,
**⌥** moves the camera (and the build layer) up and down a block at a time; while dragging
a selection it lifts it. Off, it acts as a mouse wheel. A real mouse wheel is never
affected.

## Related

[[ui-direction]] · [[architecture]] · [[tour]] · [[decisions]] ADR-018
