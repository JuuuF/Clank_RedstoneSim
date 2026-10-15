"""Sandboxed Java Edition 26.3 dedicated server, driven through its console.

Purpose: compare simulator results with the real game (owner-approved, testing only; see
doc/experiments/index.md). Sandbox rules:

* runs in ``.sandbox/gameserver/`` (gitignored); the supplied JARs are only read;
* offline mode, bound to 127.0.0.1, no RCON/query/status/management endpoints;
* a fresh superflat world, peaceful, no structures; never touches other installations.

The bundler ``data/minecraft_jars/server.jar`` extracts its libraries into the sandbox on
first start (no network access is needed for that).
"""

from __future__ import annotations

import os
import queue
import re
import shutil
import subprocess
import threading
import time
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SERVER_JAR = REPO_ROOT / "data" / "minecraft_jars" / "server.jar"
SANDBOX = REPO_ROOT / ".sandbox" / "gameserver"
JAVA_CANDIDATES = ("/usr/lib/jvm/java-25-openjdk/bin/java", "java")

PROPERTIES = {
    "online-mode": "false",
    "server-ip": "127.0.0.1",
    "server-port": "25599",
    "enable-rcon": "false",
    "enable-query": "false",
    "enable-status": "false",
    "management-server-enabled": "false",
    "enable-jmx-monitoring": "false",
    "level-name": "world",
    "level-type": "minecraft\\:flat",
    "level-seed": "redsim",
    "generate-structures": "false",
    "difficulty": "peaceful",
    "gamemode": "creative",
    "max-players": "1",
    "spawn-protection": "0",
    "view-distance": "3",
    "simulation-distance": "3",
    "pause-when-empty-seconds": "0",
    "max-tick-time": "-1",
    "sync-chunk-writes": "false",
    "log-ips": "false",
    "motd": "redsim sandbox",
}

_MARKER_RE = re.compile(r"Set \[redsim_sync\] for #sync to (\d+)")
_LOG_RE = re.compile(r"^\[[^\]]*\] \[Server thread/INFO\]: (.*)$")


def find_java() -> str:
    for candidate in JAVA_CANDIDATES:
        path = shutil.which(candidate) if not os.path.isabs(candidate) else candidate
        if path and os.path.exists(path):
            return path
    raise RuntimeError("no Java runtime found (26.3 needs Java 25)")


@dataclass
class CommandResult:
    command: str
    lines: list[str]

    @property
    def text(self) -> str:
        return "\n".join(self.lines)


