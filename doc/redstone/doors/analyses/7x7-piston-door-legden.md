# Piston Door by LegDen

World: `piston_doors/7x7 Piston Door by LegDen [broken sim].redsim.json` (not committed). Analysis by `python -m tools.doorlab.report` (facts) and by hand (explanation).

## How it works

(to be written)

<!-- generated -->

### Facts from the replay (generated)

- Doorway: 7×7 in the plane z = -3; 0 more output cells outside it.
- Timeline: use lever at 1, use lever at 71; markers Closing 1, Closed 70, Opening 71, Opened 123
- Reference states: closed at tick 70, open at tick 123. Fully closed at ticks 19-71; fully open at 0-1.
- Pistons by role: door 47, fires, moves nothing 94, helper 66, idle 72, power mover 112, power switch 14, stack 82
- How extensions were powered (block giving the signal; QC = through the block above the piston): observer 187, block←wire 149, target 121, observer (QC) 120, block←observer 107, block←wire (QC) 88, redstone_block (QC) 63, block←observer (QC) 60, wire 53, wire (QC) 47, target (QC) 47, redstone_block 42, repeater 25, block←repeater (QC) 17, bud 16, block←repeater 16, repeater (QC) 13, block←comparator (QC) 8, block←comparator 8, block←observer+wire 5, comparator 5, block←torch (QC) 5, block←torch 5, block←observer+wire (QC) 4, bud (QC) 3, comparator (QC) 3, block←comparator+wire (QC) 2, block←repeater+wire 2, lamp 1
- Phases (bursts of piston events): 1–66 (1405 events, 289 pistons); 72–113 (1890 events, 347 pistons); 117–117 (1 events, 1 pistons)

Doorway frames when they change (`#` solid, `.` open, `~` moving; tick above each; columns north → south for a door across x, west → east across z):

```
      0        2        4        5        7        8       10       11
.......  #######  #######  #######  #######  #######  #######  #######
.......  ~......  #......  ~~.....  ##.....  ~~~....  ###....  ~~~~...
.......  ~......  #......  ~~.....  ##.....  ~~~....  ###....  ~~~~...
.......  ~......  #......  ~~.....  ##.....  ~~~....  ###....  ~~~~...
.......  ~......  #......  ~~.....  ##.....  ~~~....  ###....  ~~~~...
.......  ~......  #......  ~~.....  ##.....  ~~~....  ###....  ~~~~...
.......  #######  #######  #######  #######  #######  #######  #######

     13       14       16       17       19       72       81       83
#######  #######  #######  #######  #######  ##.....  ~#.....  ##.....
####...  ~~~~~..  #####..  ~~~~~~~  #######  #######  ~######  #######
####...  ~~~~~..  #####..  ~~~~~~~  #######  #######  ~######  #######
####...  ~~~~~..  #####..  ~~~~~~~  #######  #######  ~######  #######
####...  ~~~~~..  #####..  ~~~~~~~  #######  #######  ~######  #######
####...  ~~~~~..  #####..  ~~~~~~~  #######  #######  ~######  #######
#######  #######  #######  #######  #######  ##.....  ~#.....  ##.....

     90
.......
######.
######.
######.
######.
######.
.......

```

Groups (door blocks by the side they leave through):

| exit | blocks | pistons | moves per block | closed → open |
|---|---|---|---|---|
| stays in the doorway | 30 | 26 | 2×1, 6×25, 7×4 | up 1 (5), stays (25) |
| above | 8 | 15 | 2×6, 4×1, 8×1 | up 2 (1), up 1 (6), up 2, north 1 (1) |
| below | 7 | 8 | 2×6, 3×1 | down 1 (6), stays (1) |
| east | 5 | 5 | 2×5 | east 1 (5) |

Pistons that fire (role, pulses as start+length → end):

