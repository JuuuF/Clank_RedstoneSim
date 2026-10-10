# Redstone simulator documentation

A Python simulator for Minecraft **Java Edition 26.3** redstone, built by porting the
relevant server algorithms from the supplied decompiled source and verified tick by tick
against the real game.

**Start here:** [[project-state]] (what exists, what's verified, what's next, how to resume).

## Navigation

- **Project:** [[project-state]] · [[architecture]] · [[decisions]] · [[roadmap]] · [[implementation-notes]]
- **Research:** [[research/repository-report]] · [[research/source-map]] · [[research/open-questions]] · [[research/wiki-hints]]
- **Mechanics:** [[mechanics/index]] · [[quirks]]
- **Experiments:** [[experiments/index]]

## Current status (2026-10-11)

- Milestones 0, 1, 3 and 4 are done for the initial scope: lever, buttons, lamp, torch
  (with burnout), wire, repeater, comparator and cake work.
- 72 tests pass. A sandboxed 26.3 server confirms 14 of 14 recorded scenarios tick for
  tick, including a same-tick repeater priority race and comparator subtract mode.
- No user interface yet: the editor (M2) is next, then pistons (M5).
- Work happens on branch `feat/sim-core`; nothing has been pushed.

## Owner decisions on record

- In-game testing through a sandboxed dedicated server: approved, testing only (ADR-008).
- Torch burnout: implemented, since it is deterministic in 26.3 (ADR-010).
- Test circuits start simple: door, sliding piston, lamp, inverters, AND gates, …
- Controls: Minecraft-style (WASD + mouse look on right-drag, LMB break, RMB place, MMB pick).
- Wiki pages are hints; the source and the game are proof (ADR-011).
- Docs are the project's long-term memory (ADR-012).

## Open questions for the owner

- None blocking. Lever and button behavior can only be checked in game with a player. If
  you want those verified too, a short manual session in a test world would do; the
  procedure is in [[experiments/index]].
