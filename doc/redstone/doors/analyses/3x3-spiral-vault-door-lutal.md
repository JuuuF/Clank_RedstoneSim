# Spiral Vault Door by Lutal

World: `piston_doors/3x3 Spiral Vault Door by Lutal.redsim.json` (not committed). Analysis by `python -m tools.doorlab.report` (facts) and by hand (explanation).

## How it works

(to be written)

<!-- generated -->

### Facts from the replay (generated)

- Doorway: 3×3 in the plane x = 3; 9 more output cells outside it.
- Timeline: use lever at 1, use lever at 22; markers Closing 1, Closed 21, Opening 22, Opened 48
- Reference states: closed at tick 21, open at tick 48. Fully closed at ticks 15-25; fully open at 0-2, 36-48.
- Pistons by role: door 19, fires, moves nothing 1
- How extensions were powered (block giving the signal; QC = through the block above the piston): target 12, block←repeater 8, wire 8, observer 4, repeater (QC) 2, block←observer (QC) 2, repeater 2, block←observer 2
- Phases (bursts of piston events): 3–15 (53 events, 19 pistons); 19–36 (57 events, 20 pistons); 40–46 (4 events, 3 pistons)

Doorway frames when they change (`#` solid, `.` open, `~` moving; tick above each; columns north → south for a door across x, west → east across z):

```
  0    3    5    7    9   11   13   15   26   28   30   32   34   36
...  ...  ..~  .~#  ~##  ###  ###  ###  ###  ##.  #..  ...  ...  ...
. .  . ~  . #  . #  ~ #  # #  # #  # #  # .  # .  # .  . .  . .  . .
...  ...  ...  ...  ~..  #~.  ##~  ###  ###  ###  ###  .##  ..#  ...

```

Groups (door blocks by the side they leave through):

| exit | blocks | pistons | moves per block | closed → open |
|---|---|---|---|---|
| above | 6 | 6 | 2×6 | up 1 (6) |
| below | 6 | 6 | 2×6 | down 1 (6) |
| north | 3 | 5 | 2×2, 4×1 | north 1 (2), north 2 (1) |
| south | 2 | 2 | 2×2 | south 1 (2) |

Pistons that fire (role, pulses as start+length → end):

| piston | facing | role | pulses | power |
|---|---|---|---|---|
| 3 2 -3 S | up | door | 9+2→spat, 30+2→pulled | target 2 |
| 3 2 -2 S | up | door | 11+2→spat, 32+2→pulled | block←repeater 2 |
| 3 2 -1 S | up | door | 13+2→spat, 34+2→pulled | target 2 |
| 3 5 -5 S | south | door | 9+2→spat, 30+2→pulled | observer 2 |
| 3 5 1 S | north | door | 3+2→spat, 24+2→pulled | wire 2 |
| 3 8 -3 S | down | door | 9+2→spat, 30+2→pulled | wire 2 |
| 3 8 -2 S | down | door | 7+2→spat, 28+2→pulled | block←repeater 2 |
| 3 8 -1 S | down | door | 5+2→spat, 26+2→pulled | target 2 |
| 4 5 -6 S | south | door | 11+8→pulled, 32+8→pulled | repeater (QC) 2 |
| 4 5 -5 S | south | door | 22+3→retracted, 43+3→pulled | block←observer (QC) 2 |
| 4 5 -4 S | south | door | 14+1→spat, 35+1→pulled | block←observer 2 |
| 5 2 -3 S | up | door | 9+2→spat, 30+2→pulled | target 2 |
| 5 2 -2 S | up | door | 11+2→spat, 32+2→pulled | block←repeater 2 |
| 5 2 -1 S | up | door | 13+2→spat, 34+2→pulled | target 2 |
| 5 5 -5 S | south | door | 9+2→spat, 30+2→pulled | observer 2 |
| 5 5 1 S | north | door | 3+2→spat, 24+2→pulled | wire 2 |
| 5 8 -3 S | down | door | 9+2→spat, 30+2→pulled | wire 2 |
| 5 8 -2 S | down | door | 7+2→spat, 28+2→pulled | block←repeater 2 |
| 5 8 -1 S | down | door | 5+2→spat, 26+2→pulled | target 2 |
| 4 6 -6 | up | fires, moves nothing | 11+8→retracted, 32+8→retracted | repeater 2 |

<!-- end generated -->
