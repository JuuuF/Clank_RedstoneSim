"""``redsim-cli``: the program's entry point (doc/cli.md, "Running redsim-cli").

    redsim-cli [OPTIONS] WORLD COMMAND [ARGS...]   one command
    redsim-cli [OPTIONS] WORLD -c "CMD; CMD ..."   several commands
    redsim-cli [OPTIONS] WORLD < script.txt        commands from standard input
    redsim-cli [OPTIONS] WORLD                     (a terminal) the world's summary
    redsim-cli [OPTIONS] WORLD shell               an interactive prompt
    redsim-cli help [COMMAND | --markdown]         help

Options (anywhere before the command): ``--json`` (one JSON object per command),
``--dry-run`` (run, but do not save), ``--keep-going`` (do not stop at the first error).
The exit code is 0 when every command worked, 1 when one failed, 2 for a wrong call.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TextIO

from redsim.cli import commands  # noqa: F401  (registers every command)
from redsim.cli.language import CliError, split_commands
from redsim.cli.registry import lookup, render_command, render_overview, render_reference
from redsim.cli.session import Session

USAGE = """usage: redsim-cli [--json] [--dry-run] [--keep-going] WORLD [COMMAND [ARGS...]]
       redsim-cli [OPTIONS] WORLD -c "COMMAND; COMMAND; ..."
       redsim-cli [OPTIONS] WORLD < commands.txt
       redsim-cli [OPTIONS] WORLD shell
       redsim-cli help [COMMAND] | help --markdown

WORLD is a .redsim.json world file (the editor's format); 'redsim-cli WORLD new' creates
one. 'redsim-cli help' lists the commands; doc/cli.md explains everything."""

OPTIONS = ("--json", "--dry-run", "--keep-going")


def main(
    argv: list[str] | None = None, stdin: TextIO | None = None, out: TextIO | None = None
) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    stdin = sys.stdin if stdin is None else stdin
    out = sys.stdout if out is None else out
    flags = {flag: False for flag in OPTIONS}
    while args and args[0] in OPTIONS:
        flags[args.pop(0)] = True
    if not args or args[0] in ("-h", "--help"):
        out.write(USAGE + "\n")
        return 0 if args else 2
    if args[0] == "help":
        return _help(args[1:], out)
    world = Path(args.pop(0))
    while args and args[0] in OPTIONS:
        flags[args.pop(0)] = True
    session = Session(
        world,
        json_mode=flags["--json"],
        dry_run=flags["--dry-run"],
        keep_going=flags["--keep-going"],
        out=out,
    )
    try:
        session.open()
        if args == ["shell"]:
            out.write(f"redsim-cli shell on {world}: commands as in scripts; help; exit\n")
            return session.interactive(input)
        if args and args[0] == "-c":
            if len(args) != 2:
                out.write("error: -c takes one argument: the commands, separated by ';'\n")
                return 2
            batch = list(split_commands(args[1]))
            return session.run(batch, echo=len(batch) > 1)
        if args:
            return session.run([args], echo=False)
        if not stdin.isatty():
            batch = list(split_commands(stdin.read()))
            return session.run(batch, echo=True)
        return session.run([["info"]], echo=False)
    except CliError as exc:
        out.write(f"error: {exc}\n")
        return 1


def _help(args: list[str], out: TextIO) -> int:
    if not args:
        out.write(
            USAGE + "\n\n" + render_overview() + "\n\n"
            "'redsim-cli help COMMAND' shows one command in full.\n"
        )
        return 0
    if args[0] == "--markdown":
        out.write(render_reference())
        return 0
    cmd = lookup(args[0])
    if cmd is None:
        out.write(f"error: no command {args[0]!r}; 'redsim-cli help' lists them\n")
        return 1
    out.write(render_command(cmd) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
