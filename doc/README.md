# Redstone simulator documentation

A Python simulator for Minecraft **Java Edition 26.3** redstone, built by porting the
relevant server algorithms from the supplied decompiled source.

## Navigation

- **Project:** [[architecture]] · [[decisions]] · [[roadmap]] · [[implementation-notes]]
- **Research:** [[research/repository-report]] · [[research/source-map]] · [[research/open-questions]]
- **Mechanics:** [[mechanics/index]] · [[quirks]]
- **Experiments:** [[experiments/index]]

## Current status

Milestones 0 (reconnaissance) and 1 (mechanics reference) are complete for the initial
scope. No application code exists yet; next is the world model and simulation core.

## Open questions for the owner

1. **In-game comparison:** the agent cannot run the Minecraft client. Experiments in
   [[experiments/index]] need you to run them in a clean 26.3 test world.
2. **Torch burnout:** the brief calls burnout "random", but the source
   (`RedstoneTorchBlock.tick`, `isToggledTooFrequently`) shows it is deterministic: 8 toggles
   within 60 game ticks turn a torch off for 160 ticks. It stays out of scope for now as
   briefed. Should it be added later as a deterministic mechanic?
