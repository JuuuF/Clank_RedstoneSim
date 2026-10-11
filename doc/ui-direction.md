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
