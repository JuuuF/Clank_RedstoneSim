"""Meta commands: ``help`` inside scripts and the shell."""

from __future__ import annotations

from redsim.cli.language import Args, CliError
from redsim.cli.registry import Output, command, lookup, render_command, render_overview
from redsim.cli.session import Session


@command(
    "help",
    group="meta",
    usage="help [COMMAND]",
    summary="List the commands, or show one command in full.",
    help="""
    Without a command: every command with one line about it, by chapter. With a command:
    its syntax, description, examples and what its `--json` output holds. The same text
    is in doc/cli-reference.md; the concepts are explained in doc/cli.md.
    """,
    examples=("help", "help place"),
    kind="view",
    data='{"text"}',
)
def help_(session: Session, args: Args) -> Output:
    if not args.more():
        text = render_overview()
    else:
        name = args.word()
        cmd = lookup(name)
        if cmd is None:
            raise CliError(f"help: no command {name!r}")
        text = render_command(cmd)
    args.done()
    return Output(text.splitlines(), {"text": text})
