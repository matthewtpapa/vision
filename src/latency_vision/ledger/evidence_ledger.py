from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol


class EvidenceLedger(Protocol):
    def append(self, record: Mapping[str, Any]) -> None: ...
