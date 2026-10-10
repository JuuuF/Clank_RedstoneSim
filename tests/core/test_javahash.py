"""Tests for the java.util.HashMap/HashSet iteration-order emulation (ADR-005)."""

from __future__ import annotations

import random
import subprocess
from pathlib import Path

from redsim.core.javahash import JavaHashMap, JavaHashSet, spread
from redsim.core.pos import Pos, java_hash, to_int32
from tests.jdk import find_jdk_tool


def test_java_hash_matches_vec3i_formula() -> None:
    assert java_hash((0, 0, 0)) == 0
    assert java_hash((1, 2, 3)) == (2 + 3 * 31) * 31 + 1
    # 32-bit overflow wraps exactly like Java int arithmetic.
    assert java_hash((0, 0, 30_000_000)) == to_int32(30_000_000 * 31 * 31)
    assert java_hash((-5, -64, -7)) == (-64 + -7 * 31) * 31 - 5


def test_spread_mixes_high_bits() -> None:
    assert spread(0x0001_0000) == 0x0001_0001
    assert spread(-1) == 0xFFFF_0000


def test_insertion_order_within_bucket_and_bucket_order() -> None:
    # Keys (16, 0, 0) and (0, 0, 0) land in bucket 0 of a 16-slot table (16 & 15 == 0),
    # (1, 0, 0) lands in bucket 1. Iteration: bucket 0 in insertion order, then bucket 1.
    s: JavaHashSet[Pos] = JavaHashSet(java_hash, [(1, 0, 0), (16, 0, 0), (0, 0, 0)])
    assert list(s) == [(16, 0, 0), (0, 0, 0), (1, 0, 0)]


def test_remove_and_reinsert_moves_key_to_bucket_end() -> None:
    m: JavaHashMap[Pos, int] = JavaHashMap(java_hash)
    m.put((0, 0, 0), 1)
    m.put((16, 0, 0), 2)
    m.remove((0, 0, 0))
    m.put((0, 0, 0), 3)
    assert list(m.items()) == [((16, 0, 0), 2), ((0, 0, 0), 3)]


def test_resize_doubles_capacity_after_threshold() -> None:
    m: JavaHashMap[Pos, int] = JavaHashMap(java_hash)
    for i in range(12):
        m.put((i, 0, 0), i)
    assert m.capacity == 16
    m.put((12, 0, 0), 12)
    assert m.capacity == 32


def _oracle_orders(classes: Path, cases: list[list[tuple[str, Pos]]]) -> list[list[Pos]]:
    java = find_jdk_tool("java")
    assert java is not None
    lines: list[str] = []
    for ops in cases:
        lines += [f"{op} {p[0]} {p[1]} {p[2]}" for op, p in ops]
        lines.append("end")
    result = subprocess.run(
        [java, "-cp", str(classes), "HashOrderOracle"],
        input="\n".join(lines) + "\n",
        capture_output=True,
        text=True,
        check=True,
    )
    orders = []
    for row in result.stdout.splitlines():
        keys = [tuple(int(v) for v in item.split(",")) for item in row.split(";") if item]
        orders.append(keys)
    return orders  # type: ignore[return-value]


def test_matches_real_java_hashmap(java_oracle: Path) -> None:
    """Random put/remove sequences replayed on a real JVM must iterate identically."""
    rng = random.Random(26_3)
    cases: list[list[tuple[str, Pos]]] = []
    for case_index in range(300):
        spread_range = 3 if case_index % 3 == 0 else 40  # dense cases force collisions
        live: list[Pos] = []
        ops: list[tuple[str, Pos]] = []
        for _ in range(rng.randint(1, 30)):
            if live and rng.random() < 0.25:
                pos = rng.choice(live)
                live.remove(pos)
                ops.append(("remove", pos))
            else:
                pos = (
                    rng.randint(-spread_range, spread_range),
                    rng.randint(-64, 64),
                    rng.randint(-spread_range, spread_range),
                )
                if pos not in live:
                    live.append(pos)
                ops.append(("put", pos))
        cases.append(ops)
    # The 7-element wire update set at assorted coordinates, the most important real use.
    for _ in range(100):
        c = (rng.randint(-1000, 1000), rng.randint(-64, 319), rng.randint(-1000, 1000))
        around = [c] + [
            (c[0] + dx, c[1] + dy, c[2] + dz)
            for dx, dy, dz in ((0, -1, 0), (0, 1, 0), (0, 0, -1), (0, 0, 1), (-1, 0, 0), (1, 0, 0))
        ]
        cases.append([("put", p) for p in around])

    expected = _oracle_orders(java_oracle, cases)
    for ops, java_order in zip(cases, expected, strict=True):
        m: JavaHashMap[Pos, bool] = JavaHashMap(java_hash)
        for op, pos in ops:
            if op == "put":
                m.put(pos, True)
            else:
                m.remove(pos)
        assert list(m.keys()) == java_order, ops
