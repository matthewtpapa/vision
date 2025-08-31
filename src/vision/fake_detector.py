# SPDX-License-Identifier: Apache-2.0
"""Fake object detector stub."""

from __future__ import annotations

from typing import Any


class FakeDetector:
    """A stub detector that returns a fixed bounding box.

    This placeholder mimics a real detector by always returning the same
    bounding box regardless of the input frame.
    """

    def detect(self, frame: Any) -> list[tuple[int, int, int, int]]:
        """Return a list containing a single dummy bounding box.

        Parameters
        ----------
        frame:
            Ignored input representing an image frame.

        Returns
        -------
        list of tuple of int
            A list with one bounding box in ``(x1, y1, x2, y2)`` format.
        """
        return [(50, 50, 200, 200)]
