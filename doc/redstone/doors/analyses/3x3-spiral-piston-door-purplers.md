# spiral piston door by Purplers

World: `piston_doors/3x3 spiral piston door by Purplers.redsim.json` (not committed). Analysis by `python -m tools.doorlab.report` (facts) and by hand (explanation).

## How it works

(to be written)

<!-- generated -->

### Facts from the replay (generated)

- Doorway: 3×3 in the plane x = -1; 0 more output cells outside it.
- Timeline: use lever at 1, use lever at 23; markers Closing 1, Closed 22, Opening 23, Opened 47
- Reference states: closed at tick 22, open at tick 47. Fully closed at ticks 20-27; fully open at 0-3, 44-47.
- Pistons by role: door 10, fires, moves nothing 1, power mover 1, stack 1
- How extensions were powered (block giving the signal; QC = through the block above the piston): block←observer 7, observer (QC) 4, observer 4, wire 4, bud 2, wire (QC) 2, block←repeater 2, block←wire 2, block←lever 1
- Phases (bursts of piston events): 2–20 (35 events, 12 pistons); 24–44 (43 events, 13 pistons)

Doorway frames when they change (`#` solid, `.` open, `~` moving; tick above each; columns north → south for a door across x, west → east across z):

```
  0    4    6    8   10   12   14   16   18   20   28   30   32   34
...  ...  ...  ...  ..~  .~#  ~##  ###  ###  ###  ###  ###  ###  ##.
...  ...  ...  ..~  ..#  .~#  .##  ~##  ###  ###  ###  ###  ##.  ##.
...  .~.  .#~  .##  .##  .~#  .##  .##  ~##  ###  #.#  #..  #..  #..

 35   36   38   40   42   44
##.  #..  ...  ...  ...  ...
##.  #..  #..  ...  ...  ...
#~.  #~.  ##.  ##.  .#.  ...

```

Groups (door blocks by the side they leave through):

| exit | blocks | pistons | moves per block | closed → open |
|---|---|---|---|---|
| above | 3 | 3 | 2×3 | up 1 (3) |
| below | 2 | 3 | 4×2 | down 2 (1), down 1, south 1 (1) |
| south | 2 | 2 | 2×2 | south 1 (2) |
| north | 2 | 2 | 2×2 | north 1 (2) |

Pistons that fire (role, pulses as start+length → end):

| piston | facing | role | pulses | power |
|---|---|---|---|---|
| -1 2 0 S | up | door | 4+2→spat, 12+2→spat, 26+2→pulled, 43+1→pulled | block←observer 2, observer 2 |
| -1 3 0 S | up | door | 35+1→pulled | block←observer 1 |
| -1 3 2 S | north | door | 8+2→spat, 30+2→pulled | wire 2 |
| -1 4 -3 S | south | door | 18+2→spat, 40+2→pulled | block←observer 2 |
| -1 4 3 S | north | door | 6+2→spat, 28+2→pulled | bud 2 |
| -1 5 -3 S | south | door | 16+2→spat, 38+2→pulled | observer (QC) 2 |
| -1 5 3 S | north | door | 8+2→spat, 30+2→pulled | wire (QC) 2 |
| -1 8 -1 S | down | door | 14+2→spat, 36+2→pulled | wire 2 |
| -1 8 0 S | down | door | 12+2→spat, 34+2→pulled | block←repeater 2 |
| -1 8 1 S | down | door | 10+2→spat, 32+2→pulled | block←wire 2 |
| 0 1 2 | up | fires, moves nothing | 2+22→retracted | block←lever 1 |
| 0 1 0 S | north | power mover | 4+2→pulled, 26+2→spat | block←observer 2 |
| -1 1 0 S | up | stack | 32+4→retracted, 39+1→pulled, 43+None→held | observer (QC) 2, observer 2 |

<!-- end generated -->
