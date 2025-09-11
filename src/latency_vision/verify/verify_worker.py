from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol


class VerifyResult(Protocol):
    @property
    def accepted(self) -> bool: ...

    @property
    def evidence_path(self) -> str: ...


class VerifyWorker(Protocol):
    def verify(self, embedding: Sequence[float], candidate_label: str) -> VerifyResult: ...