| piston | facing | role | pulses | power |
|---|---|---|---|---|
| -11 5 -3 S | east | door | 2+0→spat, 5+2→spat, 12+2→pulled, 18+2→spat, 30+2→pulled, 42+2→pulled, 80+2→spat, 89+2→pulled | block←wire (QC) 1, observer 6, observer (QC) 3 |
| -11 6 -3 S | east | door | 2+0→spat, 5+2→spat, 12+2→pulled, 18+2→spat, 30+2→pulled, 42+2→pulled, 89+2→spat | block←wire 1, observer (QC) 5, observer 3, block←wire (QC) 2 |
| -11 7 -3 S | east | door | 2+0→spat, 5+2→spat, 12+2→pulled, 18+2→spat, 30+2→pulled, 42+2→pulled, 89+2→spat | block←wire (QC) 1, observer 4, observer (QC) 3, block←wire 2 |
| -11 8 -3 S | east | door | 2+0→spat, 5+2→spat, 12+2→pulled, 18+2→spat, 30+2→pulled, 42+2→pulled, 89+2→spat | block←wire 1, observer (QC) 5, observer 3, block←wire (QC) 2 |
| -11 9 -3 S | east | door | 2+0→spat, 5+2→spat, 12+2→pulled, 18+2→spat, 30+2→pulled, 42+2→pulled, 89+2→spat | block←wire (QC) 1, observer 4, bud 3, block←wire 2 |
| -9 5 -3 S | east | door | 8+0→spat, 29+0→pulled, 88+0→pulled | observer 3 |
| -9 6 -3 S | east | door | 8+0→spat, 29+0→pulled | observer (QC) 2 |
| -9 7 -3 S | east | door | 8+0→spat, 29+0→pulled | observer 2 |
| -9 8 -3 S | east | door | 8+0→spat, 29+0→pulled | observer (QC) 2 |
| -9 9 -3 S | east | door | 8+0→spat, 29+0→pulled | observer 2 |
| -7 5 -3 S | east | door | 11+2→spat, 16+0→spat, 26+0→pulled, 40+32→retracted | wire (QC) 3, target 1 |
| -7 6 -3 S | east | door | 11+2→spat, 16+0→spat, 26+0→pulled, 40+32→retracted | wire 4 |
| -7 7 -3 S | east | door | 11+2→spat, 16+0→spat, 26+0→pulled, 40+32→retracted | wire (QC) 4 |
| -7 8 -3 S | east | door | 11+2→spat, 16+0→spat, 26+0→pulled, 40+32→retracted | wire 4 |
| -7 9 -3 S | east | door | 11+2→spat, 16+0→spat, 26+0→pulled, 40+32→retracted | wire (QC) 4 |
| -5 5 -3 S | east | door | 14+0→spat | block←observer 1 |
| -5 6 -3 S | east | door | 14+0→spat | observer 1 |
| -5 7 -3 S | east | door | 14+0→spat | observer (QC) 1 |
| -5 8 -3 S | east | door | 14+0→spat | observer 1 |
| -5 9 -3 S | east | door | 14+0→spat | observer 1 |
| -3 5 -3 S | east | door | 17+3→pulled, 78+2→spat, 87+0→pulled, 90+2→spat | block←wire 4 |
| -3 6 -3 S | east | door | 17+3→pulled | block←wire (QC) 1 |
| -3 7 -3 S | east | door | 17+3→pulled, 78+2→spat, 83+1→pulled, 87+0→spat, 90+2→pulled, 95+1→spat | block←wire 7 |
| -3 8 -3 S | east | door | 17+3→pulled | block←wire (QC) 1 |
| -3 9 -3 S | east | door | 17+3→pulled, 87+0→pulled, 90+2→spat | block←wire 3 |
| -2 3 -3 | east | door | 10+2→spat, 20+None→held | block←wire 3 |
| 0 2 -3 S | up | door | 2+0→spat, 81+9→pulled | target 2 |
| 0 12 -3 S | down | door | 2+0→spat, 89+1→pulled | block←wire (QC) 1, observer (QC) 1 |
| 0 12 -1 S | north | door | 19+2→pulled, 87+2→spat | comparator 2 |
| 0 13 -3 S | down | door | 82+2→pulled | observer 1 |
| 1 2 -3 S | up | door | 2+0→spat, 81+9→pulled | target 2 |
| 1 12 -3 S | down | door | 2+0→spat, 89+1→pulled | wire (QC) 1, observer (QC) 1 |
| 2 2 -3 S | up | door | 2+0→spat, 72+0→pulled | target 2 |
| 2 12 -3 S | down | door | 2+0→spat, 72+0→pulled | wire 2 |
| 3 2 -3 S | up | door | 2+0→spat, 72+0→pulled | target 2 |
| 3 12 -3 S | down | door | 2+0→spat, 72+0→pulled | wire 2 |
| 4 2 -3 S | up | door | 2+0→spat, 72+0→pulled | target 2 |
| 4 12 -3 S | down | door | 2+0→spat, 72+0→pulled | wire 2 |
| 5 2 -3 S | up | door | 2+0→spat, 72+0→pulled | target 2 |
| 5 12 -3 S | down | door | 2+0→spat, 72+0→pulled | target 2 |
| 6 2 -3 S | up | door | 2+0→spat, 72+0→pulled | target 2 |
| 6 12 -3 S | down | door | 2+0→spat, 72+0→pulled | target (QC) 2 |
| 11 5 -3 S | west | door | 17+0→spat, 90+0→pulled | observer (QC) 1, target 1 |
| 11 6 -3 S | west | door | 17+0→spat, 90+0→pulled | observer 1, target (QC) 1 |
| 11 7 -3 S | west | door | 17+0→spat, 90+0→pulled | block←observer 1, target 1 |
| 11 8 -3 S | west | door | 17+0→spat, 90+0→pulled | observer (QC) 1, target (QC) 1 |
| 11 9 -3 S | west | door | 17+0→spat, 90+0→pulled | observer 1, target 1 |
| -11 3 5 | up | fires, moves nothing | 2+70→retracted | wire 1 |
| -11 13 -3 | north | fires, moves nothing | 2+70→retracted | target 1 |
| -10 3 4 | east | fires, moves nothing | 62+2→retracted, retracted at 66 | observer (QC) 1 |
| -10 8 3 | down | fires, moves nothing | 2+70→retracted | target 1 |
| -9 2 -3 | down | fires, moves nothing | 8+0→spat, 29+0→spat, 78+0→spat, 88+0→spat | block←observer 4 |
| -9 3 3 | down | fires, moves nothing | 5+0→spat, 11+0→spat, 17+0→spat, 23+0→spat, 29+0→spat, 35+0→spat, 41+0→spat, 47+0→spat, 53+0→spat, 59+0→spat | redstone_block (QC) 10 |
| -8 3 -1 | west | fires, moves nothing | 32+2→spat, 82+0→spat | block←observer (QC) 2 |
| -8 4 -1 | south | fires, moves nothing | 32+2→spat, 82+0→spat | block←observer 2 |
| -8 6 -5 S | south | fires, moves nothing | 11+1→spat, 85+2→spat, 96+2→spat | observer (QC) 2, observer 1 |
| -8 7 -5 S | south | fires, moves nothing | 11+1→spat, 85+2→spat, 96+2→spat | observer 2, observer (QC) 1 |
| -8 8 -5 S | south | fires, moves nothing | 11+1→spat, 85+2→spat, 96+2→spat | observer (QC) 2, observer 1 |
| -8 9 -5 S | south | fires, moves nothing | 11+1→spat, 85+2→spat, 96+2→spat | observer 2, observer (QC) 1 |
| -8 10 -1 | north | fires, moves nothing | 22+2→spat | observer (QC) 1 |
| -8 11 3 | west | fires, moves nothing | retracted at 2, 8+0→spat, 14+0→spat, 20+0→spat, 26+0→spat, 32+0→spat, 38+0→spat, 44+0→spat, 50+0→spat, 56+0→spat, 62+None→held | target 10 |
| -7 1 0 | west | fires, moves nothing | 72+0→spat, 75+0→spat, 78+0→spat, 81+2→spat, 93+0→spat, 105+None→held | block←wire 6 |
| -7 2 -5 | south | fires, moves nothing | 4+72→retracted | block←observer 1 |
| -7 4 -5 | down | fires, moves nothing | 10+3→retracted, 16+0→spat, 26+0→spat, 40+32→retracted, 82+2→spat | block←observer 2, wire 3 |
| -7 4 5 | up | fires, moves nothing | 82+8→retracted | repeater 1 |
| -7 11 -5 | south | fires, moves nothing | 22+2→spat | block←wire 1 |
| -7 12 -3 | north | fires, moves nothing | 8+2→spat, 26+2→spat | observer (QC) 1, wire 1 |
| -6 1 0 | north | fires, moves nothing | 72+0→spat, 75+0→spat, 78+0→spat, 81+2→spat, 93+0→spat, 105+None→held | block←torch (QC) 5, block←wire (QC) 1 |
| -6 3 -3 | west | fires, moves nothing | 14+0→spat, 20+0→spat, 32+0→spat, 38+0→spat, 41+31→retracted | block←observer (QC) 2, block←observer 2, target (QC) 1 |
| -6 4 5 | down | fires, moves nothing | 72+0→spat, 76+2→spat, 98+0→spat | block←repeater (QC) 2, block←observer (QC) 1 |
| -6 5 0 S | north | fires, moves nothing | 84+9→retracted, 102+None→held | block←comparator (QC) 2 |
| -6 5 5 | west | fires, moves nothing | 72+0→spat, 76+2→spat, 98+0→spat | block←repeater 2, block←observer 1 |
| -6 6 0 S | north | fires, moves nothing | 84+9→retracted, 102+None→held | block←comparator 2 |
| -6 8 -2 S | east | fires, moves nothing | 78+3→retracted, 90+None→held | block←observer (QC) 1, block←observer 1 |
| -6 10 4 | down | fires, moves nothing | 2+70→retracted, 83+2→spat, 91+2→spat | bud (QC) 1, block←observer 1, observer 1 |
| -6 11 3 | north | fires, moves nothing | 83+2→spat | block←observer 1 |
| -6 12 -5 | east | fires, moves nothing | 22+2→spat, 90+2→spat | block←wire 1, block←observer (QC) 1 |
| -6 12 4 | east | fires, moves nothing | 10+70→retracted, 83+2→spat | repeater (QC) 1, block←observer 1 |
| -6 13 -5 | east | fires, moves nothing | 90+2→spat | block←observer 1 |
| -5 2 1 | down | fires, moves nothing | 72+0→spat, 75+0→spat, 78+0→spat, 93+0→spat, 105+None→held | block←torch 5 |
| -5 2 3 | south | fires, moves nothing | 72+0→spat, 75+0→spat, 78+0→spat, 102+None→held | target 4 |
| -5 3 -3 | south | fires, moves nothing | 14+0→spat, 20+0→spat, 32+0→spat, 38+0→spat | block←observer 2, block←observer (QC) 2 |
| -5 3 0 | up | fires, moves nothing | 15+0→spat, 22+0→spat, 83+0→spat, 90+0→spat | observer (QC) 4 |
| -5 4 4 | north | fires, moves nothing | 74+4→retracted, 96+None→held | observer 3, block←observer (QC) 1 |
| -5 8 -5 | west | fires, moves nothing | 16+4→retracted, 74+2→spat, 79+1→spat, 83+1→spat, 87+0→spat, 90+2→spat, 95+1→spat | block←wire 7 |
| -5 8 -1 S | east | fires, moves nothing | 78+2→spat | block←observer (QC) 1 |
| -5 8 3 | south | fires, moves nothing | 76+2→spat, 81+2→spat, 86+1→spat, 97+2→spat, 103+2→spat, 108+2→spat | observer (QC) 6 |
| -5 11 -2 | east | fires, moves nothing | 72+2→spat, 93+2→spat | target (QC) 2 |
| -5 12 -6 | west | fires, moves nothing | 18+2→spat, 36+2→spat, 90+2→spat, 99+2→spat | observer (QC) 3, block←observer (QC) 1 |
| -5 13 2 | north | fires, moves nothing | 9+2→spat, 77+2→spat | block←observer 2 |
| -4 3 -2 | up | fires, moves nothing | 22+4→retracted, 30+4→retracted, 88+4→retracted, 96+4→retracted, 105+3→retracted, 113+4→retracted | repeater 6 |
| -4 4 -3 | south | fires, moves nothing | 14+0→spat, 80+4→retracted, 101+4→retracted | block←observer 1, comparator (QC) 2 |
| -4 4 -1 | north | fires, moves nothing | 76+2→spat, 86+2→spat | observer 3 |
| -4 4 3 | down | fires, moves nothing | 97+0→spat | block←observer (QC) 1 |
| -4 5 0 S | north | fires, moves nothing | 100+None→held | block←repeater 1 |
| -4 6 3 S | east | fires, moves nothing | 98+None→held | block←wire (QC) 1 |
| -4 7 0 S | north | fires, moves nothing | 96+None→held | block←repeater 1 |
| -4 12 -3 | east | fires, moves nothing | 75+16→retracted | redstone_block (QC) 1 |
| -3 1 -6 | west | fires, moves nothing | 16+4→retracted, 74+2→spat, 79+1→spat, 83+1→spat, 87+0→spat, 90+2→spat, 95+1→spat | block←wire (QC) 7 |
| -3 2 -6 | east | fires, moves nothing | 16+4→retracted, 74+2→spat, 79+1→spat, 83+1→spat, 87+0→spat, 90+2→spat, 95+1→spat | block←wire 7 |
| -3 10 5 | west | fires, moves nothing | 96+2→spat | observer 1 |
| -3 11 -3 | down | fires, moves nothing | 26+2→spat, 31+1→spat, 96+2→spat, 101+1→spat | block←wire 4 |
| -3 11 -1 | down | fires, moves nothing | retracted at 72, 81+2→spat, 87+2→spat, 93+None→held | wire (QC) 3 |
| -3 11 2 | up | fires, moves nothing | 87+2→spat | repeater 1 |
| -3 11 4 | east | fires, moves nothing | 94+2→spat | block←observer+wire 1 |
| -3 13 -6 | down | fires, moves nothing | 24+4→retracted, 94+4→retracted | repeater 2 |
| -2 1 1 | west | fires, moves nothing | 72+0→spat, 75+0→spat, 78+0→spat, 98+None→held | target 4 |
| -2 3 3 | north | fires, moves nothing | 6+68→retracted, 80+10→retracted | comparator (QC) 1, block←comparator 1 |
| -2 6 -5 S | south | fires, moves nothing | 16+4→retracted, 82+2→spat, 94+2→spat | target 4 |
| -2 7 -5 S | south | fires, moves nothing | 16+4→retracted, 82+2→spat, 94+2→spat | target (QC) 6 |
| -2 8 -5 S | south | fires, moves nothing | 16+4→retracted, 82+2→spat, 94+2→spat | target 4 |
| -2 11 -3 | down | fires, moves nothing | 26+2→spat, 31+1→spat, 96+2→spat, 101+1→spat | target (QC) 4 |
| -2 12 -1 | down | fires, moves nothing | retracted at 72, 81+2→spat, 87+2→spat, 93+None→held | wire (QC) 3 |
| -1 1 1 | south | fires, moves nothing | 72+0→spat, 75+0→spat, 78+0→spat, 98+None→held | block←repeater (QC) 4 |
| -1 1 4 | north | fires, moves nothing | retracted at 72, 75+0→spat, 78+0→spat, 96+2→spat | block←comparator+wire (QC) 2, block←observer (QC) 1 |
| -1 12 -3 | down | fires, moves nothing | 2+0→spat, 77+2→spat, 93+2→spat | block←wire 1, observer 2 |
| 0 13 0 | north | fires, moves nothing | 80+2→spat, 86+2→spat | observer 2 |
| 1 13 -3 S | down | fires, moves nothing | 72+0→spat, 76+2→spat, 82+2→spat | wire 1, observer 2 |
| 1 13 0 | north | fires, moves nothing | 74+2→spat, 80+2→spat, 86+2→spat | lamp 1, observer 2 |
| 2 1 4 | west | fires, moves nothing | retracted at 2, 75+None→held | redstone_block (QC) 1 |
| 3 1 -6 | west | fires, moves nothing | 4+2→spat | block←observer 1 |
| 4 12 3 | north | fires, moves nothing | 2+0→spat, 72+0→spat, 75+2→spat, 80+1→spat | target (QC) 2, block←observer 2 |
| 4 13 3 | west | fires, moves nothing | 2+0→spat, 72+0→spat | target 2 |
| 5 12 -4 | east | fires, moves nothing | 2+0→spat, 72+0→spat | target (QC) 2 |
| 6 1 -6 | west | fires, moves nothing | 9+2→spat, 17+2→spat, 79+2→spat, 87+2→spat | observer (QC) 2, observer 2 |
| 7 13 -6 | east | fires, moves nothing | 10+2→spat, 80+2→spat | observer 2 |
| 7 13 4 | west | fires, moves nothing | 82+2→spat | block←observer 1 |
| 8 4 -5 | down | fires, moves nothing | 17+0→spat, 23+0→spat, 78+0→spat, 87+0→spat, 93+0→spat | redstone_block (QC) 5 |
| 9 1 -4 | west | fires, moves nothing | 16+2→spat, 87+2→spat | bud 2 |
| 9 1 2 | south | fires, moves nothing | 2+0→spat, 72+0→spat | block←wire 2 |
| 9 1 4 | south | fires, moves nothing | 2+0→spat, 72+0→spat, 80+2→spat | target (QC) 2, bud 1 |
| 9 4 -5 | down | fires, moves nothing | 78+0→spat, 90+0→spat | redstone_block (QC) 2 |
| 9 6 5 | north | fires, moves nothing | 2+70→retracted | wire (QC) 1 |
| 10 2 3 | north | fires, moves nothing | 4+2→spat, 75+0→spat, 78+None→held | observer 2, redstone_block 1 |
| 11 1 1 | north | fires, moves nothing | retracted at 72, 76+None→held | redstone_block (QC) 1 |
| 11 2 -1 | west | fires, moves nothing | retracted at 72, 75+0→spat, 78+0→spat, 81+0→spat, 84+0→spat, 87+0→spat, 90+0→spat, 93+None→held | redstone_block (QC) 7 |
| 11 3 4 | north | fires, moves nothing | retracted at 2, retracted at 72, 75+None→held | redstone_block (QC) 1 |
| 11 4 1 | north | fires, moves nothing | 22+2→spat, 92+2→spat | block←observer 2 |
| 11 6 0 | south | fires, moves nothing | 72+0→spat, 75+0→spat, 78+0→spat, 81+0→spat, 84+0→spat, 87+0→spat, 90+0→spat | block←wire 7 |
| 11 9 -5 | north | fires, moves nothing | 15+2→spat, 21+2→spat, 88+2→spat | observer 4 |
| 11 12 4 | up | fires, moves nothing | 2+70→retracted | wire 1 |
| -11 4 3 S | up | helper | pulled at 2, 16+2→spat, 74+None→held | observer 2 |
| -10 2 -2 S | east | helper | 37+35→pulled | target 1 |
| -10 7 1 S | up | helper | 2+70→pulled, 75+1→spat | block←wire 1, observer 1 |
| -10 12 -3 S | north | helper | 2+70→pulled | target 1 |
| -9 1 -6 S | east | helper | 2+70→pulled, 75+1→spat, 79+1→pulled, 92+2→spat | bud 1, observer 3 |
| -9 1 0 S | north | helper | 4+2→spat, 74+2→pulled | observer (QC) 2 |
| -9 3 5 S | up | helper | 2+70→pulled, 75+1→spat | wire 1, observer (QC) 1 |
| -9 4 2 S | west | helper | 88+2→pulled | observer 1 |
| -9 8 2 S | up | helper | 2+70→pulled, 88+2→spat | target 1, observer (QC) 1 |
| -9 10 3 | east | helper | retracted at 2, 8+0→spat, 14+0→spat, 20+0→spat, 26+0→spat, 32+0→spat, 38+0→spat, 44+0→spat, 50+0→spat, 56+0→spat, 62+None→held | redstone_block 10 |
| -9 13 1 S | north | helper | 20+2→spat | block←observer 1 |
| -8 1 3 S | west | helper | 79+2→spat | observer 1 |
| -7 12 1 S | north | helper | 2+70→pulled, 76+2→spat | wire 1, observer (QC) 1 |
| -6 7 4 S | down | helper | 72+0→spat, 98+0→spat | block←comparator (QC) 2 |
| -5 1 5 S | north | helper | 2+70→pulled, 76+2→spat | block←wire 1, observer 1 |
| -5 9 4 S | down | helper | 2+70→pulled, 97+None→held | block←wire (QC) 1, block←observer 1 |
| -4 3 -5 | up | helper | 16+2→retracted, retracted at 20, 23+1→spat, 82+2→spat, 87+1→spat, 94+2→spat, 103+2→spat, 108+1→spat | observer (QC) 5, observer 3 |
| -4 4 5 S | east | helper | 2+70→pulled, 76+2→spat, 86+2→pulled | redstone_block 1, block←observer (QC) 2 |
| -4 11 -5 | down | helper | 76+2→spat, 97+2→spat | observer 2 |
| -3 3 3 | up | helper | 72+2→spat | block←comparator (QC) 1 |
| -3 4 3 | up | helper | 107+None→held | wire (QC) 1 |
| -3 6 -4 S | east | helper | 78+2→spat, 87+0→pulled, 90+2→spat | block←wire 3 |
| -3 8 -4 S | east | helper | 78+2→spat, 87+0→pulled, 90+2→spat | block←wire 3 |
| -2 5 4 S | north | helper | 80+0→pulled | observer (QC) 1 |
| -2 9 -5 S | south | helper | 16+4→retracted, 82+2→pulled, 94+2→spat | target (QC) 4 |
| -1 2 -3 | up | helper | 81+2→spat | block←observer 1 |
| -1 2 -2 S | up | helper | pulled at 10, 24+48→retracted, pulled at 72, 93+None→held | redstone_block 2 |
| -1 3 -5 | south | helper | 14+2→spat, 20+1→spat, 24+2→spat | observer 3 |
| -1 3 2 | up | helper | 72+0→spat, 75+0→spat, 78+0→spat | block←repeater 3 |
| -1 5 -1 S | north | helper | 72+0→spat, 75+0→pulled | block←wire (QC) 2 |
| -1 6 -1 S | north | helper | 72+0→spat, 75+0→pulled, 78+0→spat | block←wire 3 |
| -1 7 -1 S | north | helper | 72+0→spat, 75+0→pulled | block←wire (QC) 2 |
| -1 8 -1 S | north | helper | 72+0→spat, 75+0→pulled, 78+0→spat | block←wire 3 |
| -1 9 -1 S | north | helper | 72+0→spat, 75+3→pulled | block←wire (QC) 1, block←repeater (QC) 1 |
| -1 12 -2 S | down | helper | pulled at 72, 93+None→held | wire 1 |
| -1 12 2 | down | helper | 10+2→spat, 15+2→spat, 80+2→spat, 85+None→held | target 4 |
| -1 13 -4 | down | helper | 2+0→spat, 7+1→spat, 17+1→spat, 91+2→spat | block←wire 1, target 3 |
| -1 13 3 S | north | helper | 8+2→retracted, pulled at 12, 15+2→spat, 78+2→retracted, pulled at 82, 85+None→held | repeater 2, target 2 |
| 1 1 3 S | south | helper | 2+70→pulled, 75+0→spat | target 1, wire (QC) 1 |
| 1 12 -4 | west | helper | 14+2→spat | observer 1 |
| 1 13 4 S | west | helper | 90+2→spat | observer 1 |
| 3 1 -5 S | west | helper | 74+2→pulled | observer 1 |
| 3 12 3 S | west | helper | 13+4→pulled, 81+4→pulled | repeater (QC) 2 |
| 4 1 -2 S | east | helper | 2+0→pulled, 72+0→spat | target 2 |
| 4 13 -2 S | south | helper | 2+0→pulled, 72+0→spat | wire 2 |
| 5 2 1 S | west | helper | 72+0→spat, 80+2→pulled | target 1, observer 1 |
| 5 2 2 S | west | helper | 2+0→pulled, 72+0→spat | target 2 |
| 6 2 -5 S | west | helper | 4+2→spat, 74+2→pulled | observer 2 |
| 6 13 0 S | north | helper | 4+2→spat, 74+2→pulled | observer 2 |
| 7 1 -4 | up | helper | retracted at 72, 75+2→spat, 81+2→spat, 87+2→spat, 93+None→held | wire (QC) 3, redstone_block 1 |
| 7 1 -2 | up | helper | retracted at 72, 75+1→spat, 81+1→spat, 87+1→spat, 93+None→held | wire (QC) 3, redstone_block 1 |
| 7 2 -3 S | up | helper | pulled at 72, 90+None→held | redstone_block 1 |
| 7 12 -4 | down | helper | 72+2→spat, 78+2→spat, 84+2→spat, 90+2→spat | target 3, observer (QC) 1 |
| 7 12 -3 S | down | helper | pulled at 72, 90+None→held | block←comparator (QC) 1 |
| 7 12 -2 | down | helper | 72+0→spat, 78+2→spat, 84+2→spat, 90+2→spat | target 1, observer 1, observer (QC) 2 |
| 7 12 5 S | west | helper | 2+70→pulled, 86+2→spat | block←wire 2 |
| 8 3 1 S | north | helper | 2+0→spat, 72+0→pulled | target 2 |
| 8 5 0 | up | helper | 9+2→spat, 14+3→retracted, 79+2→spat, 84+3→retracted | block←observer+wire 2, block←repeater 2 |
| 8 12 0 | down | helper | 4+2→spat, 74+2→spat | observer 2 |
| 8 13 -4 S | east | helper | pulled at 72, 82+2→spat, 90+None→held | observer 1, block←comparator 1 |
| 9 8 3 S | south | helper | 10+2→pulled, 75+2→spat | wire 2 |
| 9 12 4 S | west | helper | 2+70→pulled, 75+1→spat | target 1, observer (QC) 1 |
| 10 8 4 S | up | helper | 2+70→pulled, 75+0→spat | target 1, block←observer 1 |
| 11 3 -6 S | up | helper | 10+2→spat, 80+2→pulled | block←wire 2 |
| 11 9 -1 S | south | helper | 72+0→pulled, 75+0→spat, 78+2→pulled, 84+0→spat, 87+0→pulled, 90+0→spat | target 6 |
| 11 13 1 S | north | helper | 6+2→pulled | observer 1 |
| -11 2 2 S | south | power mover | pulled at 2, 5+None→held | redstone_block 1 |
| -11 3 -6 | up | power mover | 2+70→retracted | wire 1 |
| -11 3 -2 | up | power mover | 76+2→spat | observer 1 |
| -11 3 4 S | north | power mover | 2+0→spat, 8+64→pulled | target 2 |
| -11 4 -4 | up | power mover | 8+2→spat, 26+2→spat, 38+2→spat | repeater 3 |
| -11 6 4 S | down | power mover | 12+2→spat, 82+2→pulled | observer 2 |
| -11 6 5 S | east | power mover | 44+2→spat, 52+2→pulled | observer 2 |
| -11 11 -6 | down | power mover | 84+2→spat | block←observer 1 |
| -11 11 -4 | down | power mover | 4+2→spat, 14+2→spat, 32+2→spat, 44+2→spat, 84+2→spat | wire (QC) 3, block←observer 2 |
| -11 11 -2 | down | power mover | 2+70→retracted | target (QC) 1 |
| -11 11 5 S | north | power mover | pulled at 2, 5+67→pulled, 75+None→held | redstone_block 1, redstone_block (QC) 1 |
| -11 12 3 S | south | power mover | 2+0→spat, 8+64→pulled | target 2 |
| -10 3 -6 S | up | power mover | 10+2→spat, 80+2→spat, 88+2→pulled | observer 2, observer (QC) 1 |
| -10 3 -1 S | down | power mover | 32+2→pulled, 88+2→spat | block←observer (QC) 1, observer 1 |
| -10 4 -1 | up | power mover | 35+2→spat, 47+2→spat, 54+2→spat | observer (QC) 4 |
| -10 10 -1 | down | power mover | 30+2→spat, 42+2→spat | block←observer (QC) 2 |
| -10 11 -6 | down | power mover | 5+2→spat, 38+2→spat, 77+2→spat | observer 2, observer (QC) 1 |
| -10 12 -1 S | south | power mover | pulled at 2, 5+67→pulled, 75+None→held | redstone_block 1, redstone_block (QC) 1 |
| -10 13 1 S | north | power mover | 2+0→spat, 8+64→pulled | target 2 |
| -9 2 -4 | up | power mover | 8+0→spat, 29+0→spat, 78+0→spat, 88+0→spat | block←observer (QC) 4 |
| -9 2 4 | up | power mover | 5+0→spat, 11+0→spat, 17+0→spat, 23+0→spat, 29+0→spat, 35+0→spat, 41+0→spat, 47+0→spat, 53+0→spat, 59+0→spat | redstone_block (QC) 10 |
| -9 3 -2 | up | power mover | 8+0→spat, 32+2→spat, 82+0→spat, 88+0→spat | block←observer 3, block←observer (QC) 2 |
| -9 8 1 S | north | power mover | 14+2→pulled, 26+2→spat | observer 2 |
| -9 11 -2 | down | power mover | 28+2→spat, 78+2→spat | observer 1, observer (QC) 1 |
| -9 11 4 | down | power mover | 2+0→spat, 8+0→spat, 14+0→spat, 20+0→spat, 26+0→spat, 32+0→spat, 38+0→spat, 44+0→spat, 50+0→spat, 56+0→spat, 62+None→held | target 11 |
| -9 12 -4 | down | power mover | 4+2→spat, 25+2→spat, 74+2→spat, 84+4→retracted | observer (QC) 3, comparator 1 |
| -9 13 -6 S | west | power mover | 32+2→pulled, 40+2→spat | observer 2 |
| -8 1 -5 | east | power mover | 13+2→spat, 83+2→spat | observer 2 |
| -8 3 0 S | west | power mover | 84+2→spat, 90+2→pulled | observer (QC) 2 |
| -8 4 -6 | up | power mover | 12+2→spat, 40+2→spat, 45+2→spat, 78+2→spat, 92+2→spat | observer (QC) 4, observer 2 |
| -8 11 -6 | down | power mover | 7+2→spat, 75+2→spat, 81+2→spat | bud 2, observer 1 |
| -7 3 -6 | up | power mover | 4+2→spat, 16+0→spat, 26+0→spat, 74+2→spat | block←observer 2, block←observer+wire (QC) 3 |
| -7 9 4 S | up | power mover | 79+2→spat, 85+2→pulled | block←observer 2 |
| -7 11 -6 | down | power mover | 7+2→spat, 22+2→spat | bud (QC) 1, block←wire (QC) 1 |
| -7 13 3 S | north | power mover | 2+70→pulled | wire 1 |
| -7 13 5 S | east | power mover | 2+70→pulled | wire 1 |
| -6 1 -2 S | east | power mover | 8+2→pulled, 20+2→spat, 40+32→pulled, 89+2→spat | observer 3, block←wire 1 |
| -6 3 -6 | up | power mover | 82+2→spat | block←observer (QC) 1 |
| -6 3 -4 | up | power mover | 20+0→spat, 38+0→spat | block←observer (QC) 2 |
| -6 3 1 | up | power mover | 11+1→spat, 81+7→retracted, 99+None→held | block←observer (QC) 2, block←wire 1 |
| -6 3 4 S | up | power mover | 72+0→spat, 75+1→pulled, 98+None→held | block←repeater (QC) 2, observer (QC) 1 |
| -6 7 -5 S | south | power mover | 85+5→pulled | block←comparator 1 |
| -6 9 -5 S | south | power mover | 85+5→pulled | block←comparator 1 |
| -6 10 1 | down | power mover | 75+2→spat, 93+2→spat | block←observer 2 |
| -6 11 -6 | down | power mover | 9+2→spat, 77+2→spat, 90+2→spat | observer (QC) 2, block←observer (QC) 1 |
| -6 11 -4 | down | power mover | 16+2→spat, 34+2→spat | wire (QC) 2 |
| -5 3 -4 | up | power mover | 14+0→spat, 32+0→spat | block←observer (QC) 2 |
| -5 3 1 | up | power mover | 15+0→spat, 22+0→spat, 83+0→spat, 90+0→spat | block←observer (QC) 4 |
| -5 5 -5 S | south | power mover | 74+2→spat, 79+1→pulled, 83+1→spat, 87+0→pulled, 94+2→spat | block←wire (QC) 5 |
| -5 5 3 S | down | power mover | 13+2→spat, 18+1→pulled, 22+2→spat, 27+1→pulled, 72+0→spat, 78+0→pulled, 81+2→spat, 86+1→pulled, 90+2→spat, 95+1→pulled, 99+None→held | wire 11 |
| -5 7 -5 S | south | power mover | 74+2→spat, 79+1→pulled, 83+1→spat, 87+0→pulled, 90+2→spat, 95+1→pulled | block←wire (QC) 6 |
| -5 9 -5 S | south | power mover | 74+2→spat, 79+1→pulled, 83+1→spat, 87+0→pulled, 90+2→spat, 95+1→pulled | block←wire (QC) 6 |
| -5 11 -4 | down | power mover | 10+2→spat, 28+2→spat | observer (QC) 2 |
| -5 11 1 | down | power mover | 11+2→spat, 18+2→spat, 79+2→spat, 86+4→retracted | observer 2, repeater (QC) 2 |
| -5 13 -2 S | east | power mover | pulled at 72, 91+2→spat, 96+None→held | observer 1, block←repeater 1 |
| -4 1 -5 | west | power mover | 16+4→retracted, 87+0→spat, 90+2→spat | block←repeater (QC) 2, block←observer (QC) 1 |
| -4 2 5 S | east | power mover | pulled at 2, 5+67→pulled, 75+None→held | redstone_block 1, redstone_block (QC) 1 |
| -4 3 4 | up | power mover | 2+70→retracted, 97+0→spat | redstone_block 1, block←observer (QC) 1 |
| -4 5 5 | up | power mover | 10+0→spat, 76+2→spat, 86+2→spat, 100+None→held | block←observer (QC) 2, block←observer 2 |
| -4 11 5 | down | power mover | 6+2→spat, 94+2→spat | observer (QC) 1, wire (QC) 1 |
| -4 12 4 | down | power mover | 93+3→retracted | observer (QC) 1 |
| -3 1 -2 S | east | power mover | pulled at 10, 14+2→spat, 22+50→pulled, 75+1→spat, 91+None→held | observer (QC) 2, redstone_block 2 |
| -3 1 -1 S | west | power mover | 18+2→spat, 24+2→pulled, 72+0→spat, 75+0→pulled, 78+0→spat, 82+4→pulled, 89+1→spat, 94+2→pulled, 99+None→held | bud 5, block←wire (QC) 4 |
| -3 13 -5 S | west | power mover | 78+2→pulled, 95+2→spat | observer 2 |
| -2 3 -6 | up | power mover | 16+4→retracted, 74+2→spat, 79+1→spat, 83+1→spat, 87+0→spat, 90+2→spat, 95+1→spat | block←wire 7 |
| -2 3 5 S | west | power mover | 2+0→spat, 8+64→pulled | target 2 |
| -2 5 5 | up | power mover | 80+0→spat, 97+0→spat | block←observer (QC) 2 |
| -2 8 1 S | down | power mover | 14+2→pulled, 20+2→spat, 25+1→pulled, 29+1→spat, 33+1→pulled, 38+2→spat, 100+2→spat | observer 7 |
| -2 8 2 S | down | power mover | 84+3→pulled | block←observer (QC) 1 |
| -2 11 -6 | down | power mover | 26+2→spat | observer 1 |
| -2 11 5 | down | power mover | 76+2→spat, 92+2→retracted, retracted at 96 | block←observer (QC) 2 |
| -2 13 5 | west | power mover | 89+6→retracted | repeater 1 |
| -1 1 -6 S | up | power mover | 6+2→spat, 11+1→pulled | block←observer 1, observer (QC) 1 |
| 1 2 5 S | east | power mover | 2+70→pulled | target 1 |
| 2 1 5 S | east | power mover | pulled at 2, 5+67→pulled, 75+None→held | redstone_block (QC) 1, redstone_block 1 |
| 2 12 -2 S | south | power mover | 2+0→pulled, 72+0→spat | block←wire 2 |
| 3 1 -2 S | north | power mover | 2+0→pulled, 72+0→spat | target 2 |
| 3 1 1 S | east | power mover | 6+2→pulled, 76+2→spat | block←observer 2 |
| 3 2 0 S | east | power mover | 6+2→spat, 76+2→pulled | block←observer 2 |
| 3 2 3 S | west | power mover | 8+2→pulled, 78+2→spat | block←observer 2 |
| 4 1 -3 S | north | power mover | 2+0→spat, 72+0→pulled | target (QC) 2 |
| 4 13 -5 S | west | power mover | 4+2→spat, 74+2→pulled | repeater 2 |
| 5 2 5 S | east | power mover | 2+0→spat, 72+0→spat | redstone_block 2 |
| 5 12 3 S | east | power mover | 2+0→spat, 6+4→pulled, 72+0→spat, 76+4→pulled | target (QC) 2, repeater 2 |
| 6 1 3 S | east | power mover | 6+2→pulled, 76+2→spat | observer (QC) 2 |
| 7 1 5 S | west | power mover | pulled at 2, 5+67→pulled, 75+None→held | observer 2 |
| 7 11 3 S | east | power mover | pulled at 2, 5+67→pulled, 75+None→held | observer 2 |
| 8 3 -6 | up | power mover | 17+0→spat, 23+0→spat, 78+0→spat, 87+0→spat, 93+0→spat | redstone_block (QC) 5 |
| 8 11 -6 | down | power mover | 14+2→spat, 20+2→spat, 75+2→spat, 84+2→spat, 90+2→spat | block←wire 4, block←wire (QC) 1 |
| 8 13 4 S | north | power mover | 6+2→spat, 76+2→pulled | observer 2 |
| 9 1 -3 S | west | power mover | 2+70→pulled, 88+2→spat | redstone_block 1, observer 1 |
| 9 1 0 S | north | power mover | 2+0→spat, 72+0→pulled | block←wire 2 |
| 9 2 5 S | west | power mover | 2+0→spat, 6+2→pulled, 72+0→spat, 76+2→pulled | target (QC) 2, repeater 2 |
| 9 3 -6 | up | power mover | 78+0→spat, 90+0→spat | redstone_block (QC) 2 |
| 9 3 -2 | up | power mover | 15+2→spat, 23+2→spat, 85+2→spat, 93+2→spat | observer (QC) 4 |
| 9 4 4 S | east | power mover | 2+0→spat, 72+0→pulled | target 2 |
| 9 11 -6 | down | power mover | 75+2→spat, 87+3→retracted | block←wire 2 |
| 9 11 -2 | down | power mover | 4+2→spat, 20+2→spat, 72+0→spat, 75+1→spat, 90+2→spat | observer 2, repeater 2, target (QC) 1 |
| 9 12 3 S | west | power mover | 2+0→spat, 72+0→spat | redstone_block 2 |
| 10 3 -6 | up | power mover | 21+3→retracted, 78+0→spat, 82+2→spat, 87+1→spat, 93+3→retracted, 99+None→held | redstone_block (QC) 3, observer (QC) 2, block←observer 1 |
| 10 11 -6 | down | power mover | 17+2→spat, 75+2→spat, 90+2→spat | block←observer 2, block←wire 3 |
| 11 1 -6 S | west | power mover | 10+2→spat, 80+2→pulled | block←wire 2 |
| 11 2 -2 | up | power mover | 4+2→spat, 74+2→spat | observer 2 |
| 11 2 0 S | up | power mover | 72+0→spat, 75+0→spat, 78+0→spat, 81+0→spat, 84+0→spat, 87+0→spat, 90+0→spat | wire (QC) 7 |
| 11 2 4 S | north | power mover | 4+68→pulled, 75+1→spat | block←observer 2 |
| 11 5 -4 | up | power mover | 17+67→retracted, 87+1→spat, 91+1→spat | observer 3 |
| 11 5 0 S | down | power mover | 72+0→spat, 75+0→spat, 78+0→spat, 81+0→spat, 84+0→spat, 87+0→spat, 90+0→spat | block←wire (QC) 7 |
| 11 9 2 S | down | power mover | 4+2→pulled, 74+2→spat | block←observer 2 |
| 11 10 2 S | west | power mover | 2+70→pulled | bud (QC) 1 |
| 11 11 -4 | down | power mover | 13+2→retracted, retracted at 17, 89+None→held | repeater (QC) 1, block←repeater+wire 1, block←wire 1 |
| 11 11 -2 | down | power mover | 86+4→retracted | repeater 1 |
| 11 11 2 S | up | power mover | 2+70→pulled | bud 1 |
| -6 2 0 | south | power switch | 72+0→spat, 75+0→spat, 78+0→spat, 81+2→spat, 93+0→spat | block←wire 5 |
| -6 2 3 S | north | power switch | 72+0→spat, 75+0→spat, 78+0→spat, 91+2→spat, 102+None→held | block←wire (QC) 4, block←observer 1 |
| -6 6 5 | up | power switch | 72+0→spat, 77+2→spat, 82+1→spat, 98+0→spat | block←comparator (QC) 2, repeater (QC) 2 |
| -6 10 5 | down | power switch | 2+70→retracted, 83+2→spat | bud 1, block←observer (QC) 1 |
| -6 13 0 S | north | power switch | 2+70→pulled, 93+2→spat | target 1, block←observer 1 |
| -4 1 1 | up | power switch | 24+2→spat, 29+1→spat, 33+1→spat, 37+1→spat, 84+2→spat, 90+2→spat, 95+1→spat, 99+1→spat, 103+1→spat, 107+2→spat | observer (QC) 8, observer 2 |
| -4 5 3 S | east | power switch | 97+0→spat | block←observer 1 |
| -4 10 1 | down | power switch | 4+2→spat, 9+2→spat, 14+1→spat, 19+2→spat, 74+2→spat, 79+4→retracted, 87+2→spat | observer (QC) 2, block←repeater (QC) 2, observer 3 |
| -2 4 1 | south | power switch | 24+2→spat, 32+2→spat | observer (QC) 3 |
| -2 5 -5 S | south | power switch | 16+4→retracted, 78+2→spat, 83+1→pulled, 94+2→spat | target (QC) 5 |
| -1 2 1 S | south | power switch | 72+0→spat, 75+0→spat, 78+0→spat | target 3 |
| -1 2 4 S | north | power switch | 72+0→spat, 75+0→spat, 78+0→spat, 96+2→spat | block←wire 3, block←observer 1 |
| -1 12 -1 | down | power switch | 2+0→spat | wire 1 |
| 8 13 -1 S | north | power switch | 2+70→pulled, 88+2→spat | target 1, observer 1 |
| -10 5 -5 S | south | stack | 4+1→spat, 13+25→pulled | target (QC) 2, target 1 |
| -10 5 -3 S | east | stack | 35+0→pulled, 47+0→spat | block←wire (QC) 2 |
| -10 6 -5 S | south | stack | 4+1→spat, 13+25→pulled | target 2 |
| -10 6 -3 S | east | stack | 35+0→pulled, 47+0→spat | block←wire 2 |
| -10 7 -5 S | south | stack | 4+1→spat, 13+25→pulled | target (QC) 2 |
| -10 7 -3 S | east | stack | 35+0→pulled, 47+0→spat | wire 2 |
| -10 8 -5 S | south | stack | 4+1→spat, 13+25→pulled | target 2 |
| -10 8 -3 S | east | stack | 35+0→pulled, 47+0→spat | block←observer+wire 2 |
| -10 9 -5 S | south | stack | 4+1→spat, 13+25→pulled | target (QC) 2 |
| -10 9 -3 S | east | stack | 35+0→pulled, 47+0→spat | wire 2 |
| -8 3 1 S | east | stack | 8+4→retracted, 16+2→pulled, 78+4→retracted, 90+2→pulled, 96+4→retracted | repeater (QC) 3, observer 2 |
| -8 3 3 S | up | stack | 5+0→spat, 56+0→pulled | block←wire (QC) 4 |
| -8 4 3 S | down | stack | pulled at 2, 11+0→spat, 50+0→pulled, 59+0→spat, 62+None→held | block←wire 7 |
| -8 5 -5 S | south | stack | 11+1→spat, 85+2→spat, 96+2→pulled | observer 2, observer (QC) 1 |
| -8 5 -3 S | east | stack | 32+0→pulled | block←observer 1 |
| -8 5 3 S | down | stack | 8+0→pulled, 17+0→spat, 44+0→pulled, 53+0→spat, 56+None→held | block←wire (QC) 8 |
| -8 6 -3 S | east | stack | 32+0→pulled | block←observer (QC) 1 |
| -8 6 3 S | down | stack | 14+0→pulled, 23+0→spat, 38+0→pulled, 47+0→spat, 50+None→held | block←wire 8 |
| -8 7 -3 S | east | stack | 32+0→pulled | block←observer 1 |
| -8 7 3 S | down | stack | 20+0→pulled, 29+0→spat, 32+0→pulled, 41+0→spat, 44+None→held | block←wire (QC) 7 |
| -8 8 -3 S | east | stack | 32+0→pulled | block←observer (QC) 1 |
| -8 8 3 S | down | stack | 26+0→pulled, 35+0→spat, 38+None→held | block←wire 4 |
| -8 9 -3 S | east | stack | 32+0→pulled | block←observer 1 |
| -7 5 -2 S | east | stack | 81+2→spat, 93+0→spat, 105+None→held | block←wire 3 |
| -6 3 -1 | up | stack | 22+2→spat, 40+2→spat | repeater (QC) 2 |
| -6 8 0 S | north | stack | 78+3→retracted, 84+9→pulled, 96+3→pulled, 102+None→held | redstone_block 2, block←comparator 2 |
| -6 11 -1 | down | stack | 72+2→spat, 93+2→spat | wire 2 |
| -5 3 -1 | up | stack | 22+4→retracted, 75+0→spat, 80+2→spat, 92+2→spat, 98+2→spat, 103+2→spat | block←observer 6 |
| -5 5 -1 S | east | stack | 86+1→spat, 98+2→spat | block←observer 3 |
| -5 6 -2 S | east | stack | 86+1→spat, 90+3→pulled, 98+2→spat | block←observer 3, block←observer (QC) 1 |
| -5 6 -1 S | east | stack | 78+2→spat, 86+1→pulled, 94+2→spat | block←observer (QC) 3 |
| -5 7 -1 S | east | stack | 78+2→spat, 86+1→pulled, 94+2→spat | block←observer 3 |
| -5 8 -2 S | east | stack | 86+1→spat, 90+3→pulled, 96+None→held | block←observer 2, block←observer (QC) 1 |
| -5 8 0 S | north | stack | 83+0→spat, 90+0→spat | observer (QC) 2 |
| -5 9 -1 S | east | stack | 78+2→spat, 86+1→pulled | block←observer 2 |
| -5 11 -1 | down | stack | 72+2→spat, 93+2→spat | target 2 |
| -4 2 -1 | up | stack | 22+4→retracted, 30+2→spat, 92+2→spat, 98+2→spat, 103+2→spat | block←observer 6, observer 1 |
| -4 6 -2 S | east | stack | 78+2→spat, 96+None→held | block←observer (QC) 2 |
| -4 6 0 S | north | stack | 75+0→spat, 96+None→held | block←wire (QC) 1, block←repeater (QC) 1 |
| -4 8 -2 S | east | stack | 78+2→spat, 96+None→held | block←observer (QC) 2 |
| -4 8 0 S | north | stack | 75+0→spat, 87+0→spat, 93+None→held | block←wire (QC) 1, block←repeater (QC) 2 |
| -4 11 -1 | down | stack | 8+2→spat, 72+2→spat, 78+2→spat, 91+2→retracted, retracted at 95 | block←repeater 2, target (QC) 1, block←observer 1 |
| -3 1 3 | up | stack | 78+2→spat, 84+2→spat, 104+None→held | observer 2, block←wire (QC) 1 |
| -3 2 -2 S | east | stack | 14+2→pulled, 22+2→spat, 28+2→spat, 41+2→spat, 74+2→pulled, 91+2→spat, 96+2→spat, 102+2→spat, 107+2→spat | observer 9 |
| -3 3 -1 | up | stack | 78+2→spat, 84+2→spat, 89+1→spat, 93+3→retracted | block←repeater 2, block←observer 2 |
| -3 5 -1 S | east | stack | 72+0→spat, 75+0→spat | block←wire 3 |
| -3 5 4 S | east | stack | 97+0→spat | block←observer 1 |
| -3 5 5 S | north | stack | 10+0→pulled, 100+None→held | observer (QC) 2 |
| -3 6 -1 S | east | stack | 72+0→spat | block←wire (QC) 2 |
| -3 6 5 S | north | stack | 10+0→pulled | observer 1 |
| -3 7 -1 S | east | stack | 72+0→spat, 75+0→spat | block←wire 2 |
| -3 7 5 S | north | stack | 10+0→pulled, 98+2→spat, 103+1→pulled | block←observer 3 |
| -3 8 -1 S | east | stack | 72+0→spat | block←wire (QC) 2 |
| -3 8 5 S | north | stack | 10+0→pulled | observer (QC) 1 |
| -3 9 -1 S | east | stack | 72+0→spat, 75+0→spat | block←wire 2 |
| -3 9 5 S | north | stack | 10+0→pulled, 97+1→retracted, pulled at 100 | observer 1, observer (QC) 1 |
| -3 11 3 | down | stack | 11+1→spat, 17+1→spat, 23+1→spat, 29+1→spat, 35+1→spat, 75+2→spat, 81+1→spat, 94+2→spat | target 3, wire (QC) 4, block←observer+wire (QC) 1 |
| -2 2 -3 | up | stack | 81+2→spat | block←observer 1 |
| -2 4 -1 | up | stack | 78+2→spat, 84+2→spat, 89+1→spat, 93+3→retracted | block←repeater 2, block←observer 2 |
| -2 6 4 S | north | stack | 80+0→pulled, 96+1→spat | observer 2 |
| -2 7 4 S | north | stack | 80+0→pulled, 96+1→spat | block←observer 2 |
| -2 8 4 S | north | stack | 80+0→pulled, 96+1→spat | observer (QC) 2 |
| -2 9 4 S | north | stack | 76+3→retracted, pulled at 81, 96+1→spat | block←wire (QC) 1, observer 1 |
| -1 2 -1 | up | stack | 10+3→retracted, 23+1→spat, 93+3→retracted | block←repeater (QC) 1, block←observer (QC) 2, block←observer 1 |
| -1 3 0 S | south | stack | 18+2→spat, 84+2→pulled, 89+1→spat | observer 3 |
| 0 2 -5 S | south | stack | 9+2→pulled, 79+2→spat | block←wire 2 |
| 0 13 -5 S | south | stack | 16+2→spat, 86+2→pulled | block←wire 2 |
| 1 2 -5 S | south | stack | 9+2→pulled, 79+2→spat | wire 2 |
| 1 12 -1 S | north | stack | 19+2→pulled, 87+2→spat | comparator 2 |
| 1 13 -5 S | south | stack | 16+2→spat, 86+2→pulled | wire 2 |
| 3 12 -4 S | west | stack | 4+2→spat, 74+2→pulled | observer 2 |
| 8 3 -4 | up | stack | 5+2→spat, 18+2→spat, 75+2→spat, 90+1→spat | observer 4 |
| 8 11 -4 | down | stack | 15+2→spat, 72+2→spat, 87+2→spat | wire (QC) 3 |
| 9 3 -4 | up | stack | 18+2→spat, 23+1→spat, 89+2→spat, 94+1→spat | observer 4 |
| 9 11 -4 | down | stack | 15+2→spat, 72+2→spat, 87+2→spat | block←wire 2, block←repeater+wire 1 |
| 10 3 -4 | up | stack | 18+2→spat, 89+2→spat | observer 2 |
| 10 5 -5 S | south | stack | 21+0→spat, 24+51→pulled, 78+0→spat, 81+9→pulled | redstone_block 2, redstone_block (QC) 2 |
| 10 6 -5 S | south | stack | 21+0→spat, 24+51→pulled, 78+0→spat, 81+9→pulled | redstone_block (QC) 2, redstone_block 2 |
| 10 7 -5 S | south | stack | 21+0→spat, 24+51→pulled, 78+0→spat, 81+9→pulled | redstone_block 2, redstone_block (QC) 2 |
| 10 8 -5 S | south | stack | 21+0→spat, 24+51→pulled, 78+0→spat, 81+9→pulled | redstone_block (QC) 2, redstone_block 2 |
| 10 9 -5 S | south | stack | 21+0→spat, 24+51→pulled, 78+0→spat, 81+9→pulled | redstone_block (QC) 3, redstone_block 2 |
| 10 10 -4 | down | stack | 15+2→spat | block←wire 1 |

<!-- end generated -->
