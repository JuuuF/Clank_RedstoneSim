"""A session: one world file opened, commands run on it, the file saved if it changed.

How a session works (doc/cli.md, "How a session works"):

1. **Open.** ``Session.open`` reads the world file into an editor ``Document`` (the same
   object the GUI edits; opening re-simulates the recorded history) and goes to the view
   saved last time (``extra["cli"]["view"]``: a tick and, for a view inside a tick, the
   number of engine steps into it).
2. **Run.** Each command line is split into words (``language.split_commands``), looked
   up in the registry and run. The whole session runs inside ``Document.deferred``, so a
   script of many build edits re-simulates the recorded future only once.
3. **Edits.** An editing command runs inside ``Session.editing``: it moves to the edit
   tick (0, the build, unless the line started with ``at T``), applies its edits as one
   undo step and leaves the view there for the moment. Before the next command that
   reads the world (and before saving) ``restore_view`` re-runs the deferred future and
   returns to the view, so inspection always sees the complete history.
4. **Save.** If anything changed, the previous file content goes to the undo file next to
   the world (``WORLD.undo``, the last 20 versions) and the document is saved with the
   command log (``extra["cli"]["log"]``, the last 500 command lines) and the view.

Printing: in text mode a command's lines are printed as they are; when several commands
run, each block starts with ``> command line``. Errors print ``error: message`` and stop the
run (unless ``keep_going``). In ``--json`` mode each command prints one JSON object on one
line: ``{"command": "...", "ok": true, "data": {...}}`` or ``{"command": "...", "ok":
false, "error": "..."}``.
"""

from __future__ import annotations

import contextlib
import gzip
import json
import sys
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any, TextIO

from redsim.cli.language import Args, CliError, join_words
from redsim.cli.registry import Output, lookup

#: How many earlier versions of a world the undo file keeps.
UNDO_VERSIONS = 20
#: Worlds larger than this are not copied into the undo file (opened Minecraft saves).
UNDO_MAX_BYTES = 20_000_000
#: How many command lines the world file's log keeps.
LOG_LINES = 500


