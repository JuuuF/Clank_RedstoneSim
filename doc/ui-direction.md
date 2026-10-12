# UI and product direction (owner feedback)

Feedback from the first hands-on session (2026-10-11), recorded as design input.
Implementation status is tracked in [[roadmap]] and [[project-state]].

## Interaction

- **Modes, vim-like.** Separate a *build* mode (placing/breaking blocks only there) from a
  mode for selections and settings. Today's single mode with click overloading
  (left = break, right = place or use) is not liked.
- **Shortcuts must not collide with camera keys.** Shift+T (tick back) also moved the camera
  down, because Shift is "down". Camera keys and command keys need separate namespaces.
- **Selections like Axiom** (the Minecraft building mod): box selections, moving and copying
  selections in place, with visible handles.

## Camera

- Replace the fly camera with an **orbit ("trackball") camera around a visible pivot**, a mix
  of Blender and Trackmania's editor:
  - the pivot point is highlighted;
  - mouse wheel moves the pivot up and down;
  - dragging the mouse moves it horizontally;
  - Ctrl+wheel zooms in and out, as does middle-click dragging.
- Resolved by the decisions below (middle-drag orbits).

## Decisions (owner, 2026-10-11)

| Topic | Decision |
|---|---|
| Camera | Blender-style orbit around a visible pivot: **middle-drag orbits**, **Shift+middle-drag pans** the pivot horizontally, **Ctrl+wheel moves the pivot up/down**, plain wheel zooms. All bindings live in a **user-editable keymap** (rebindable later). |
| Modes | **NORMAL** (Esc): inspect, use levers, run/step. **BUILD** (B): place/break only here. **SELECT** (V): Axiom-like boxes, move/copy/paste, groups. Mode badge in the viewport. |
| Build clicks | Minecraft-style: **left breaks, right places**, middle picks the block type. |
| Selection | Left-drag draws box selections in SELECT mode. |
| Signal sources | Hot-swappable source block backed by real blocks: **container (barrel/chest)** and **lectern** first; cake stays available. |

**Status (2026-10-11):** camera, modes, build clicks and the rebindable keymap are
implemented ([[controls]], ADR-018), as are Axiom-like selections: face handles to resize,
drag to move, Ctrl+drag to copy, paste preview (ADR-019), and the hot-swappable signal
source backed by barrel, lectern or cake (ADR-020). Open: rotate/flip in place,
stack/repeat.

## Second round of feedback (2026-10-11, after trying selections and sources)

| Topic | Request |
|---|---|
| Hotkeys | A panel giving a good overview of what can be done and how to navigate. |
| Selection handles | Face dragging works well, but the handle looked like a block outline (same size and shape). Make it a distinct handle. |
| Selection outline | Thicker, clearly different from the section/group outlines around components (which were unexplained). Visible through blocks. |
| Bottom face | Selections starting at the ground: the lower face could not be grabbed again. |
| Paste | Follow the camera height, not the surface under the cursor, like the Trackmania map editor, so selections can go into the air or inside blocks. |
| Cloning | Editor cloning must not cause block updates (budded components must stay budded): it is an editor operation, not a game action. |
| Build preview | Show the block about to be placed as a translucent preview. |
| Info overlay | Hotkey-toggled debug view showing signal strengths on blocks (sources read by comparators, dust power), like Blender's overlay toggles. |
| X-ray | A Blender-like X-ray toggle. |
| Inspector | Apply edits immediately (no Set/Apply button); facing as arrow buttons; booleans as toggle buttons. |
| Selection tools | Rotate and flip are essential (blocks inside must turn too); stack/repeat wanted. |

**Status (2026-10-11):** all of the above is implemented and on `main` ([[controls]]):
hotkeys panel (F1), pin handles and thick see-through selection (bottom face grabbable),
Trackmania-style paste on the camera's working layer, strict update-free cloning
(game-verified EXP-026), build preview, info overlay (F3), X-ray (Alt+Z), immediate-apply
inspector with arrows/toggles/steppers, rotate/flip/stack in place (ADR-021).

## Third round of feedback (2026-10-11)

