"""The tutorial world: one small station per lesson (``redsim.tutorial.lessons``), each on
its own stone square with signs, laid out in three rows of three. The camera looks south,
so east (+x, the inputs) is on the left of the screen. Built in code each time the
tutorial starts (an untitled document: the user's files are never touched).
"""

from __future__ import annotations

from redsim.core.pos import Pos
from redsim.editor.builder import LOOK_EAST_LEVEL, LOOK_WEST, ON_EAST_FACE, ON_WEST_FACE, Builder
from redsim.editor.document import Document
from redsim.world import blocks

#: Marks a document as the tutorial world (``Document.extra``).
TUTORIAL_KEY = "tutorial"
#: Station origins (x, z) in lesson order: east to west, then the next row south.
STATIONS: tuple[tuple[int, int], ...] = tuple((x, z) for z in (0, 16, 32) for x in (30, 15, 0))
#: A station's stone square, relative to its origin (x0, z0, x1, z1).
PAD = (-1, -3, 12, 11)


def station(index: int, pos: Pos) -> Pos:
    """World position of ``pos`` relative to station ``index`` (0-based)."""
    x, z = STATIONS[index]
    return (x + pos[0], pos[1], z + pos[2])


def station_center(index: int) -> tuple[float, float, float]:
    x, z = STATIONS[index]
    return (x + 5.5, 1.0, z + 4.5)


#: Positions the lessons check, by name (relative to their station).
LOOK_LAMP = (5, 1, 4)  # station 1: the lamp to focus with F
USE_LEVER, USE_LAMP = (8, 1, 2), (7, 1, 2)  # station 2
USE_REPEATER = (7, 1, 6)
TIME_LEVER, TIME_LAMP = (9, 1, 4), (4, 1, 4)  # station 3
BUILD_LEVER, BUILD_LAMP = (9, 1, 4), (2, 1, 4)  # station 4: connect them with dust
BUILD_AREA = ((1, 1, 1), (10, 3, 8))
SELECT_LEVER, SELECT_LAMP = (9, 1, 2), (6, 1, 2)  # station 5: the inverter to copy
SELECT_AREA = ((0, 1, 0), (11, 3, 9))
SEQ_PISTON, SEQ_PLANKS = (8, 1, 3), (7, 1, 3)  # station 6
SEQ_LAMPS = ((8, 1, 6), (6, 1, 6), (4, 1, 6))
SEQ_LEVER, SEQ_LEVER_LAMP = (9, 1, 8), (8, 1, 8)
SEE_BARREL, SEE_LAMP = (10, 1, 3), (1, 1, 3)  # station 7
WHY_LEVER, WHY_LAMP = (10, 1, 7), (5, 1, 7)
ORG_LEVER, ORG_LAMP = (8, 1, 3), (6, 1, 3)  # station 8


def build() -> Document:
    """The tutorial world, settled, at tick 0, camera over the first station."""
    pads = []
    for x, z in STATIONS:
        x0, z0, x1, z1 = PAD
        pads.append(((x + x0, z + z0, x + x1, z + z1), "minecraft:smooth_stone"))
    b = Builder((-8, -10), (50, 48), "minecraft:grass_block", pads)
    for index, build_station in enumerate(_BUILDERS):
        x, z = STATIONS[index]
        b.origin = (x, 0, z)
        build_station(b)
    b.settle(10)
    doc = b.doc
    doc.extra[TUTORIAL_KEY] = True
    pivot = list(station_center(0))
    doc.extra["camera"] = {"pivot": pivot, "distance": 20.0, "yaw": 0.0, "pitch": 40.0}
    doc.dirty = False
    return doc


def is_tutorial(doc: Document) -> bool:
    return bool(doc.extra.get(TUTORIAL_KEY))


# ------------------------------------------------------------------ stations
def _look(b: Builder) -> None:
    b.set((5, 0, 4), "minecraft:redstone_block")  # in the floor: the lamp above is lit
    b.place(LOOK_LAMP, blocks.REDSTONE_LAMP)
    b.sign((10, 1, 0), "1  LOOK AROUND", "The card at the", "top right says", "what to do")
    b.sign((1, 1, 0), "Point at the", "lamp and press F:", "the camera turns", "around it")


