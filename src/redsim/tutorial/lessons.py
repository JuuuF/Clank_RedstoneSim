"""The tutorial's lessons: steps with a text and, for most, a check that notices when the
user has done what the step asks.

Checks look at a ``Snapshot`` of the editor (taken by the window a few times a second)
and at a step's ``memo`` (a dict that lives as long as the step; ``memo["start"]`` is the
snapshot from when the step began). This module knows nothing about Qt, so lessons can be
tested with plain snapshots. Texts name keys as ``{key:action.id}`` (shown with the
user's own binding) or ``{cap:Right Click}`` (shown as a keycap as written).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from redsim.core.pos import Pos
from redsim.editor import sources
from redsim.editor.clipboard import Region
from redsim.editor.document import Document
from redsim.tutorial import world as tw
from redsim.world import blocks
from redsim.world.blocks.sign import SignBlockEntity
from redsim.world.properties import DELAY, LIT

Memo = dict[str, Any]
Check = Callable[["Snapshot", Memo], bool]


@dataclass(frozen=True)
class Snapshot:
    """What the tutorial can see of the editor at one moment."""

    doc: Document
    mode: str = "normal"
    tick: int = 0
    running: bool = False
    inspected: Pos | None = None
    regions: tuple[Region, ...] = ()
    pivot: tuple[float, float, float] = (0.0, 0.0, 0.0)
    yaw: float = 0.0
    pitch: float = 0.0
    distance: float = 20.0
    pasting: bool = False
    confirmed: bool = False  # the selection is confirmed (Enter)
    heat: bool = False
    xray: int = 0
    info: bool = False
    popup: bool = False
    #: The side panel's tab and sub-tab ("Diagnostics/Why?", "Inspector", …).
    tab: str = ""
    build_block: str | None = None
    undo: tuple[str, ...] = ()
    redo: int = 0
    saves: int = 0  # worlds saved so far
    world_screens: int = 0  # Select World screens opened so far


@dataclass(frozen=True)
class Step:
    title: str
    text: str
    check: Check | None = None  # None: the user presses Next
    #: Where the camera goes when the step starts (a station's center), if anywhere.
    focus: tuple[float, float, float] | None = None


@dataclass(frozen=True)
class Lesson:
    title: str
    station: int  # index into ``tutorial.world.STATIONS``
    steps: tuple[Step, ...]


# ------------------------------------------------------------------ helpers
def lit(snap: Snapshot, station: int, pos: Pos) -> bool:
    return bool(snap.doc.state_at(tw.station(station, pos)).get(LIT))


def count_in(snap: Snapshot, station: int, area: tuple[Pos, Pos], block_id: str) -> int:
    low, high = (tw.station(station, p) for p in area)
    return sum(
        1
        for pos, state in snap.doc.level.blocks.items()
        if low[0] <= pos[0] <= high[0]
        and low[1] <= pos[1] <= high[1]
        and low[2] <= pos[2] <= high[2]
        and state.block.id == block_id
    )


def start(memo: Memo) -> Snapshot:
    snapshot: Snapshot = memo["start"]
    return snapshot


def changed_by(a: float, b: float, amount: float) -> bool:
    return abs(a - b) >= amount


def remember(memo: Memo, key: str, value: bool) -> bool:
    """``value``, remembered once true (for steps with several parts)."""
    memo[key] = memo.get(key, False) or value
    return bool(memo[key])


def last_edit(snap: Snapshot) -> str:
    return snap.undo[0] if snap.undo else ""


def new_edit(snap: Snapshot, memo: Memo, *words: str) -> bool:
    """An undo step was added since the step began whose label has one of ``words``."""
    if len(snap.undo) <= len(start(memo).undo) and snap.undo == start(memo).undo:
        return False
    label = last_edit(snap).lower()
    return any(word in label for word in words)


def recorded(snap: Snapshot, kind: str, pos: Pos | None = None) -> int:
    """Recorded edits (after tick 0) of ``kind`` (at ``pos``)."""
    return sum(
        1
        for action in snap.doc.history.inputs.values()
        if action.kind == kind and (pos is None or action.pos == pos)
    )


def signs_with_text(snap: Snapshot) -> int:
    return sum(
        1
        for entity in snap.doc.level.block_entities.values()
        if isinstance(entity, SignBlockEntity) and any(line.strip() for line in entity.front)
    )


def section_count(snap: Snapshot) -> int:
    return sum(len(section.positions) for section in snap.doc.sections.sections.values())


def contains(regions: tuple[Region, ...], *positions: Pos) -> bool:
    return any(all(region.contains(pos) for pos in positions) for region in regions)


# ------------------------------------------------------------------ checks
def _orbited(snap: Snapshot, memo: Memo) -> bool:
    first = start(memo)
    return changed_by(snap.yaw, first.yaw, 25) or changed_by(snap.pitch, first.pitch, 15)


def _zoomed(snap: Snapshot, memo: Memo) -> bool:
    return changed_by(snap.distance, start(memo).distance, 4)


def _panned(snap: Snapshot, memo: Memo) -> bool:
    (x, _, z), (x0, _, z0) = snap.pivot, start(memo).pivot
    return abs(x - x0) + abs(z - z0) >= 3


def _focused_lamp(snap: Snapshot, memo: Memo) -> bool:
    lamp = tw.station(0, tw.LOOK_LAMP)
    return all(abs(snap.pivot[i] - (lamp[i] + 0.5)) < 0.6 for i in range(3))


def _lamp_on(station: int, pos: Pos) -> Check:
    return lambda snap, memo: lit(snap, station, pos)


def _inspected(station: int, pos: Pos) -> Check:
    return lambda snap, memo: snap.inspected == tw.station(station, pos)


def _repeater_delay(snap: Snapshot, memo: Memo) -> bool:
    state = snap.doc.state_at(tw.station(1, tw.USE_REPEATER))
    return state.is_(blocks.REPEATER) and state.get(DELAY) != 1


def _ran_and_paused(snap: Snapshot, memo: Memo) -> bool:
    return remember(memo, "ran", snap.running) and not snap.running


def _stepped_to_lamp(snap: Snapshot, memo: Memo) -> bool:
    return snap.tick > 0 and lit(snap, 2, tw.TIME_LAMP)


def _stepped_back(snap: Snapshot, memo: Memo) -> bool:
    memo["max"] = max(memo.get("max", start(memo).tick), snap.tick)
    return snap.tick < memo["max"] and not snap.running


def _at_tick_zero(snap: Snapshot, memo: Memo) -> bool:
    return snap.tick == 0 and (start(memo).tick > 0 or remember(memo, "away", snap.tick > 0))


def _scrubbed(snap: Snapshot, memo: Memo) -> bool:
    last = memo.get("last", start(memo).tick)
    memo["last"] = snap.tick
    return not snap.running and abs(snap.tick - last) >= 3


def _mode(mode: str) -> Check:
    return lambda snap, memo: snap.mode == mode


def _chose(block_id: str) -> Check:
    return lambda snap, memo: snap.build_block == block_id


def _dust_placed(snap: Snapshot, memo: Memo) -> bool:
    return count_in(snap, 3, tw.BUILD_AREA, "minecraft:redstone_wire") >= 3


def _build_lamp(snap: Snapshot, memo: Memo) -> bool:
    return lit(snap, 3, tw.BUILD_LAMP)


def _removed(snap: Snapshot, memo: Memo) -> bool:
    return new_edit(snap, memo, "break")


def _turned(snap: Snapshot, memo: Memo) -> bool:
    return new_edit(snap, memo, "set ")


def _undone(snap: Snapshot, memo: Memo) -> bool:
    return snap.redo > start(memo).redo


def _wool_variant(snap: Snapshot, memo: Memo) -> bool:
    block = snap.build_block or ""
    return block.endswith("_wool_stairs") or block.endswith("_wool_slab")


def _layer_moved(snap: Snapshot, memo: Memo) -> bool:
    return changed_by(snap.pivot[1], start(memo).pivot[1], 1)


def _boxed_inverter(snap: Snapshot, memo: Memo) -> bool:
    return contains(snap.regions, tw.station(4, tw.SELECT_LEVER), tw.station(4, tw.SELECT_LAMP))


def _copied(snap: Snapshot, memo: Memo) -> bool:
    return count_in(snap, 4, tw.SELECT_AREA, "minecraft:redstone_lamp") >= 2


def _transformed(snap: Snapshot, memo: Memo) -> bool:
    return new_edit(snap, memo, "rotate", "flip", "turn")


def _deleted(snap: Snapshot, memo: Memo) -> bool:
    return new_edit(snap, memo, "fill")


def _two_boxes(snap: Snapshot, memo: Memo) -> bool:
    return len(snap.regions) >= 2


def _zero_tick(snap: Snapshot, memo: Memo) -> bool:
    piston = tw.station(5, tw.SEQ_PISTON)
    return any(p.pos == piston and p.ticks == 0 and not p.muted for p in snap.doc.pulses())


def _spat(snap: Snapshot, memo: Memo) -> bool:
    planks = tw.station(5, tw.SEQ_PLANKS)
    return snap.doc.state_at((planks[0] - 1, planks[1], planks[2])).is_(blocks.OAK_PLANKS)


def _flag(name: str) -> Check:
    return lambda snap, memo: bool(getattr(snap, name))


def _strength_changed(snap: Snapshot, memo: Memo) -> bool:
    value = sources.strength_at(snap.doc.level, tw.station(6, tw.SEE_BARREL))
    return value is not None and value != 12


def _why(snap: Snapshot, memo: Memo) -> bool:
    return snap.tab == "Diagnostics/Why?" and snap.inspected == tw.station(6, tw.WHY_LAMP)


def _more(counter: Callable[[Snapshot], int]) -> Check:
    """More of something in the document than when the step began. Snapshots share the
    live document, so the count is taken when the step begins (``Progress.begin`` runs
    each check once right away)."""

    def check(snap: Snapshot, memo: Memo) -> bool:
        return counter(snap) > memo.setdefault("before", counter(start(memo)))

    return check


_used_while_running = _more(lambda snap: recorded(snap, "use"))
_pulse_added = _more(lambda snap: len(snap.doc.pulses()))
_monitored = _more(lambda snap: len(snap.doc.monitors))


def _center(station: int) -> tuple[float, float, float]:
    return tw.station_center(station)


# ------------------------------------------------------------------ the lessons
LESSONS: tuple[Lesson, ...] = (
    Lesson(
        "Look around",
        0,
        (
            Step(
                "Welcome!",
                "This card teaches the simulator one step at a time. It notices when you "
                "have done what a step asks and moves on by itself; <b>Next</b> skips a "
                "step, <b>Lessons</b> jumps to any lesson.<br><br>Each lesson has its own "
                "station in this tutorial world, with signs. Nothing here touches your files.",
                focus=_center(0),
            ),
            Step(
                "Orbit",
                "Drag with {key:camera.orbit} to turn the camera around the orange pivot.",
                _orbited,
            ),
            Step("Zoom", "Turn the mouse wheel ({key:camera.zoom}) to zoom in and out.", _zoomed),
            Step(
                "Move",
                "Move the pivot: drag with {key:camera.pan}, or hold {key:camera.forward} "
                "{key:camera.left} {key:camera.back} {key:camera.right}.",
                _panned,
            ),
            Step(
                "Focus",
                "Point at the lit lamp and press {key:camera.focus}: the pivot moves to it, "
                "and the camera turns around it from now on.",
                _focused_lamp,
                focus=_center(0),
            ),
        ),
    ),
    Lesson(
        "Use and inspect",
        1,
        (
            Step(
                "NORMAL mode",
                "You are in <b>NORMAL</b> mode (the badge at the bottom left; "
                "{key:mode.normal} gets you back here from any mode). Right-click "
                "({cap:Right Click}) the lever in the front row: the lamp lights at once.",
                _lamp_on(1, tw.USE_LAMP),
                focus=_center(1),
            ),
            Step(
                "Inspect",
                "Left-click ({cap:Left Click}) the lamp. The <b>Inspector</b> tab on the "
                "right shows its state and lets you change every property.",
                _inspected(1, tw.USE_LAMP),
            ),
            Step(
                "Block popup",
                "Point at the repeater in the back row and press {key:block.popup}: the "
                "same inspector opens next to the cursor.",
                lambda snap, memo: snap.popup,
            ),
            Step(
                "Change the delay",
                "Right-click the repeater (or use the arrows in the popup) to change its "
                "delay. Every change is one undo step.",
                _repeater_delay,
            ),
        ),
    ),
    Lesson(
        "Time",
        2,
        (
            Step(
                "Run and pause",
                "Press {key:sim.run} to run the simulation (20 ticks a second, like the "
                "game) and press it again to pause.",
                _ran_and_paused,
                focus=_center(2),
            ),
            Step(
                "Step tick by tick",
                "Flip the lever of this station, then press {key:sim.tick} a few times: "
                "the dust lights at once, the lamp after the repeater's 4 game ticks.",
                _stepped_to_lamp,
            ),
            Step(
                "Rewind",
                "Press {key:sim.tick_back} to step back. The history replays exactly, so "
                "you can go back and forth as often as you like.",
                _stepped_back,
            ),
            Step(
                "Tick 0 is the build",
                "Press {key:sim.start} to jump to tick 0, the build. Edits at tick 0 change "
                "the build itself; edits later in time are recorded on the timeline.",
                _at_tick_zero,
            ),
            Step(
                "Scrub the timeline",
                "Click or drag on the timeline's ruler (below the view) to jump to any "
                "recorded tick.",
                _scrubbed,
            ),
        ),
    ),
    Lesson(
        "Build",
        3,
        (
            Step(
                "BUILD mode",
                "Press {key:mode.build} for <b>BUILD</b> mode. The hotbar appears at the "
                "bottom. (Holding {key:mode.ring} shows a ring with every mode.)",
                _mode("build"),
                focus=_center(3),
            ),
            Step(
                "Choose redstone dust",
                "Press the number key of the <b>Redstone</b> folder, then <b>Wiring</b>, then "
                "<b>Redstone Dust</b>. Or search: {key:search.blocks}, type “dust”, Enter.",
                _chose("minecraft:redstone_wire"),
            ),
            Step(
                "Place a line",
                "On the white square, drag with the left mouse button from the lever "
                "towards the lamp: a line of dust, placed as one edit.",
                _dust_placed,
            ),
            Step(
                "Make it work",
                "Fill any gaps until the dust reaches the lamp, then flip the lever "
                "({key:build.use} in BUILD mode). The lamp lights up.",
                _build_lamp,
            ),
            Step(
                "Remove a block",
                "Right-click ({cap:Right Click}) a block in BUILD mode to remove it.",
                _removed,
            ),
            Step(
                "Turn a block",
                "Place a repeater, then point at it and press {key:edit.rotate_block} to turn it.",
                _turned,
            ),
            Step(
                "Undo",
                "Press {key:edit.undo} to undo the last edit ({key:edit.redo} redoes it). "
                "Edit → Undo History goes back several steps at once.",
                _undone,
            ),
            Step(
                "The build layer",
                "New blocks go on the layer at the pivot's height (the grid around the "
                "cursor). {key:build.layer} moves the layer up or down a block, for "
                "building in the air.",
                _layer_moved,
            ),
            Step(
                "Shapes and colors",
                "Choose a wool block (search “wool”), then press {key:inventory.color} for "
                "its other colors and {key:inventory.shape} for its stairs and slab (Shift "
                "goes back). The rows above the hotbar show them; a click picks one.",
                _wool_variant,
            ),
        ),
    ),
    Lesson(
        "Select, copy and paste",
        4,
        (
            Step(
                "SELECT mode",
                "Press {key:mode.select} for <b>SELECT</b> mode.",
                _mode("select"),
                focus=_center(4),
            ),
            Step(
                "Draw a box",
                "Drag across the inverter (the lever, the block with the torch and the "
                "lamp) to put a box around it. Drag a face's arrow to resize the box, or "
                "drag from inside it to move the box itself.",
                _boxed_inverter,
            ),
            Step(
                "Confirm it",
                "Press {key:select.lock} to confirm the selection (it turns orange): now "
                "the tools act on the blocks inside it. {key:mode.normal} goes back to "
                "editing the box.",
                _flag("confirmed"),
            ),
            Step(
                "Copy it",
                "Hold Ctrl and drag from inside the box: a pulsing copy follows the mouse "
                "(blocks it would replace turn red). Press {key:select.lock} to place it. "
                "(Or {key:edit.copy}, then {key:edit.paste} and a click to place.)",
                _copied,
            ),
            Step(
                "Turn and flip",
                "Press {key:edit.rotate} to turn the box's contents, {key:edit.flip} to flip "
                "them, then {key:select.lock} to place them ({key:mode.normal} cancels). "
                "Levers, torches and dust turn with them.",
                _transformed,
            ),
            Step(
                "Several boxes",
                "Press {key:mode.normal} to edit the boxes again, then hold Shift and drag "
                "somewhere else to draw a second box: once confirmed, moving, copying, "
                "turning and flipping act on all boxes together.",
                _two_boxes,
            ),
            Step(
                "Delete",
                "Press {key:edit.delete} to clear the boxes (it fills them with air).",
                _deleted,
            ),
        ),
    ),
    Lesson(
        "Sequences and the timeline",
        5,
        (
            Step(
                "Edits in time",
                "Run the simulation ({key:sim.run}), flip this station's lever while it "
                "runs, then pause. The flip is recorded: a yellow diamond in the "
                "timeline's <b>Used</b> row. Drag diamonds to move edits in time.",
                _used_while_running,
                focus=_center(5),
            ),
            Step(
                "ANIMATE mode",
                "Press {key:mode.animate} for <b>ANIMATE</b> mode: clicks power a "
                "position from the current tick on.",
                _mode("animate"),
            ),
            Step(
                "Add a pulse",
                "Scrub to a tick on the timeline and click one of the lamps: it gets a "
                "pulse (strength and duration come from the <b>Sequence</b> tab). The "
                "<b>Powered</b> row shows it as a bar.",
                _pulse_added,
            ),
            Step(
                "A 0-tick pulse",
                "In the Sequence tab set the duration to 0, scrub to another tick and "
                "click the sticky piston: power on and off inside one tick.",
                _zero_tick,
            ),
            Step(
                "Watch it",
                "Jump to tick 0 ({key:sim.start}) and run: the 0-tick pulse makes the "
                "piston spit its block instead of pulling it back.",
                _spat,
            ),
        ),
    ),
    Lesson(
        "See inside",
        6,
        (
            Step(
                "Debug screen",
                "Press {key:view.info} for the debug screen: signal values on the blocks, "
                "and details of the block under the cursor on the right.",
                _flag("info"),
                focus=_center(6),
            ),
            Step(
                "Heat view",
                "Press {key:view.heat}: powered blocks glow from dark red (strength 1) to "
                "yellow (15). Watch the dust lose one per block.",
                _flag("heat"),
            ),
            Step(
                "X-ray",
                "Press {key:view.xray} (again for more, a third time for off): building "
                "blocks turn see-through.",
                lambda snap, memo: snap.xray > 0,
            ),
            Step(
                "Signal sources",
                "Left-click the barrel and change its <b>strength</b> in the inspector: the "
                "comparator follows. Barrels, lecterns, cakes, composters, hoppers and "
                "chests can all be sources.",
                _strength_changed,
            ),
            Step(
                "Why did this change?",
                "Flip the back lever, left-click the lamp at the end of that row and open "
                "<b>Diagnostics → Why?</b>: the chain of causes back to the lever.",
                _why,
            ),
            Step(
                "Monitor tracks",
                "In the Inspector, press <b>Monitor</b>: the block gets a track on the "
                "timeline, like a logic analyzer.",
                _monitored,
            ),
        ),
    ),
    Lesson(
        "Organize",
        7,
        (
            Step(
                "Sections",
                "Inspect the lever and choose a <b>Section</b> in the inspector (input, "
                "output, …): it gets a colored outline. Sections are notes; they never "
                "change the simulation.",
                _more(section_count),
                focus=_center(7),
            ),
            Step(
                "Groups",
                "Draw a box around this station (SELECT mode), open <b>Circuit → Groups</b> "
                "and press <b>Group selection…</b>. Ports show live values; a double click "
                "on a group takes the camera there.",
                _more(lambda snap: len(snap.doc.groups.groups)),
            ),
            Step(
                "Prefabs",
                "With the box still there, open <b>Circuit → Prefabs</b> and press "
                "<b>Save selection…</b>: a reusable piece, kept with the world.",
                _more(lambda snap: len(snap.doc.prefabs)),
            ),
            Step(
                "Signs",
                "Place a sign (inventory <b>Wood</b> › a wood, or search “sign”) and type its "
                "text in the inspector.",
                _more(signs_with_text),
            ),
            Step(
                "Markers",
                "Press {key:sim.marker} to name the current tick: a marker on the timeline.",
                _more(lambda snap: len(snap.doc.visible_markers())),
            ),
        ),
    ),
    Lesson(
        "Files and worlds",
        8,
        (
            Step(
                "Save",
                "{key:file.save} saves a world as a <b>.redsim.json</b> file, with its "
                "timeline and notes. Try it: save this tutorial world anywhere you like "
                "(the tutorial goes on with it).",
                lambda snap, memo: snap.saves > start(memo).saves,
                focus=_center(8),
            ),
            Step(
                "Open",
                "{key:file.open} shows the <b>Select World</b> screen with your recent "
                "worlds and the examples. Open one, or cancel: the tutorial stays, and "
                "<b>Exit tutorial</b> (top of the view) brings back the world you had "
                "before. Any lesson takes you back to the tutorial world.",
                lambda snap, memo: snap.world_screens > start(memo).world_screens,
            ),
            Step(
                "Minecraft worlds",
                "File → <b>Open Minecraft world…</b> opens a Java 26.3 save; chunks load "
                "around the camera. <b>Builds in this world…</b> finds the redstone in it, "
                "<b>Save as Minecraft world…</b> writes a copy you can open in the game.",
            ),
            Step(
                "Schematics",
                "<b>Region → Import schematic…</b> reads Litematica, WorldEdit and "
                "structure files; <b>Export selection as schematic…</b> writes them.",
            ),
            Step(
                "Make it yours",
                "<b>Settings → Keymap…</b> changes any key, <b>Preferences</b> the look. "
                "{key:help.controls} lists every key; the hint bar at the bottom shows "
                "the ones that matter right now.",
            ),
            Step(
                "Done!",
                "That's everything. Open the <b>showcase</b> (File → Open…, Simulation "
                "worlds) for 44 working stations: logic, signal strength, pistons, items, "
                "clocks and a recorded sequence. <b>Exit tutorial</b> takes you back to "
                "your own world.",
            ),
        ),
    ),
)


@dataclass
class Progress:
    """Where the user is in the tutorial; ``poll`` runs the current step's check."""

    lesson: int = 0
    step: int = 0
    memo: Memo = field(default_factory=dict)
    done: bool = False  # the current step's check passed (shown until ``advance``)

    @property
    def current(self) -> Step:
        return LESSONS[self.lesson].steps[self.step]

    def begin(self, snapshot: Snapshot) -> None:
        """Start the current step: its baseline is this snapshot."""
        self.memo = {"start": snapshot}
        self.done = False
        check = self.current.check
        if check is not None:
            check(snapshot, self.memo)  # lets checks note counts at the start

    def poll(self, snapshot: Snapshot) -> bool:
        """True when the current step has just been done."""
        check = self.current.check
        if self.done or check is None or "start" not in self.memo:
            return False
        try:
            self.done = bool(check(snapshot, self.memo))
        except (KeyError, ValueError, IndexError, AttributeError):
            self.done = False  # e.g. another world is open: the step waits
        return self.done

    def go(self, lesson: int, step: int = 0) -> None:
        self.lesson = max(0, min(lesson, len(LESSONS) - 1))
        self.step = max(0, min(step, len(LESSONS[self.lesson].steps) - 1))
        self.memo = {}
        self.done = False

    def advance(self) -> bool:
        """On to the next step (or lesson); False at the very end."""
        if self.step + 1 < len(LESSONS[self.lesson].steps):
            self.go(self.lesson, self.step + 1)
            return True
        if self.lesson + 1 < len(LESSONS):
            self.go(self.lesson + 1)
            return True
        return False

    def back(self) -> None:
        if self.step > 0:
            self.go(self.lesson, self.step - 1)
        elif self.lesson > 0:
            self.go(self.lesson - 1, len(LESSONS[self.lesson - 1].steps) - 1)

    @property
    def is_last(self) -> bool:
        return self.lesson == len(LESSONS) - 1 and self.step == len(LESSONS[-1].steps) - 1

    def to_json(self) -> dict[str, int]:
        return {"lesson": self.lesson, "step": self.step}

    @staticmethod
    def from_json(data: Any) -> Progress:
        progress = Progress()
        if isinstance(data, dict):
            progress.go(int(data.get("lesson", 0) or 0), int(data.get("step", 0) or 0))
        return progress
