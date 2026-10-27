# SPDX-License-Identifier: AGPL-3.0-or-later
"""Small stand-ins for standard-library features newer than Python 3.8.

Added by the ABUKARIM build so the add-on runs on every Kodi from 19
(Matrix) on, not only on Kodi 22's Python 3.14.
"""
from __future__ import annotations

from typing import Any, Iterable, Iterator, Tuple


def zip_strict(*iterables: Iterable[Any]) -> Iterator[Tuple[Any, ...]]:
    """``zip(..., strict=True)``: raise ValueError when the lengths differ."""
    sentinel = object()
    iterators = [iter(it) for it in iterables]
    while True:
        items = [next(it, sentinel) for it in iterators]
        done = [item is sentinel for item in items]
        if all(done):
            return
        if any(done):
            raise ValueError("zip_strict() arguments have different lengths")
        yield tuple(items)
