# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 The Vision Authors
"""Protocol definitions for embedding matchers.

Vectors are expected to be L2-normalised ``float32`` arrays and similarity is
computed as cosine similarity (dot product on normalised vectors).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

Label = str
Score = float
Neighbor = tuple[Label, Score]


class MatcherProtocol(Protocol):
    """Protocol for vector similarity search backends."""

    def add(self, vec: Sequence[float], label: Label) -> None:
        """Add a single vector with its label to the index."""

    def add_many(self, vecs: Sequence[Sequence[float]], labels: Sequence[Label]) -> None:
        """Add many vectors and labels at once."""

    def topk(self, query: Sequence[float], k: int) -> list[Neighbor]:
        """Return the ``k`` most similar neighbours for ``query``."""
