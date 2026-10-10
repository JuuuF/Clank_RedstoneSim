"""Emulation of ``java.util.HashMap``/``HashSet`` iteration order.

The game iterates hash collections of ``BlockPos`` in two order-sensitive places
(see doc/decisions.md ADR-005):

* ``DefaultRedstoneWireEvaluator.updatePowerStrength`` (``HashSet<BlockPos>``),
* ``PistonBaseBlock.moveBlocks`` (``HashMap<BlockPos, BlockState>`` ``deleteAfterMove``).

Java's ``HashMap`` stores entries in ``table[(h ^ (h >>> 16)) & (capacity - 1)]`` where ``h``
is the key's ``hashCode()``. New keys are appended to their bucket's list, iteration walks
the table by index and each bucket in list order, the table starts at 16 slots and doubles
when the size exceeds ``0.75 * capacity``, and a resize keeps the relative order of entries
that land in the same bucket. A bucket that reaches the treeify threshold (8 nodes while
adding a 9th) triggers a resize while the capacity is below 64, and becomes a red-black tree
otherwise. Tree bins are not emulated: they raise ``NotImplementedError`` so a divergence
can never go unnoticed.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator

_DEFAULT_CAPACITY = 16
_LOAD_FACTOR = 0.75
_TREEIFY_THRESHOLD = 8
_MIN_TREEIFY_CAPACITY = 64


def spread(hash_code: int) -> int:
    """``HashMap.hash``: ``h ^ (h >>> 16)`` on the 32-bit hash code (result as unsigned)."""
    h = hash_code & 0xFFFFFFFF
    return h ^ (h >> 16)


class JavaHashMap[K, V]:
    """Insertion/removal semantics and iteration order of ``java.util.HashMap``."""

    def __init__(self, hash_function: Callable[[K], int]) -> None:
        self._hash_function = hash_function
        self._capacity = _DEFAULT_CAPACITY
        self._table: list[list[tuple[K, V]]] = [[] for _ in range(self._capacity)]
        self._size = 0

    @property
    def capacity(self) -> int:
        return self._capacity

    def __len__(self) -> int:
        return self._size

    def _index(self, key: K, capacity: int) -> int:
        return spread(self._hash_function(key)) & (capacity - 1)

    def put(self, key: K, value: V) -> None:
        bucket = self._table[self._index(key, self._capacity)]
        for i, (existing, _) in enumerate(bucket):
            if existing == key:
                bucket[i] = (key, value)  # replacing a value keeps the node's position
                return
        nodes_before = len(bucket)
        bucket.append((key, value))
        if nodes_before >= _TREEIFY_THRESHOLD:
            if self._capacity < _MIN_TREEIFY_CAPACITY:
                self._resize()
            else:
                raise NotImplementedError("Java HashMap tree bins are not emulated")
        self._size += 1
        if self._size > self._capacity * _LOAD_FACTOR:
            self._resize()

    def get(self, key: K, default: V | None = None) -> V | None:
        for existing, value in self._table[self._index(key, self._capacity)]:
            if existing == key:
                return value
        return default

    def __contains__(self, key: object) -> bool:
        bucket = self._table[self._index(key, self._capacity)]  # type: ignore[arg-type]
        return any(existing == key for existing, _ in bucket)

    def remove(self, key: K) -> None:
        bucket = self._table[self._index(key, self._capacity)]
        for i, (existing, _) in enumerate(bucket):
            if existing == key:
                del bucket[i]
                self._size -= 1
                return

    def _resize(self) -> None:
        new_capacity = self._capacity * 2
        new_table: list[list[tuple[K, V]]] = [[] for _ in range(new_capacity)]
        # Walking old buckets in index order and appending preserves the lo/hi split order.
        for bucket in self._table:
            for key, value in bucket:
                new_table[self._index(key, new_capacity)].append((key, value))
        self._table = new_table
        self._capacity = new_capacity

    def items(self) -> Iterator[tuple[K, V]]:
        for bucket in self._table:
            yield from list(bucket)

    def keys(self) -> Iterator[K]:
        for key, _ in self.items():
            yield key

    def __iter__(self) -> Iterator[K]:
        return self.keys()


class JavaHashSet[K]:
    """``java.util.HashSet`` (a ``HashMap`` with dummy values)."""

    def __init__(self, hash_function: Callable[[K], int], items: Iterable[K] = ()) -> None:
        self._map: JavaHashMap[K, bool] = JavaHashMap(hash_function)
        for item in items:
            self.add(item)

    def add(self, item: K) -> None:
        if item not in self._map:
            self._map.put(item, True)

    def __contains__(self, item: object) -> bool:
        return item in self._map

    def __len__(self) -> int:
        return len(self._map)

    def __iter__(self) -> Iterator[K]:
        return self._map.keys()
