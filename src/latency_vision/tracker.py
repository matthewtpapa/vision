# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 The Vision Authors
"""Simple object tracker stub."""

from __future__ import annotations

from collections.abc import Iterable


class Tracker:
    """A stub tracker that assigns incremental IDs to bounding boxes."""

    def __init__(self) -> None:
        self._next_id = 1

    def update(
        self, boxes: Iterable[tuple[int, int, int, int]]
    ) -> list[tuple[int, tuple[int, int, int, int]]]:
        """Return each input box paired with a unique ID.

        Parameters
        ----------
        boxes:
            Iterable of bounding boxes in ``(x1, y1, x2, y2)`` format.

        Returns
        -------
        list of tuple
            Each tuple contains the assigned track ID and the corresponding
            bounding box.
        """
        results: list[tuple[int, tuple[int, int, int, int]]] = []
        for box in boxes:
            results.append((self._next_id, box))
            self._next_id += 1
        return results