class GameServer:
    """A running sandboxed server. Use as a context manager."""

    def __init__(self, sandbox: Path = SANDBOX, fresh_world: bool = False) -> None:
        self.sandbox = sandbox
        self.fresh_world = fresh_world
        self.process: subprocess.Popen[str] | None = None
        self._lines: queue.Queue[str] = queue.Queue()
        self._marker = 0
        self.log: list[str] = []

    # ------------------------------------------------------------------ lifecycle
    def prepare(self) -> None:
        self.sandbox.mkdir(parents=True, exist_ok=True)
        if self.fresh_world and (self.sandbox / "world").exists():
            shutil.rmtree(self.sandbox / "world")
        # The project owner accepted the Minecraft EULA for this sandbox (2026-10-10).
        (self.sandbox / "eula.txt").write_text("eula=true\n")
        props = "\n".join(f"{k}={v}" for k, v in PROPERTIES.items()) + "\n"
        (self.sandbox / "server.properties").write_text(props)

    def start(self, timeout: float = 240.0) -> None:
        self.prepare()
        self.process = subprocess.Popen(
            [find_java(), "-Xms1G", "-Xmx2G", "-jar", str(SERVER_JAR), "--nogui"],
            cwd=self.sandbox,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        threading.Thread(target=self._pump, daemon=True).start()
        deadline = time.monotonic() + timeout
        while True:
            line = self._next_line(deadline)
            if "Done (" in line and "For help" in line:
                break
        self.run(
            [
                "scoreboard objectives add redsim_sync dummy",
                "gamerule random_tick_speed 0",
                "gamerule advance_time false",
                "gamerule advance_weather false",
                "gamerule spawn_mobs false",
                "gamerule log_admin_commands false",
                # The simulator has no item entities: popped blocks must not drop items
                # that hoppers could collect (found by fuzzing, EXP-031).
                "gamerule block_drops false",
                # Nor item entities from falling blocks that cannot land (gravity blocks).
                "gamerule entity_drops false",
                "kill @e[type=minecraft:item]",
                "tick freeze",
            ]
        )

    def stop(self) -> None:
        if self.process is None:
            return
        try:
            assert self.process.stdin is not None
            self.process.stdin.write("stop\n")
            self.process.stdin.flush()
            self.process.wait(timeout=60)
        except (OSError, subprocess.TimeoutExpired):
            self.process.kill()
        self.process = None

    def __enter__(self) -> GameServer:
        self.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self.stop()

    def _pump(self) -> None:
        assert self.process is not None and self.process.stdout is not None
        for raw in self.process.stdout:
            self._lines.put(raw.rstrip("\n"))
        self._lines.put("\x00EOF")

    def _next_line(self, deadline: float) -> str:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("server did not answer in time")
        line = self._lines.get(timeout=remaining)
        if line == "\x00EOF":
            raise RuntimeError("server exited:\n" + "\n".join(self.log[-30:]))
        self.log.append(line)
        return line

    # ------------------------------------------------------------------ commands
    def run(self, commands: Iterable[str], timeout: float = 60.0) -> list[CommandResult]:
        """Send commands (executed in order between ticks) and collect each one's output."""
        assert self.process is not None and self.process.stdin is not None
        commands = list(commands)
        markers: list[int] = []
        payload = []
        for command in commands:
            self._marker += 1
            markers.append(self._marker)
            payload.append(command)
            payload.append(f"scoreboard players set #sync redsim_sync {self._marker}")
        self.process.stdin.write("\n".join(payload) + "\n")
        self.process.stdin.flush()
        results: list[CommandResult] = []
        deadline = time.monotonic() + timeout
        current: list[str] = []
        for command, marker in zip(commands, markers, strict=True):
            while True:
                line = self._next_line(deadline)
                match = _LOG_RE.match(line)
                message = match.group(1) if match else line
                found = _MARKER_RE.search(message)
                if found and int(found.group(1)) == marker:
                    break
                current.append(message)
            results.append(CommandResult(command, current))
            current = []
        return results

    def command(self, command: str) -> CommandResult:
        return self.run([command])[0]

    def game_time(self) -> int:
        text = self.command("time query gametime").text
        found = re.search(r"time is (-?\d+)", text)
        if not found:
            raise RuntimeError(f"unexpected time output: {text!r}")
        return int(found.group(1))

    def step(self, ticks: int = 1, timeout: float = 30.0) -> int:
        """``/tick step`` and wait until the game time advanced; returns the new time."""
        start = self.game_time()
        self.command(f"tick step {ticks}")
        deadline = time.monotonic() + timeout
        while True:
            now = self.game_time()
            if now >= start + ticks:
                return now
            if time.monotonic() > deadline:
                raise TimeoutError("tick step did not complete")
            time.sleep(0.02)

    def test_blocks(self, checks: list[tuple[tuple[int, int, int], str]]) -> list[bool]:
        """``execute if block`` for many (pos, state predicate) pairs in one round trip."""
        commands = [f"execute if block {x} {y} {z} {pred}" for (x, y, z), pred in checks]
        results = self.run(commands)
        verdicts = []
        for result in results:
            if "Test passed" in result.text:
                verdicts.append(True)
            elif "Test failed" in result.text:
                verdicts.append(False)
            else:
                raise RuntimeError(f"unexpected output for {result.command!r}: {result.text!r}")
        return verdicts
