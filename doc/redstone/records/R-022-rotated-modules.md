# R-022: modules pasted in any rotation behave the same

- **Date:** 2026-10-16 · **Simulator:** 864a6da · **Game:** Java 26.3
- **Script:** `experiments/redstone/R-022-rotated-modules.cli.txt` · **Status:** verified
- **Question:** The library's modules are meant to be pasted turned (`import … rotate
  N`). Do they keep their contracts, and does the port-offset rule in [[circuits]] find
  the ports?
- **Hypothesis:** rotating turns every directional block with the structure (the paste
  is the game's structure rotation), so behavior is the same; port offsets move as
  (dx, dz) → (D − 1 − dz, dx) per quarter turn (D = depth along z before the turn). The
  only thing rotation can change is the coordinate-dependent order of wire updates
  ([[R-017-wire-order]]), which these modules do not rely on.
- **Setup:** a 112×112 world: `clock.nbt` pasted with rotate 0, 1, 2, 3; `xor_gate.nbt`
  with rotate 1 and 3; `piston_door_2x2.nbt` with rotate 1. Each port computed with the
  rule (the script's generator), each input driven by a lever on the side its contract
  names, turned with the module.
- **Procedure:** clocks enabled at 2; XOR truth tables; door lever on 2..30.
- **Observations:** every clock ran with period 8 from tick 4 (on 4..7, off 8..11, on
  12..15); both rotated XOR gates passed their truth tables; the turned door's cells were
  clear from 6 to 33 and stone again from 36.
- **Result:** as predicted: 10 of 10 cases passed.
- **Conclusion:** library modules can be pasted in any rotation; compute ports with:

```python
def rotate_offset(dx, dz, width, depth, turns):
    """Port offset after `import … rotate turns` (width along x, depth along z)."""
    for _ in range(turns):
        dx, dz = depth - 1 - dz, dx
        width, depth = depth, width
    return dx, dz
```

  Inputs come from the rotated side: "from the west" becomes north, east, south for
  1, 2, 3 turns. Confidence: high for these modules (V); a module that relied on wire
  update order could change (R-017).
- **Used by:** [[circuits]] (Using a module).
