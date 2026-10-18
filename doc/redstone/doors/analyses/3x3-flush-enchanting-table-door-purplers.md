# Flush Enchanting Table Door by Purplers

World: `other_piston_contraptions/3x3 Flush Enchanting Table Door by Purplers.redsim.json` (not committed). Analysis by `python -m tools.doorlab.report` (facts) and by hand (explanation).

## How it works

(to be written)

<!-- generated -->

### Facts from the replay (generated)

- Doorway: 3×3 in the plane z = -4; 0 more output cells outside it.
- Timeline: use oak_button at 1, use oak_button at 63; markers Closing 1, Closed 62, Opening 63, Opened 123
- Reference states: closed at tick 62, open at tick 123. Fully closed at ticks 37-66; fully open at 0-2, 119-137.
- Pistons by role: door 18, idle 6, power mover 3, power switch 3, stack 9
- How extensions were powered (block giving the signal; QC = through the block above the piston): block←observer 31, wire (QC) 25, observer (QC) 12, repeater 9, block←observer (QC) 8, block←wire (QC) 8, block←wire 7, bud 4, wire 2, block←repeater (QC) 1
- Phases (bursts of piston events): 3–53 (149 events, 33 pistons); 57–57 (3 events, 3 pistons); 65–71 (10 events, 4 pistons); 77–119 (127 events, 32 pistons)

Doorway frames when they change (`#` solid, `.` open, `~` moving; tick above each; columns north → south for a door across x, west → east across z):

```
  0    3    5    7   14   15   31   33   35   37   67   69   95  108
...  ...  ...  ...  ...  ...  ~~~  ###  ###  ###  ###  ###  ...  ...
...  ...  ...  ...  ~~~  ###  ###  ###  ###  ###  ###  ###  ###  ###
...  .~.  ~#~  ###  ~~~  ...  ...  .~.  ~#~  ###  #.#  ...  ...  ~~~

109  111  119
...  ...  ...
...  ...  ...
~~~  ###  ...

```

Groups (door blocks by the side they leave through):

| exit | blocks | pistons | moves per block | closed → open |
|---|---|---|---|---|
| below | 6 | 9 | 4×6 | down 2 (3), down 1, south 1 (3) |
| recess | 3 | 9 | 6×3 | south 3 (3) |

Pistons that fire (role, pulses as start+length → end):

| piston | facing | role | pulses | power |
|---|---|---|---|---|
| -3 3 -4 S | up | door | 5+2→spat, 22+3→retracted, 35+2→spat, 67+2→pulled, 97+2→spat, 116+3→pulled | block←observer 4, block←observer (QC) 2 |
| -3 4 -4 S | up | door | 14+1→spat, 108+1→pulled | block←observer 2 |
| -3 4 -2 S | north | door | 32+1→spat, 52+1→spat, 84+1→pulled | block←observer 3 |
| -3 7 -2 S | north | door | 31+2→spat, 93+2→pulled | block←wire 2 |
| -3 7 -1 S | north | door | 40+3→retracted, 102+3→pulled | block←wire (QC) 2 |
| -3 7 0 S | north | door | 15+2→spat, 27+2→spat, 35+2→pulled, 49+2→spat, 77+2→spat, 89+2→spat, 97+2→pulled, 111+2→pulled | wire (QC) 8 |
| -2 3 -4 S | up | door | 3+2→spat, 22+3→retracted, 33+2→spat, 65+2→pulled, 95+2→spat, 116+3→pulled | block←observer 4, block←observer (QC) 2 |
| -2 4 -4 S | up | door | 14+1→spat, 108+1→pulled | block←observer 2 |
| -2 4 -2 S | north | door | 32+1→spat, 52+1→spat, 84+1→pulled | block←observer 3 |
| -2 7 -2 S | north | door | 31+2→spat, 93+2→pulled | block←wire 2 |
| -2 7 -1 S | north | door | 40+3→retracted, 102+3→pulled | block←wire (QC) 2 |
| -2 7 0 S | north | door | 15+2→spat, 27+2→spat, 35+2→pulled, 49+2→spat, 77+2→spat, 89+2→spat, 97+2→pulled, 111+2→pulled | wire (QC) 8 |
| -1 3 -4 S | up | door | 5+2→spat, 22+3→retracted, 35+2→spat, 67+2→pulled, 97+2→spat, 116+3→pulled | block←observer 4, block←observer (QC) 2 |
| -1 4 -4 S | up | door | 14+1→spat, 108+1→pulled | block←observer 2 |
| -1 4 -2 S | north | door | 32+1→spat, 52+1→spat, 84+1→pulled | block←observer 3 |
| -1 7 -2 S | north | door | 31+2→spat, 93+2→pulled | block←wire 2 |
| -1 7 -1 S | north | door | 40+3→retracted, 102+3→pulled | block←wire (QC) 2 |
| -1 7 0 S | north | door | 15+2→spat, 27+2→spat, 35+2→pulled, 49+2→spat, 77+2→spat, 89+2→spat, 97+2→pulled, 111+2→pulled | wire (QC) 8 |
| 0 3 -2 S | down | power mover | pulled at 9, 71+None→held | wire (QC) 1 |
| 0 10 0 S | north | power mover | 27+2→spat, 49+2→pulled, 89+2→spat, 111+2→pulled | block←observer 4 |
| 1 4 -4 S | down | power mover | pulled at 31, 93+None→held | block←repeater (QC) 1 |
| -3 4 0 S | north | power switch | pulled at 21, 91+None→held | block←wire (QC) 1 |
| -2 4 0 S | north | power switch | pulled at 21, 91+None→held | block←wire 1 |
| -1 4 0 S | north | power switch | pulled at 21, 91+None→held | block←wire (QC) 1 |
| -3 2 -4 S | up | stack | 11+8→pulled, 105+8→pulled | bud 2 |
| -3 2 -2 S | up | stack | 29+8→pulled, 49+8→pulled, 81+8→pulled | repeater 3 |
| -3 9 -1 S | down | stack | 23+2→spat, 45+2→pulled, 85+2→spat, 107+2→pulled | observer (QC) 4 |
| -2 2 -4 S | up | stack | 11+8→pulled, 105+8→pulled | wire 2 |
| -2 2 -2 S | up | stack | 29+8→pulled, 49+8→pulled, 81+8→pulled | repeater 3 |
| -2 9 -1 S | down | stack | 23+2→spat, 45+2→pulled, 85+2→spat, 107+2→pulled | observer (QC) 4 |
| -1 2 -4 S | up | stack | 11+8→pulled, 105+8→pulled | bud 2 |
| -1 2 -2 S | up | stack | 29+8→pulled, 49+8→pulled, 81+8→pulled | repeater 3 |
| -1 9 -1 S | down | stack | 23+2→spat, 28+1→spat, 45+2→pulled, 85+2→spat, 90+1→spat, 107+2→pulled | observer (QC) 4, block←observer (QC) 2 |

<!-- end generated -->
