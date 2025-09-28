from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Protocol


class TopK(Protocol):
    """Minimal read-only interface; concrete impl may add fields."""

    def scores(self) -> Sequence[float]:
        """Return the similarity scores for the current query."""

        raise NotImplementedError

    def labels(self) -> Sequence[str]:
        """Return the labels corresponding to :meth:`scores`."""

        raise NotImplementedError


class LabelBankProtocol(Protocol):
    """Protocol describing label bank lookup behaviour."""

    def lookup_vecs(self, vectors: Sequence[Sequence[float]], k: int = 10) -> TopK:
        """Return top-*k* matches for raw embedding vectors."""

        raise NotImplementedError

    def lookup(self, items: Sequence[str] | Sequence[int], k: int = 10) -> TopK:
        """Return top-*k* matches for identifier-based lookups."""

        raise NotImplementedError

    def stats(self) -> Mapping[str, int]:
        """Return summary statistics for the label bank."""

        raise NotImplementedError
