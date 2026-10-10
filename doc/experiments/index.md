# In-game experiments

Comparisons between the simulator and a clean Java Edition 26.3 test world. Each entry
records the setup, the observed in-game result, the simulator result, and the evidence.

No in-game experiments have been run yet. The agent cannot launch the game client; these
experiments need the owner (see [[README#Open questions for the owner]]).

## Template

```markdown
## EXP-NNN: <short title>
- Date / game version: 26.3, clean superflat world, `/tick freeze` + `/tick step` used for timing
- Setup: block list with coordinates and states (or a saved simulator file)
- Procedure: exact inputs and tick at which they were applied
- In-game observation: states per tick, screenshots
- Simulator result: trace excerpt
- Verdict: match / mismatch → linked fix and regression test
```
