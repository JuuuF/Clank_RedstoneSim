"""The command language of ``redsim-cli``: how a line of text becomes a command and its
arguments. The same language is used on the command line, in script files, on standard
input and inside targets (doc/cli.md, "The command language").

A line is split into words like a shell does (``shlex``): words are separated by spaces,
``"double quotes"`` or ``'single quotes'`` keep spaces inside one word, ``#`` starts a
comment that runs to the end of the line, and ``;`` separates two commands on one line.
The first word is the command; the others are its arguments, read by an ``Args`` reader
in the order the command expects them.

Argument kinds (each has a reader method on ``Args``):

* **position** (``Args.pos``): three integers ``x y z``, or one word ``x,y,z``, or a label
  ``@NAME``, optionally with an offset: ``@NAME+1,0,-2`` (each part may be negative).
  Coordinates are Minecraft's: +x east, +z south, +y up.
* **block** (``Args.block``): a block id with or without ``minecraft:`` and optionally the
  ``/setblock`` property list: ``repeater``, ``minecraft:repeater[facing=west,delay=2]``.
  Further ``key=value`` words right after it are more properties (``repeater
  facing=west delay=2``). ``out=DIRECTION`` is a shortcut for the blocks whose ``facing``
  is the opposite of where they send their signal (repeaters, comparators, observers):
  ``repeater out=east`` is ``repeater[facing=west]``.
* **direction** (``Args.direction``): ``north south east west up down`` or their first
  letters ``n s e w u d``.
* **tick** (``Args.tick``) and **tick range** (``Args.tick_range``): ``5`` or ``3..9``
  (both ends included).
* **keyword options**: a word followed by its value, like ``for 3`` or ``strength 15``
  (``Args.option``), and ``key=value`` options (``Args.pop_key``).

Every reader raises ``CliError`` with a message that says what was expected and what was
found; the session prints it as ``error: …``.
"""

from __future__ import annotations

import difflib
import re
import shlex
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from redsim.core.direction import Direction
from redsim.core.pos import Pos

if TYPE_CHECKING:
    from redsim.editor.document import Document
    from redsim.world.block import BlockState


class CliError(Exception):
    """A command that cannot run: wrong arguments, unknown names, an edit the game refuses.
    The message is shown to the user as ``error: <message>``."""


DIRECTIONS = {
    "north": Direction.NORTH,
    "n": Direction.NORTH,
    "south": Direction.SOUTH,
    "s": Direction.SOUTH,
    "east": Direction.EAST,
    "e": Direction.EAST,
    "west": Direction.WEST,
    "w": Direction.WEST,
    "up": Direction.UP,
    "u": Direction.UP,
    "down": Direction.DOWN,
    "d": Direction.DOWN,
}

#: Blocks whose ``facing`` property points opposite to where their signal goes, for the
#: ``out=`` shortcut.
OUT_IS_OPPOSITE_OF_FACING = frozenset(
    {"minecraft:repeater", "minecraft:comparator", "minecraft:observer"}
)

_INT = re.compile(r"-?\d+$")
_TRIPLE = re.compile(r"(-?\d+),(-?\d+),(-?\d+)$")
_LABEL = re.compile(r"@([A-Za-z_][\w.-]*)(?:([+-]-?\d+),(-?\d+),(-?\d+))?$")
_RANGE = re.compile(r"(-?\d+)\.\.(-?\d+)$")


def split_commands(text: str) -> Iterator[list[str]]:
    """The commands in ``text`` (lines, and ``;`` within lines), each as its words.
    Empty lines and comments give nothing."""
    for line in text.splitlines():
        lexer = shlex.shlex(line, posix=True, punctuation_chars=";")
        lexer.whitespace_split = True
        try:
            words = list(lexer)
        except ValueError as exc:  # an unclosed quote
            raise CliError(f"cannot read {line!r}: {exc}") from exc
        current: list[str] = []
        for word in words:
            if word == ";":
                if current:
                    yield current
                current = []
            else:
                current.append(word)
        if current:
            yield current


def join_words(words: list[str]) -> str:
    """Words back to one line that ``split_commands`` reads the same way."""
    return " ".join(shlex.quote(w) if _needs_quotes(w) else w for w in words)


