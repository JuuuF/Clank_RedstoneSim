# Redstone simulator documentation

A Python simulator for Minecraft **Java Edition 26.3** redstone, built by porting the
relevant server algorithms from the supplied decompiled source and verified tick by tick
against the real game.

**Start here:** [[project-state]] (what exists, what's verified, what's next, how to resume).
To click through the simulator: [[tour]].

## Navigation

- **Project:** [[project-state]] · [[tour]] · [[controls]] · [[ui-direction]] · [[architecture]] · [[decisions]] · [[roadmap]] · [[implementation-notes]]
- **Research:** [[research/repository-report]] · [[research/source-map]] · [[research/open-questions]] · [[research/wiki-hints]]
- **Mechanics:** [[mechanics/index]] · [[quirks]]
- **Experiments:** [[experiments/index]]

## Current status (2026-10-11)

- Milestones 0–4 are done for the initial scope, and pistons (M5) work: lever, buttons,
  lamp, torch (with burnout), wire, repeater, comparator, cake, pistons, sticky pistons,
  slime and honey.
- 165 tests pass. A sandboxed 26.3 server confirms 22 of 22 recorded scenarios tick for
  tick, including a repeater priority race, comparator modes, QC doors and block spitting.
- The 3D editor works (`python -m redsim`): rewind/replay (M6), copy/paste with `/clone`
  semantics, prefabs and groups (M7). All seven milestones have a working core.
- After the owner's first hands-on session: real-time running (ADR-017), and the new
  controls: modes, orbit camera, rebindable keymap (ADR-018, [[controls]]).
- Work happens on feature branches; verified work is fast-forwarded to `main` and pushed.

## Owner decisions on record

- In-game testing through a sandboxed dedicated server: approved, testing only (ADR-008).
- Torch burnout: implemented, since it is deterministic in 26.3 (ADR-010).
- Test circuits start simple: door, sliding piston, lamp, inverters, AND gates, …
- Controls: vim-like modes, Blender-style orbit camera, rebindable keymap ([[controls]],
  [[ui-direction]]); replaces the first Minecraft-style fly controls.
- Wiki pages are hints; the source and the game are proof (ADR-011).
- Docs are the project's long-term memory (ADR-012).

## Open questions for the owner

- None blocking. Lever and button behavior can only be checked in game with a player. If
  you want those verified too, a short manual session in a test world would do; the
  procedure is in [[experiments/index]].
