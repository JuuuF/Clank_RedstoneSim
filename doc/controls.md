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
| **SELECT** | V | select one block (Shift+click: extend the box) | — | draw a box |

- Middle click picks the block type under the cursor in every mode.
- The badge in the bottom-left corner shows the mode and what the mouse buttons do.
- Choosing a block (palette, hotbar keys 1–9, middle-click pick) switches to BUILD.
- Esc in NORMAL clears the inspector selection and the selection box.
- In BUILD, a white outline shows where a right click will put the block.
- Placed blocks are oriented like a player looking at the target from the camera along the
  cursor ray (`Viewport.player_view`).

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
| Ctrl+C / Ctrl+V | copy the selection box / paste at the block under the cursor |
| R | rotate the clipboard 90° |
| Del | clear the selection box (fill with air) |
| 1–9 | hotbar |
| F1 | controls panel |

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