def _needs_quotes(word: str) -> bool:
    return word == "" or any(c in word for c in " \t'\"#;\\")


def format_pos(pos: Pos) -> str:
    """A position as the language writes it: ``x y z``."""
    return f"{pos[0]} {pos[1]} {pos[2]}"


@dataclass
class Args:
    """The arguments of one command, read front to back. ``document`` resolves labels."""

    words: list[str]
    document: Document | None = None
    command: str = ""
    index: int = 0
    used_keys: set[str] = field(default_factory=set)

    # ------------------------------------------------------------------ basics
    def more(self) -> bool:
        return self.index < len(self.words)

    def peek(self) -> str | None:
        return self.words[self.index] if self.more() else None

    def word(self, what: str = "a word") -> str:
        if not self.more():
            raise CliError(f"{self.command}: expected {what}, found the end of the line")
        word = self.words[self.index]
        self.index += 1
        return word

    def rest(self) -> list[str]:
        """All words left (and consume them)."""
        words, self.index = self.words[self.index :], len(self.words)
        return words

    def done(self) -> None:
        """Fail if words are left over (catches typos in options)."""
        if self.more():
            left = " ".join(self.words[self.index :])
            raise CliError(f"{self.command}: did not understand {left!r}")

    def number(self, what: str = "a number") -> int:
        word = self.word(what)
        if not _INT.match(word):
            raise CliError(f"{self.command}: expected {what}, found {word!r}")
        return int(word)

    def choice(self, options: tuple[str, ...], what: str) -> str:
        word = self.word(what)
        if word not in options:
            raise CliError(f"{self.command}: {what} must be one of {', '.join(options)}")
        return word

    # ------------------------------------------------------------------ options
    def option(self, name: str) -> bool:
        """Consume the word ``name`` if it comes next (``for``, ``strength``, …)."""
        if self.peek() == name:
            self.index += 1
            return True
        return False

    def option_int(self, name: str, default: int) -> int:
        """``name N`` if it comes next, else ``default``."""
        return self.number(f"a number after {name!r}") if self.option(name) else default

    def pop_key(self, key: str) -> str | None:
        """A ``key=value`` word anywhere among the remaining words (removed if found)."""
        for i in range(self.index, len(self.words)):
            if self.words[i].startswith(key + "="):
                value = self.words[i][len(key) + 1 :]
                del self.words[i]
                self.used_keys.add(key)
                return value
        return None

    # ------------------------------------------------------------------ values
    def pos(self, what: str = "a position") -> Pos:
        """A position: ``x y z``, ``x,y,z``, ``@NAME`` or ``@NAME+dx,dy,dz``."""
        word = self.word(what)
        triple = _TRIPLE.match(word)
        if triple:
            return (int(triple[1]), int(triple[2]), int(triple[3]))
        label = _LABEL.match(word)
        if label:
            return self._label(label)
        if _INT.match(word):
            y = self.number(f"the y of {what}")
            z = self.number(f"the z of {what}")
            return (int(word), y, z)
        raise CliError(f"{self.command}: expected {what} (x y z, x,y,z or @label), found {word!r}")

    def maybe_pos(self) -> Pos | None:
        """A position if the next word starts one, else None (nothing consumed)."""
        word = self.peek()
        if word is None:
            return None
        if _TRIPLE.match(word) or _LABEL.match(word):
            return self.pos()
        following = self.words[self.index : self.index + 3]
        if len(following) == 3 and all(_INT.match(w) for w in following):
            return self.pos()
        return None

    def _label(self, match: re.Match[str]) -> Pos:
        name = match[1]
        labels = self.document.labels if self.document is not None else {}
        label = labels.get(name)
        if label is None:
            known = ", ".join(f"@{n}" for n in sorted(labels)) or "none yet"
            raise CliError(f"{self.command}: no label @{name} (labels: {known})")
        x, y, z = label.pos
        if match[2] is not None:
            x, y, z = x + int(match[2]), y + int(match[3]), z + int(match[4])
        return (x, y, z)

    def direction(self, what: str = "a direction") -> Direction:
        word = self.word(what)
        direction = DIRECTIONS.get(word.lower())
        if direction is None:
            raise CliError(
                f"{self.command}: expected {what} (north south east west up down), found {word!r}"
            )
        return direction

    def tick(self, what: str = "a tick") -> int:
        value = self.number(what)
        if value < 0:
            raise CliError(f"{self.command}: ticks start at 0 (the build), found {value}")
        return value

    def tick_range(self, what: str = "a tick or a range A..B") -> tuple[int, int]:
        word = self.word(what)
        match = _RANGE.match(word)
        if match:
            low, high = int(match[1]), int(match[2])
        elif _INT.match(word):
            low = high = int(word)
        else:
            raise CliError(f"{self.command}: expected {what}, found {word!r}")
        if low < 0 or high < low:
            raise CliError(f"{self.command}: {word!r} is not a range of ticks (0 ≤ A ≤ B)")
        return low, high

    def block(self, what: str = "a block") -> BlockState:
        """A block state: ``id``, ``id[props]`` and following ``key=value`` properties."""
        text = self.word(what)
        extra: list[str] = []
        while self.more() and "=" in (self.peek() or "") and not self.peek().startswith("@"):  # type: ignore[union-attr]
            key = (self.peek() or "").split("=", 1)[0]
            if not re.fullmatch(r"[a-z_]+", key):
                break
            extra.append(self.word())
        return parse_block(text, extra, self.command)


