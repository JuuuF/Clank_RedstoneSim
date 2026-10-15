"""The command registry: every command of ``redsim-cli`` with its documentation.

A command is a function ``run(session, args) -> Output`` registered with the ``command``
decorator, which also records everything the help and the reference documentation show:

* ``name``, ``group`` (the chapter of the reference), ``usage`` (the syntax line);
* ``summary``: one line; ``help``: the full description (plain text, paragraphs separated
  by blank lines, lists with ``-``);
* ``examples``: command lines, each optionally with ``  # what it does``;
* ``kind``: ``"edit"`` (changes the world: the build, or the timeline with ``at T``),
  ``"view"`` (only reads; ``at T`` looks at tick T), ``"time"`` (moves the view or changes
  the timeline), ``"file"`` (whole-file operations) or ``"meta"`` (help, annotations);
* ``data``: what the ``--json`` output's ``data`` holds.

``redsim-cli help`` prints this text and ``doc/cli-reference.md`` is generated from it
(``render_reference``; ``tests/cli/test_docs.py`` checks that the file is up to date), so
the help an agent reads, the help a person reads and the documentation are the same text.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from redsim.cli.language import Args
    from redsim.cli.session import Session

Kind = Literal["edit", "view", "time", "file", "meta"]

#: The chapters of the reference, in order, with a sentence each.
GROUPS: dict[str, str] = {
    "world": "Creating, describing and saving world files.",
    "build": "Changing the contraption. These edit the build (tick 0) unless prefixed "
    "with `at T`, which records the edit on the timeline at tick T instead.",
    "time": "Moving the view through time and changing the timeline (recorded edits, "
    "power pulses, markers, undo).",
    "inspect": "Looking at the world: maps, single blocks, signals, causes, changes and "
    "signal timelines. They only read; `at T` looks at tick T.",
    "annotate": "Names and notes that make a world readable: labels, notes, sections.",
    "targets": "Acceptance tests for contraptions: what should happen, checked from the build.",
    "io": "Exchanging builds with Minecraft: schematics and structure files, saves.",
    "meta": "Help and the command line itself.",
}


@dataclass
class Output:
    """What a command returns: text lines for people and agents, and the same facts as
    JSON-ready ``data`` for ``--json``."""

    lines: list[str] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)

    def add(self, line: str = "") -> Output:
        self.lines.append(line)
        return self


@dataclass(frozen=True)
class Command:
    name: str
    group: str
    usage: str
    summary: str
    help: str
    examples: tuple[str, ...]
    kind: Kind
    data: str
    run: Callable[[Session, Args], Output]
    aliases: tuple[str, ...] = ()


COMMANDS: dict[str, Command] = {}
ALIASES: dict[str, str] = {}


def command(
    name: str,
    *,
    group: str,
    usage: str,
    summary: str,
    help: str,
    examples: tuple[str, ...] = (),
    kind: Kind,
    data: str = "",
    aliases: tuple[str, ...] = (),
) -> Callable[[Callable[[Session, Args], Output]], Callable[[Session, Args], Output]]:
    """Register a command (see the module docstring for the fields)."""
    if group not in GROUPS:
        raise ValueError(f"unknown group {group!r}")

    def register(run: Callable[[Session, Args], Output]) -> Callable[[Session, Args], Output]:
        if name in COMMANDS or name in ALIASES:
            raise ValueError(f"duplicate command {name!r}")
        COMMANDS[name] = Command(
            name,
            group,
            usage,
            summary,
            _dedent(help),
            examples,
            kind,
            _dedent(data),
            run,
            aliases,
        )
        for alias in aliases:
            ALIASES[alias] = name
        return run

    return register


def lookup(name: str) -> Command | None:
    return COMMANDS.get(ALIASES.get(name, name))


def _dedent(text: str) -> str:
    import textwrap

    return textwrap.dedent(text).strip()


# ---------------------------------------------------------------------------- help text
def render_command(cmd: Command, markdown: bool = False) -> str:
    """One command's help: usage, summary, description, examples, JSON data."""
    if markdown:
        parts = [f"### `{cmd.name}`", "", f"`{cmd.usage}`", "", cmd.summary, "", cmd.help]
        if cmd.aliases:
            parts += ["", "Also: " + ", ".join(f"`{a}`" for a in cmd.aliases)]
        if cmd.examples:
            parts += ["", "Examples:", "", "```", *cmd.examples, "```"]
        if cmd.data:
            parts += ["", f"JSON `data`: {cmd.data}"]
        return "\n".join(parts)
    parts = [f"{cmd.usage}", "", f"  {cmd.summary}", ""]
    parts += [("  " + line) if line else "" for line in cmd.help.splitlines()]
    if cmd.aliases:
        parts += ["", "  Also: " + ", ".join(cmd.aliases)]
    if cmd.examples:
        parts += ["", "  Examples:"] + [f"    {e}" for e in cmd.examples]
    if cmd.data:
        parts += ["", "  JSON data: " + cmd.data.replace("\n", " ")]
    return "\n".join(parts)


def render_overview() -> str:
    """``redsim-cli help`` without a command: every command by group, one line each."""
    lines: list[str] = []
    for group, text in GROUPS.items():
        members = [c for c in COMMANDS.values() if c.group == group]
        if not members:
            continue
        lines += [f"{group}: {text}"]
        width = max(len(c.name) for c in members)
        lines += [f"  {c.name.ljust(width)}  {c.summary}" for c in members]
        lines.append("")
    return "\n".join(lines).rstrip()


def render_reference() -> str:
    """``doc/cli-reference.md``: every command's help in Markdown, by group."""
    out = [
        "# redsim-cli command reference",
        "",
        "Generated from the command registry (`redsim-cli help --markdown`); do not edit by",
        "hand. The concepts (positions, ticks, the build and the timeline, labels, targets,",
        "output formats) are explained in [[cli]]. Each command below shows its syntax, what",
        "it does, examples and what its `--json` output holds.",
        "",
        "Syntax: `UPPER` words are values you fill in, `[brackets]` are optional, `A|B`",
        "means one of them, `...` means repeatable. POS is a position (`x y z`, `x,y,z` or",
        "`@label[+dx,dy,dz]`), BLOCK a block state (`repeater[facing=west]` or",
        "`repeater facing=west`), T a tick, A..B a range of ticks.",
        "",
    ]
    for group, text in GROUPS.items():
        members = [c for c in COMMANDS.values() if c.group == group]
        if not members:
            continue
        out += [f"## {group.capitalize()}", "", text, ""]
        for cmd in members:
            out += [render_command(cmd, markdown=True), ""]
    return "\n".join(out).rstrip() + "\n"
