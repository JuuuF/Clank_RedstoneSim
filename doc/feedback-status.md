# Feedback and feature requests: status

One list of everything the owner asked for, across the project brief and all feedback
rounds, compiled 2026-10-13. Details, causes and code locations per item are in
[[ui-direction]] (rounds 1–9), [[world-import]], [[project-state]] and [[controls]].

## Still open

| # | Request | From | What is missing |
|---|---|---|---|
| O1 | **Open Minecraft worlds**, load around the camera, own cache, write back | round 8 #18 | Done: reading saves, opening, streaming chunks around the camera, an index of the save's builds with "go there" (2026-10-14), reconnecting a saved world document to its save (2026-10-14), write-back to a **copy** with pending ticks, checked in the real game (2026-10-14). Open: writing into the original save, unloading far chunks, an on-disk chunk cache. |
| O5 | **Smooth 60 fps with big contraptions** | round 9 (follow-up) | Done: moving-piston mesh, heavy ticks in parts, faster engine paths, and (2026-10-14) an optional compiled build: 2–3× faster ticks than before the night. Open: the owner's own check on the desktop. |
| O6 | **Generic signal-strength source** that maps to a real block, hot-swappable | round 1 (Analog signal sources) | Done for barrel, lectern and cake. Open: hopper, composter and chest as source kinds (chests and hoppers exist as blocks; composters do not). |
| O7 | **Mechanics left** (brief "later extensions") | brief; project-state | Open: dispense effects (shooting, placing, fluids), detector rails (need minecarts), daylight sensors, composters, furnaces and other containers, water streams; entities stay out of scope. |
| O8 | **Abstract (black-box) group models** | brief M7 | Deferred on purpose (ADR-016): groups expose ports but always simulate their blocks. |
| O9 | **Schematic import/export** | brief M7 ("deferred until the core is stable") | Not started; the core is stable now, so it could follow. |
| O10 | **Final look**: "a technical version of Minecraft", panels | round 1 (Looks) | Largely answered by the game's textures, the theme and the polish pass; the owner has not yet reviewed the result as a whole. |
| O11 | **Owner checks** | rounds 7–9, Mac support | The owner tests Mac support and reviews rounds 7–9, the polish pass, the popup and the frame rate on real hardware. Optional: a short manual game session to verify levers and buttons with a player ([[experiments/index]]). |

| O12 | **Small loose ends** | rounds 9–12 | 0-tick behavior not checked against the real game. Done 2026-10-14: the Select World screen's stray "r" (the text cursor on the placeholder's "T"), its game look (dirt, stone buttons and tabs from the jar), thumbnails made when an older world is opened, colored groups for every timeline category; the timeline height is remembered. |

## Done after the list was compiled

- Save as Minecraft world (a copy of the save), 2026-10-13 ([[world-import]] phase 4).
- **Select World screen** like the game's (owner: the file dialog was slow): Minecraft
  saves, simulation worlds with thumbnails, search, Browse… (`ui/world_picker.py`,
  `recent_worlds.json`, `thumbnails/` in the config folder).

- **Sequences**: ANIMATE mode, power pulses locked to positions with strength and
  duration, Sequence tab, Tab mode ring (ADR-026).

- **Round 10** ([[ui-direction]]): 0-tick pulses; short piston arm while moving (no
  head out of the base's back); the inspector extends a piston with its head; long
  property button lists wrap; the timeline's per-block lines with Ableton-like colored
  groups for pulses, draggable and resizable pulse bars, a resizable, scrolling timeline.
  Open from it: groups for the other categories' lines; the timeline height is not
  remembered between sessions.

- **Round 11**: group colors in the view, hover-to-locate for coordinates everywhere,
  pulse selection with Del, moving selected pulses together, dragging pulses onto
  another block's line.

- **Round 12**: 0-tick pulses act inside a tick (pistons spit their block); sequences
  and all recorded edits are saved with the file (they were lost on reopening); the
  hover highlight clears below the last list row and is more subtle.

- **Signs** (O4, 2026-10-14): text drawn on the sign's board (front and back, in
  perspective); standing and wall signs are real blocks now (placing, popping, text typed
  in the inspector as an edit; game-verified EXP-048). Hanging signs stay foreign blocks
  (their text from opened worlds is drawn too).

- **Diagnostics** (O2, 2026-10-14): Diagnostics → Why? shows a block's chain of causes
  back across ticks; a signal heat view (Alt+H).

- **Several selections act together** (O3, 2026-10-14): move, copy, rotate, flip and
  Ctrl+C work on every box at once (`transform_regions` editor action, one undo step).

- **2026-10-14 (night):** pulses can be muted (bypassed); timeline lines named by
  position with the current block; refactor, stability and speed pass
  ([[refactor-plan]]).

## Implemented

### Project brief (milestones 0–7)