def parse_block(text: str, extra: list[str] | None = None, command: str = "") -> BlockState:
    """``id[props]`` plus ``key=value`` words into a block state, with helpful errors:
    close matches for unknown ids, the allowed values for a wrong property value."""
    from redsim.world import blocks
    from redsim.world.blocks.catalog_data import BLOCKS as GAME_BLOCKS

    name, bracket, rest = text.partition("[")
    block_id = name if ":" in name else f"minecraft:{name}"
    block = blocks.REGISTRY.get(block_id)
    if block is None and block_id in GAME_BLOCKS:
        # A real block the simulator does not model: kept as a foreign (inert) block.
        props = (rest.rstrip("]") if bracket else "").split(",") + list(extra or [])
        inner = ",".join(p.strip() for p in props if p.strip())
        return blocks.parse_state(f"{block_id}[{inner}]" if inner else block_id)
    if block is None:
        names = [b.removeprefix("minecraft:") for b in GAME_BLOCKS]
        close = difflib.get_close_matches(name.removeprefix("minecraft:"), names, n=4)
        hint = f" (did you mean {', '.join(close)}?)" if close else ""
        raise CliError(f"{command}: unknown block {name!r}{hint}")
    pairs: list[tuple[str, str]] = []
    if bracket:
        if not rest.endswith("]"):
            raise CliError(f"{command}: {text!r} lacks the closing ]")
        for part in rest[:-1].split(","):
            if part.strip():
                key, eq, value = part.partition("=")
                if not eq:
                    raise CliError(f"{command}: property {part!r} needs key=value")
                pairs.append((key.strip(), value.strip()))
    for word in extra or []:
        key, _, value = word.partition("=")
        pairs.append((key, value))
    state = block.default_state
    by_name = {p.name: p for p in block.properties}
    for key, value in pairs:
        if key == "out" and block.id in OUT_IS_OPPOSITE_OF_FACING:
            direction = DIRECTIONS.get(value)
            if direction is None:
                raise CliError(f"{command}: out= needs a direction, found {value!r}")
            key, value = "facing", direction.opposite.serialized
        prop = by_name.get(key)
        if prop is None:
            known = ", ".join(sorted(by_name)) or "none"
            raise CliError(f"{command}: {block.name} has no property {key!r} (it has: {known})")
        try:
            parsed = prop.parse(value)
        except Exception as exc:
            allowed = ", ".join(prop.serialize(v) for v in prop.values)
            raise CliError(f"{command}: {key}={value} is not allowed (values: {allowed})") from exc
        if parsed not in prop.values:
            allowed = ", ".join(prop.serialize(v) for v in prop.values)
            raise CliError(f"{command}: {key}={value} is not allowed (values: {allowed})")
        state = state.with_(prop, parsed)
    return state