def _use(b: Builder) -> None:
    b.place(USE_LEVER, blocks.LEVER)
    b.place(USE_LAMP, blocks.REDSTONE_LAMP)
    b.place((8, 1, 6), blocks.LEVER)
    b.place(USE_REPEATER, blocks.REPEATER, LOOK_WEST)
    b.place((6, 1, 6), blocks.REDSTONE_LAMP)
    b.sign((10, 1, 0), "2  USE", "Right-click to", "use, left-click", "to inspect")


def _time(b: Builder) -> None:
    b.place(TIME_LEVER, blocks.LEVER)
    for x in (8, 7, 6):
        b.place((x, 1, 4), blocks.REDSTONE_WIRE)
    b.place((5, 1, 4), blocks.REPEATER, LOOK_WEST)
    b.use((5, 1, 4))  # delay 2: 4 game ticks
    b.place(TIME_LAMP, blocks.REDSTONE_LAMP)
    b.sign((11, 1, 0), "3  TIME", "Run, pause, step", "and rewind")


def _build(b: Builder) -> None:
    for x in range(1, 11):
        for z in range(1, 9):
            b.set((x, 0, z), "minecraft:white_concrete")
    b.place(BUILD_LEVER, blocks.LEVER)
    b.place(BUILD_LAMP, blocks.REDSTONE_LAMP)
    b.sign((11, 1, 0), "4  BUILD", "Connect the", "lever and the", "lamp with dust")


def _select(b: Builder) -> None:
    b.solid((8, 1, 2))
    b.place(SELECT_LEVER, blocks.LEVER, ON_EAST_FACE)
    b.place((7, 1, 2), blocks.REDSTONE_TORCH, ON_WEST_FACE)
    b.place(SELECT_LAMP, blocks.REDSTONE_LAMP)
    b.sign((11, 1, 0), "5  SELECT", "Copy this", "inverter into", "the free space")


def _sequence(b: Builder) -> None:
    b.place(SEQ_PISTON, blocks.STICKY_PISTON, LOOK_EAST_LEVEL)
    b.solid(SEQ_PLANKS, blocks.OAK_PLANKS)
    for lamp in SEQ_LAMPS:
        b.place(lamp, blocks.REDSTONE_LAMP)
    b.place(SEQ_LEVER, blocks.LEVER)
    b.place(SEQ_LEVER_LAMP, blocks.REDSTONE_LAMP)
    b.sign((11, 1, 0), "6  SEQUENCES", "Edits and pulses", "at chosen ticks")


def _see(b: Builder) -> None:
    b.source(SEE_BARREL, "barrel", 12)
    b.place((9, 1, 3), blocks.COMPARATOR, LOOK_WEST)
    for x in range(2, 9):
        b.place((x, 1, 3), blocks.REDSTONE_WIRE)
    b.place(SEE_LAMP, blocks.REDSTONE_LAMP)
    b.place(WHY_LEVER, blocks.LEVER)
    for x in (9, 8):
        b.place((x, 1, 7), blocks.REDSTONE_WIRE)
    b.place((7, 1, 7), blocks.REPEATER, LOOK_WEST)
    b.place((6, 1, 7), blocks.REDSTONE_WIRE)
    b.place(WHY_LAMP, blocks.REDSTONE_LAMP)
    b.sign((11, 1, 0), "7  SEE INSIDE", "Signal values,", "heat, x-ray and", "causes")


def _organize(b: Builder) -> None:
    b.place(ORG_LEVER, blocks.LEVER)
    b.place((7, 1, 3), blocks.REDSTONE_WIRE)
    b.place(ORG_LAMP, blocks.REDSTONE_LAMP)
    b.sign((11, 1, 0), "8  ORGANIZE", "Sections, groups,", "prefabs, signs", "and markers")


def _files(b: Builder) -> None:
    b.sign((10, 1, 0), "9  FILES", "Save, open, and", "Minecraft worlds")
    b.sign((6, 1, 4), "Thanks for", "following along!", "Next: File > Open", "> the showcase")


_BUILDERS = (_look, _use, _time, _build, _select, _sequence, _see, _organize, _files)
