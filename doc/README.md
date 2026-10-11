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

- Milestones 0–7 have a working core. Blocks: lever, buttons, lamp, torch (with burnout),
  wire, repeater, comparator, barrel, lectern, cake, pistons, slime and honey, observers,
  rails (plain, powered, activator), target blocks and hoppers ([[mechanics/index]]).
- 319 tests pass. A sandboxed 26.3 server confirms 40 of 40 named scenarios and 40 random
  circuits tick for tick, including hopper contents and cooldowns.
- The 3D editor (`redsim`): four rounds of owner feedback are in ([[ui-direction]]); the
  latest made tick 0 the build state, added keyframe rows with move/merge, drag-placed
  lines, block previews and a quick search ([[controls]], ADR-022).
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