| Topic | Request |
|---|---|
| Layout | Views feel scattered and unordered; hard to find things. |
| Inventory | Like Trackmania: hierarchical groups in a bar at the bottom of the screen, navigated with number keys. |
| Selection body | Keep the edge thickness; add a very low-alpha body so it is clear which blocks are inside. |
| Gizmos | Handles too big and clunky. Blender-like gizmos and arrows for resizing, rotating and flipping are welcome (may break from Minecraft looks). |
| Paste height | Plain mouse wheel moves the paste layer vertically (no Ctrl). |
| Timeline | Like Blender: Left/Right step time, Shift+Left jumps to the start; Blender-like timeline mechanics, possibly with a timeline monitor. |
| X-ray | Three-way toggle (like Minecraft's F5): off, building blocks see-through, everything see-through (circuit blocks too). Both alphas adjustable in the options. |
| Lock selection | Enter locks a selection (like GIMP) to rotate, flip etc. in place. |
| Hints | Blender-like context hints for the essential actions at the bottom. |
| Stack feedback | Handles change their look while Shift is held, so stacking is discoverable. |
| Bug | Ctrl+drag copy of a selection did nothing on release. |
| Delete | Keep neighbor updates on delete. |
| Debug screen | F3: a Minecraft-like debug screen with block states and more. |
| Style | Simple but slick; looks good, still feels like Minecraft, not disconnected from the game. |
| Verification | Build bigger circuits and stress-test against the game, including 0-ticking and block-event manipulation. |
| Next mechanics | Observers, rails, target blocks, then hoppers. |

Status: all of the third round is implemented (see [[controls]], [[project-state]]).

## Fourth round of feedback (2026-10-11, after using the third-round build)

| Topic | Request |
|---|---|
| Drag placement | Drag to place a line of blocks (wire especially); straight lines are enough for now. |
| Preview flicker | The translucent build preview z-fights with the block below it (its back faces); raising or minimally shrinking the preview is fine. |
| Inventory | Keep the hierarchy, but add recent/favourite blocks on top, show the folder path up to the current level, and show a preview of each block, not just a name and a color. |
| Quick search | A quick block search in BUILD mode, like Blender's quick favourites, Rider's double Shift or macOS Cmd+Space. |
| Build clicks | Change again: **left click places, right click rotates, DEL removes**. |
| Timeline start | Why does the simulation start at tick 4, not 0? Fix it unless there is a reason. |
| Shift+Left | Jump-to-start did not work because Shift+Left was bound twice. |
| Atomic placements | Block placements in one time step form one event: all blocks appear at once, not one after another. |
| Replay error | Replaying placements often fails with "player actions happen between ticks; finish the tick first", which blocks the timeline. |
| Quick placing | Fast consecutive placements sometimes get lost (something seems to block new actions). |
| Keyframes | Move and merge keyframes; color-coded rows (placements, block actions, …); merging should combine all placements made while the simulation ran. |
| Tick 0 | A build state at tick 0 that is not replayed: build something, then simulate from there. Replaying the whole build history wastes time. |
| Step back | Stepping backwards is much slower than forwards. |
| Observer | The model should show clearly which way it faces. |

Status: all of the fourth round is implemented ([[controls]], [[decisions]] ADR-022). Notes:
the replay error was a real bug (a failed edit consumed a step); "starts at tick 4" was the
example file being saved at game time 4 (ticks now count from the build); Shift+Left failed
because the keymap file written earlier kept the old default Shift+Left = step back (old
defaults in keymap files now follow the new ones). Stepping back was fast in measurements
(the build is no longer replayed, keyframes are denser); backward playback was added.

## Fifth round of feedback (2026-10-11)

| Topic | Request |
|---|---|
| Build height | Do not place against any surface: place on the layer at the camera pivot's height; the wheel moves it up and down. |
| Inventory | Show the whole hierarchy up to the current level, like Trackmania (stacked rows). |
| Rails | Curved rails looked wrong. |
| Observer | Return the face side to the plain model (keep the rest). |
| Tick 0 | "Set tick 0 here": after moving placements into tick 0, run a few ticks (e.g. a new redstone block updates its circuit) and make that the start. |

Status: implemented. BUILD places on the working layer with a grid and drop lines (wheel:
layer, Ctrl+wheel: zoom); the inventory shows one compact row per level above the current
one; curved rails are two concentric arcs; the observer face is plain again (arrows kept);
"Set tick 0 here" is a button next to the transport controls (Ctrl+0, also in the
Simulation menu and the timeline menu) and keeps later edits, shifted.

## Sixth round of feedback (2026-10-11)

| Topic | Request |
|---|---|
| Smoothness | The system should feel smoother. |
| Coherence | Everything should look like it belongs together, not like views thrown together. |
| Style | Minecraft vibe with Blender's UI in mind (futuristic, professional); dark theme. |
| Models | Is it feasible to use the game's models and textures? Real textures would feel way better. |
| Inventory | The hierarchy stack should grow upwards; a fitting, sleek design. |
| Tick 0 | After "Set tick 0 here" the status still showed the old "game time X → Y": update the internal timers too. |

Status: implemented ([[decisions]] ADR-023, ADR-024). "Set tick 0 here" now restarts the
clock (every stored game time shifts, tested to change nothing in the simulation); blocks
use the game's models and textures read from the supplied jar; dark theme, the game's
pixel font for overlays and the F3 screen, a hotbar-style inventory with the folder stack
growing upwards, a smooth camera.

## Seventh round of feedback (2026-10-12)

| Topic | Request |
|---|---|
| Wheel | Scrolling should move the camera up and down, not zoom. |
| Inventory | Folder rows should not change their look when diving into a lower level. |
| Names | Block names were lowercase. |
| Keymap | "Keymap: unknown action 'hotbar.1' (ignored)" for each hotbar slot at start. |
| Preferences | Fixed width: the sliders were squeezed until the window was widened. |
| X-ray | Defaults 30 % for building blocks, 50 % for circuit blocks. |
| Flat models | Dust (and other flat models) one game pixel high by default. |
| 7×7 outlines | In BUILD, the blocks around the target were outlined at the layer's floor: feature or bug? |

Status: implemented. The wheel moves the camera (pivot) up or down in every mode and
Ctrl+wheel zooms (old keymap files keep working: unchanged old defaults follow the new
ones); every inventory level is the same row of hotbar slots, the root lowest; block names
are the game's own English names from the jar's `en_us.json` ("Redstone Dust", "Block of
Redstone"); the retired `hotbar.N` actions of older keymap files are ignored silently; the
Preferences dialog is 480 px wide; flat model elements (dust, rails) are extruded to one
pixel with side faces cut from the top texture's edge. The outlines were a **feature**: the
Trackmania-style layer grid (round 5) drawn around the target cell at the layer's height,
which on flat ground coincides with the edges of the blocks below. It now fades out with
the distance to the target, so it reads as a height guide.

## UI polish pass (2026-10-12, owner: "keep iterating on the UI until 6 AM")

Not a feedback round; changes made while reviewing screenshots of every view
([[decisions]] ADR-025):

- Pixel-art icons for the toolbar (modes, rotate, flip, copy, paste, delete, lock), the
  transport buttons, menus, Monitor, the target projectiles and the search button; mouse
  gestures in keycaps are pixel mice.
- Timeline: a darker ruler band with centered tick labels and a rounded playhead badge;
  the current tick in gold in the ruler's label column; monitor tracks as seamless step
  waveforms with the block's icon, name and dim position.
- Inventory: 9-slot hotbar rows (empty slots complete short folders), folders as stacked
  slots with an up chevron, number keys as small key caps.
- Viewport: the mode badge shows what the mode works on (block and layer, selection
  size, inspected block) instead of repeating the hint bar; an empty world shows how to
  start; the build layer grid fades out.
- Panels: no dock title bar; Circuit has one tab level (Sections, Groups, Prefabs);
  inspector header with name and coordinates, capitalized property labels; Diagnostics
  with game names, fitting columns and empty-state rows; section color swatches;
  Preferences grouped with a reset button; block search shows the folder dim on the
  right; game block names in every message.
- Fixes: document-mode tab widgets left unpainted gaps (now filled); Fusion's bevel
  colors were light; the window size and dock layout are remembered (`window.json`).

## Looks

- Later, not now: the final product should look like a **technical version of Minecraft**,
  cleaner than the current colored boxes. Functionality comes first.
- The UI panels need work, but that is not a current priority.

## Analog signal sources

- Changing placed blocks: Q / Shift+Q rotate the block under the cursor; the inspector
  edits any property (owner request, 2026-10-11).
- Cake as the comparator source feels odd. Wanted: a **generic "signal strength source"**
  in the palette that maps to a real block (lectern, hopper, composter, container, …) and
  can be **hot-swapped** between them, with tooltips explaining how they differ
  (pushability, block entity, update behavior, value range). The real block underneath
  keeps the simulation faithful.

## Performance

- The simulation must easily run in **real time (20 ticks/s)**; the owner saw about half that.
- Measured (2026-10-11): the engine runs about 950–1 300 ticks/s on the busy example world.
  The bottleneck is the renderer: `build_mesh` rebuilds the whole world mesh (~51 ms for
  1 067 blocks) after every tick, so with the 50 ms run timer only about 10 ticks/s happen.
- Plan, as the game client does it: mesh per 16³ section with dirty tracking (only changed
  sections rebuilt), vectorized geometry, and rendering decoupled from simulation (simulate
  at the target rate; draw at most once per frame). Show the achieved ticks/s in the UI.
  Trace detail can stay on: it costs about 30 % of engine time, which is not the bottleneck.
- **Done (2026-10-11):** 8³ chunk meshes with dirty tracking, vectorized geometry, a
  wall-clock-paced run loop and a ticks/s + frames/s overlay. Measured on the owner's
  desktop: 19.9 ticks/s at target 20, paint about 2 ms. Details in [[architecture]]
  ("Rendering and the run loop") and [[decisions]] ADR-017.
