from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Protocol


class TopK(Protocol):
    """Minimal read-only interface; concrete impl may add fields."""

    def scores(self) -> Sequence[float]: ...
    def labels(self) -> Sequence[str]: ...


class LabelBankProtocol(Protocol):
    def lookup(self, items: Sequence[str] | Sequence[int], k: int = 10) -> TopK: ...
    def stats(self) -> Mapping[str, int]: ...