class Session:
    def __init__(
        self,
        path: Path,
        *,
        json_mode: bool = False,
        dry_run: bool = False,
        keep_going: bool = False,
        out: TextIO | None = None,
    ) -> None:
        self.path = path
        self.json_mode = json_mode
        self.dry_run = dry_run
        self.keep_going = keep_going
        self.out = out if out is not None else sys.stdout
        self._document: Any = None
        self.changed = False
        #: The tick edits go to (``at T`` sets it for one command; 0 = the build).
        self.edit_tick = 0
        #: Where the view was before edits moved away from it (restored lazily).
        self._pending_view: tuple[int, int] | None = None
        self._stack = contextlib.ExitStack()
        #: Command lines run in this session (added to the world's log when saving).
        self.log: list[str] = []
        #: Restored from the undo file by ``undo`` (then saved without pushing a version).
        self.file_undone = False
        #: A ``check`` in this run found failing cases (the exit code becomes 1).
        self.failed_check = False

    # ------------------------------------------------------------------ the document
    @property
    def document(self) -> Any:
        if self._document is None:
            raise CliError(
                f"no world at {self.path} yet: create one with 'redsim-cli {self.path} new'"
            )
        return self._document

    @property
    def doc(self) -> Any:  # short form used by the commands
        return self.document

    @property
    def has_document(self) -> bool:
        return self._document is not None

    def open(self) -> None:
        """Open the world file if it exists (``new`` creates one otherwise)."""
        if not self.path.exists():
            return
        from redsim.editor.document import Document

        self.adopt(Document.open(self.path))

    def adopt(self, document: Any) -> None:
        """Make ``document`` the session's world (opening, ``new``, file undo)."""
        self._stack.close()
        self._stack = contextlib.ExitStack()
        self._document = document
        view = (document.extra.get("cli") or {}).get("view")
        if view:
            self.goto_view((int(view[0]), int(view[1])))
        self._stack.enter_context(document.deferred())

    def close(self) -> None:
        self._stack.close()

    # ------------------------------------------------------------------ time and view
    def view_now(self) -> tuple[int, int]:
        """The view as (tick boundary, engine steps after it)."""
        doc = self.document
        if doc.can_edit:
            return (doc.tick, 0)
        boundary = doc.tick - 1  # mid-tick: the tick in progress started after it
        start = doc.tick_steps.get(boundary, doc.history.start)
        return (boundary, doc.history.position - start)

    def goto(self, tick: int) -> None:
        """Move the view to the boundary after tick ``tick`` (simulating further if the
        recorded history is shorter)."""
        doc = self.document
        doc.flush()
        if tick <= doc.end_tick:
            doc.seek_tick(tick)
        else:
            doc.seek_tick(doc.end_tick)
            doc.run_ticks(tick - doc.tick)

    def goto_view(self, view: tuple[int, int]) -> None:
        tick, steps = view
        self.goto(tick)
        for _ in range(steps):
            if self.document.history.position >= self.document.history.end:
                break
            self.document.step()

    def restore_view(self) -> None:
        """Back to the view after edits moved to their tick (re-running deferred work)."""
        if self._pending_view is not None and self.has_document:
            view, self._pending_view = self._pending_view, None
            self.document.flush()
            self.goto_view(view)

    @contextlib.contextmanager
    def editing(self) -> Iterator[Any]:
        """An editing command: at ``edit_tick`` (the build unless ``at T``), as one undo
        step. Editor errors become ``CliError``."""
        from redsim.editor.document_history import EditError

        doc = self.document
        if self._pending_view is None:
            self._pending_view = self.view_now()
        if doc.tick != self.edit_tick or not doc.can_edit:
            self.goto(self.edit_tick)
        try:
            with doc.batch():
                yield doc
        except EditError as exc:
            raise CliError(str(exc)) from exc
        self.changed = True

    @property
    def where(self) -> str:
        """Where the last edit went, in words: "the build" or "tick T"."""
        return "the build" if self.edit_tick == 0 else f"tick {self.edit_tick}"

    # ------------------------------------------------------------------ running
    def execute(self, words: list[str]) -> Output:
        """Run one command (``words``: the command and its arguments)."""
        if not words:
            return Output()
        cmd = lookup(words[0])
        if cmd is None:
            import difflib

            from redsim.cli.registry import COMMANDS

            close = difflib.get_close_matches(words[0], list(COMMANDS), n=3)
            hint = f" (did you mean {', '.join(close)}?)" if close else ""
            raise CliError(f"unknown command {words[0]!r}{hint}; 'redsim-cli help' lists them")
        if cmd.kind != "edit":
            self.restore_view()
        args = Args(list(words[1:]), self._document, cmd.name)
        notice_before = self._document.notice if self._document is not None else ""
        if self._document is not None:
            self._document.notice = ""
        output = cmd.run(self, args)
        if self._document is not None:
            notice = self._document.notice
            if notice and notice != notice_before:
                output.add(f"note: {notice}")
                output.data.setdefault("notes", []).append(notice)
        return output

    def run(self, commands: Iterable[list[str]], echo: bool = False) -> int:
        """Run commands, printing each result; returns the exit code (0 or 1)."""
        failed = False
        for words in commands:
            text = join_words(words)
            try:
                self.edit_tick = 0
                output = self.execute(words)
                cmd = lookup(words[0])
                if cmd is not None and cmd.kind != "view":
                    self.log.append(text)  # the world's log (``log``)
            except CliError as exc:
                failed = True
                self._print_error(text, str(exc), echo)
                if not self.keep_going:
                    break
                continue
            self._print(text, output, echo)
        try:
            self.finish()
        except CliError as exc:
            self._print_error("save", str(exc), echo)
            return 1
        return 1 if failed or self.failed_check else 0

    def _print(self, text: str, output: Output, echo: bool) -> None:
        if self.json_mode:
            record = {"command": text, "ok": True, "data": output.data}
            self.out.write(json.dumps(record, ensure_ascii=False) + "\n")
            return
        if echo:
            self.out.write(f"> {text}\n")
        for line in output.lines:
            self.out.write(line + "\n")

    def _print_error(self, text: str, message: str, echo: bool) -> None:
        if self.json_mode:
            record = {"command": text, "ok": False, "error": message}
            self.out.write(json.dumps(record, ensure_ascii=False) + "\n")
            return
        if echo:
            self.out.write(f"> {text}\n")
        self.out.write(f"error: {message}\n")

    # ------------------------------------------------------------------ saving
    def finish(self) -> None:
        """Re-run deferred work, return to the view and save if something changed."""
        if not self.has_document:
            return
        self.restore_view()
        self.close()
        self.restore_view()
        if (self.changed or self.file_undone) and not self.dry_run:
            self.save()

    def save(self) -> None:
        doc = self.document
        if self.path.exists() and not self.file_undone:
            push_undo(self.path, self.path.read_bytes())
        cli = dict(doc.extra.get("cli") or {})
        cli["log"] = (list(cli.get("log", [])) + self.log)[-LOG_LINES:]
        cli["view"] = list(self.view_now())
        doc.extra["cli"] = cli
        doc.save(self.path)
        self.log = []


# ---------------------------------------------------------------------------- undo file
def undo_path(path: Path) -> Path:
    return path.with_name(path.name + ".undo")


def _read_undo(path: Path) -> dict[str, list[str]]:
    file = undo_path(path)
    if not file.exists():
        return {"undo": [], "redo": []}
    data = json.loads(gzip.decompress(file.read_bytes()))
    return {"undo": list(data.get("undo", [])), "redo": list(data.get("redo", []))}


def _write_undo(path: Path, data: dict[str, list[str]]) -> None:
    raw = json.dumps(data).encode()
    undo_path(path).write_bytes(gzip.compress(raw, compresslevel=6, mtime=0))


def push_undo(path: Path, content: bytes, clear_redo: bool = True) -> None:
    """Keep ``content`` (the file before a change) as the newest undo version."""
    if len(content) > UNDO_MAX_BYTES:
        return
    data = _read_undo(path)
    data["undo"] = (data["undo"] + [content.decode()])[-UNDO_VERSIONS:]
    if clear_redo:
        data["redo"] = []
    _write_undo(path, data)


def pop_version(path: Path, which: str) -> str | None:
    """Take the newest version from ``"undo"`` (moving the current file content to
    ``"redo"``) or from ``"redo"`` (moving it to ``"undo"``); None if there is none."""
    data = _read_undo(path)
    if not data[which]:
        return None
    version = data[which].pop()
    other = "redo" if which == "undo" else "undo"
    if path.exists():
        data[other] = (data[other] + [path.read_text()])[-UNDO_VERSIONS:]
    _write_undo(path, data)
    return version