- M0 reconnaissance, M1 source research (every mechanic in [[mechanics/index]] with source
  references), M3 deterministic engine (phases, scheduled ticks, block events, trace,
  snapshots), M4 core redstone (lever, buttons, lamp, torch with burnout, wire,
  repeater, comparator), M5 pistons (QC, BUD, slime/honey, 0-ticks, scheduled-tick
  pulses), M6 playback (run, step tick/event, warp, step back, save mid-tick, pending
  ticks view), M7 contraptions (prefabs, copy/paste, groups with ports).
- Beyond the initial scope, on request: observers, rails (plain/powered/activator),
  target blocks, hoppers, barrels, lecterns, cake, note blocks, copper bulbs, dispensers,
  droppers, chests (double, trapped), pressure plates; the game's textures (owner asked).
- Verified in the real game: 46 named scenarios and 40 random circuits match tick for
  tick ([[experiments/index]]).

### Round 1 (2026-10-11)

- Vim-like modes NORMAL / BUILD / SELECT with a mode badge; camera keys separate from
  command keys; Axiom-like box selections with handles, move and copy.
- Orbit camera around a visible pivot (Blender/Trackmania mix); rebindable keymap.
- Hot-swappable signal source backed by barrel, lectern or cake (see O6 for more kinds).
- Real-time speed: chunked meshes, decoupled run loop, ticks/s and frames/s shown.

### Round 2

- Hotkeys panel (F1); distinct pin handles; thick see-through selection outline; bottom
  face grabbable; Trackmania-style paste on the camera's layer; update-free editor
  cloning (game-verified); translucent build preview; info overlay (F3); X-ray;
  immediate-apply inspector with arrows and toggles; rotate, flip and stack in place.

### Round 3

- Ordered layout; Trackmania inventory with number keys; low-alpha selection body;
  Blender-like gizmos; wheel moves the paste layer; Blender timeline keys and monitor;
  three-way X-ray with adjustable alphas; Enter locks a selection; context hints; stack
  handles change while Shift is held; Ctrl+drag copy fixed; delete keeps neighbor
  updates; F3 debug screen; stress tests against the game (fuzzing); observers, rails,
  target blocks, hoppers.

### Round 4

- Drag to place a line; preview without z-fighting; inventory with favourites row, path
  and block previews; quick block search (double Shift, Ctrl+Space, /); atomic edit
  batches per tick; replay error fixed; fast placements no longer lost; keyframes that
  move and merge, color-coded rows; tick 0 as the build state; fast step back and
  backward playback; observer facing visible.
- Superseded later: "left places, right rotates, Del removes" (round 8 changed it).

### Round 5

- Placing on the layer at the pivot's height (later combined with face placement, round
  9); stacked inventory rows; curved rails; plain observer face; "Set tick 0 here".

### Round 6

- Smoother feel; coherent look; Minecraft vibe with a Blender-like dark UI; the game's
  models and textures from the jar; inventory growing upwards; tick 0 restarts the clock.

### Round 7

- Wheel behavior (changed again in round 8); same-looking folder rows; the game's block
  names; no "unknown action hotbar.N" warnings; fixed-width preferences; X-ray defaults
  30 %/50 %; flat models one pixel high; the layer grid explained and faded.

### UI polish pass (owner: "keep iterating until 6 AM")

- Pixel-art icons, restyled timeline, the game's hotbar sprites, scenery (grass and
  clouds), slot grids for containers, game-style tooltips, remembered window layout.

### Round 8

- Wheel zooms, Shift+wheel moves up/down; BUILD right click removes, Del only clears the
  selection, Q turns; ^ goes up a folder; fixed hint bar height; GL textures freed on
  close; keymap file explained and cleaned; gliding playhead; solid voxel dust; inventory
  only in BUILD as a hotbar overlay; recent blocks (later replaced by palettes, round 9);
  R/H vary the block to place (top slabs etc.); pivot block with a shadow (made quieter
  in round 9); gizmo outlines; filled, breathing selection; warm/cool light; keymap
  editor; world import (see O1 for what is left). The grass ground was kept.

### Mac support and block popup (2026-10-12)

- Mac: extra defaults (⌘F, ⌫, ⌥+right click, ⌘I, ⌘/), symbols, trackpad pinch, rotate,
  smart zoom, two-finger navigation; existing bindings unchanged.
- E over a block opens its inspector as a popup in the viewport.
- Owner priorities of the day: missing blocks (done), world loading (O1), diagnostics
  (O2).

### Round 9 (2026-10-13)

- Piston animation fixed and interpolated between ticks; clouds drift steadily without
  jumps; Diagnostics clicks flash the block; sign texts from saves (see O4); placing
  against the pointed face like Minecraft; red preview when blocked; textures for
  bare-id signs, no see-through faces under signs; rails on the floor; a smaller, quiet
  pivot with a correct shadow; 60 fps frames; F3 label range slider, fade, hover and F
  jump; selection fill without flicker; several selections (see O3); favourite
  palettes; frame rate with many moving pistons (see O5).
