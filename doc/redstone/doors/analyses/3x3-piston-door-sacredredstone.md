# piston door by SacredRedstone

World: `piston_doors/3x3 piston door by SacredRedstone.redsim.json` (not committed). Analysis by `python -m tools.doorlab.report` (facts) and by hand (explanation).

## How it works

(to be written)

<!-- generated -->

### Facts from the replay (generated)

- Doorway: 3×3 in the plane x = 4; 0 more output cells outside it.
- Timeline: use lever at 2, use lever at 43; markers Closing 1, Closed 42, Opening 43, Opened 87
- Reference states: closed at tick 42, open at tick 87. Fully closed at ticks 21-22, 26-29, 40-43; fully open at 0-2, 85-116.
- Pistons by role: door 11
- How extensions were powered (block giving the signal; QC = through the block above the piston): observer 12, block←observer 9, block←observer (QC) 4, block←wire 4, observer (QC) 2, block←lever+wire 2, repeater 2, repeater (QC) 2, block←lever+wire (QC) 1, block←wire (QC) 1
- Phases (bursts of piston events): 1–3 (5 events, 3 pistons); 8–32 (35 events, 8 pistons); 38–40 (3 events, 1 pistons); 44–44 (2 events, 2 pistons); 49–81 (63 events, 11 pistons); 85–85 (1 events, 1 pistons)

Doorway frames when they change (`#` solid, `.` open, `~` moving; tick above each; columns north → south for a door across x, west → east across z):

```
  0    3    5    8   10   13   14   15   16   18   19   20   21   23
...  ~~.  ##.  ##.  ##.  ##~  ##~  ###  ###  ###  #~#  #~#  ###  #~#
...  ...  ...  ~..  #..  #.~  #.~  #.#  #.#  #.#  #~#  #~#  ###  #.#
...  ...  ...  ~..  #..  #..  #~.  #~.  ##.  ##~  ##~  ###  ###  ###

 24   25   26   30   38   40   44   51   56   57   59   60   61   62
#~#  ###  ###  ###  ###  ###  .##  .##  .#.  ~#.  ##.  #~.  #~.  ##.
#~#  #~#  ###  ###  ###  ###  ###  .##  .#.  .#.  .#.  .~.  .~.  .#.
#~#  #~#  ###  ##.  ##~  ###  ###  .##  .##  ..#  ..#  .~#  .~.  .#.

 64   66   67   69   71   77   81   83   85
#~.  ##.  .#~  .##  .##  ...  .~.  .#.  ...
...  ...  ..~  ..#  ..#  ...  ...  ...  ...
.#.  .#.  ...  ..~  ..#  ..#  ...  ...  ...

```

Groups (door blocks by the side they leave through):

| exit | blocks | pistons | moves per block | closed → open |
|---|---|---|---|---|
| south | 3 | 3 | 4×2, 6×1 | south 1 (3) |
| above | 2 | 4 | 4×1, 8×1 | up 1 (2) |
| north | 2 | 2 | 2×2 | north 1 (2) |
| below | 2 | 3 | 4×2 | down 2 (1), down 1, south 1 (1) |

Pistons that fire (role, pulses as start+length → end):

| piston | facing | role | pulses | power |
|---|---|---|---|---|
| 4 4 0 S | up | door | 14+2→spat, 24+2→spat, 55+2→pulled, 65+2→pulled | observer 4 |
| 4 5 2 S | north | door | 20+2→spat, 26+2→spat, 31+1→spat, 57+2→spat, 62+1→pulled | block←observer 5 |
| 4 6 -3 S | south | door | 8+2→spat, 49+2→pulled | observer (QC) 2 |
| 4 6 3 S | north | door | 18+2→spat, 28+2→pulled, 38+2→spat, 59+2→pulled, 69+2→spat, 79+2→pulled | observer 6 |
| 4 7 -3 S | south | door | 8+2→spat, 49+2→pulled | observer 2 |
| 4 7 3 S | north | door | 13+2→spat, 54+2→pulled, 67+2→spat, 75+2→pulled | block←observer (QC) 4 |
| 4 8 3 S | north | door | 13+2→spat, 54+2→pulled, 67+2→spat, 75+2→pulled | block←observer 4 |
| 4 9 0 S | down | door | 19+4→pulled, 60+4→pulled | repeater (QC) 2 |
| 4 10 -1 S | down | door | 3+41→pulled, 57+2→spat, 65+2→pulled | block←lever+wire 1, block←wire 2 |
| 4 10 0 S | down | door | 73+4→pulled, 81+4→pulled | block←lever+wire (QC) 1, block←wire (QC) 1, repeater 2 |
| 4 11 0 S | down | door | 3+41→pulled, 57+2→spat, 65+2→pulled | block←lever+wire 1, block←wire 2 |

<!-- end generated -->
